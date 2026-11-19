import asyncio
import pytest
from plugins.krita_mcp_bridge.dispatcher import KritaMainThreadDispatcher
from plugins.krita_mcp_bridge.bridge_extension import BridgeExtension
from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus


def test_dispatcher_queue_and_execute():
    dispatcher = KritaMainThreadDispatcher(max_queue_size=10)
    
    executed = []
    def sample_action(params):
        executed.append(params["val"])
        return {"processed": True}

    dispatcher.register_handler("test.action", sample_action)
    
    req = JobRequest(action="test.action", params={"val": 42})
    dispatcher.enqueue(req)
    
    assert dispatcher.queue_size() == 1
    # Process tick simulating Qt QTimer tick
    processed_count = dispatcher.process_pending_jobs()
    
    assert processed_count == 1
    assert executed == [42]
    assert dispatcher.queue_size() == 0
    resp = dispatcher.get_result(req.job_id)
    assert resp is not None
    assert resp.status == JobStatus.SUCCESS
    assert resp.result["processed"] is True
    assert resp.elapsed_ms is not None


def test_dispatcher_unregistered_action():
    dispatcher = KritaMainThreadDispatcher(max_queue_size=10)
    req = JobRequest(action="unknown.action", params={})
    dispatcher.enqueue(req)
    
    dispatcher.process_pending_jobs()
    resp = dispatcher.get_result(req.job_id)
    assert resp is not None
    assert resp.status == JobStatus.FAILED
    assert resp.error_code == ErrorCode.NOT_FOUND.value


def test_dispatcher_queue_full():
    dispatcher = KritaMainThreadDispatcher(max_queue_size=2)
    dispatcher.register_handler("noop", lambda p: {})
    
    req1 = JobRequest(action="noop", params={})
    req2 = JobRequest(action="noop", params={})
    req3 = JobRequest(action="noop", params={})
    
    dispatcher.enqueue(req1)
    dispatcher.enqueue(req2)
    
    with pytest.raises(KritaError) as exc_info:
        dispatcher.enqueue(req3)
    assert exc_info.value.code == ErrorCode.QUEUE_FULL


def test_dispatcher_handler_exception():
    dispatcher = KritaMainThreadDispatcher(max_queue_size=10)
    
    def failing_handler(params):
        raise RuntimeError("Operation failed inside Krita")
        
    dispatcher.register_handler("failing.action", failing_handler)
    req = JobRequest(action="failing.action", params={})
    dispatcher.enqueue(req)
    
    dispatcher.process_pending_jobs()
    resp = dispatcher.get_result(req.job_id)
    assert resp is not None
    assert resp.status == JobStatus.FAILED
    assert "Operation failed inside Krita" in resp.error
    assert resp.error_code == ErrorCode.INTERNAL_ERROR.value


def test_dispatcher_cancel_job():
    dispatcher = KritaMainThreadDispatcher(max_queue_size=10)
    req = JobRequest(action="any.action", params={})
    dispatcher.enqueue(req)
    
    cancelled = dispatcher.cancel_job(req.job_id)
    assert cancelled is True
    assert dispatcher.queue_size() == 0
    
    resp = dispatcher.get_result(req.job_id)
    assert resp is not None
    assert resp.status == JobStatus.CANCELLED


@pytest.mark.asyncio
async def test_bridge_extension_dispatch_async():
    extension = BridgeExtension(parent=None, max_queue_size=10)
    extension.dispatcher.register_handler("echo", lambda p: {"echoed": p})
    
    req = JobRequest(action="echo", params={"data": 123})
    
    # Simulate main thread loop running in background
    async def pump_dispatcher():
        while True:
            await asyncio.sleep(0.01)
            extension.dispatcher.process_pending_jobs()
            
    pump_task = asyncio.create_task(pump_dispatcher())
    try:
        resp = await extension.dispatch_job_async(req, timeout_seconds=1.0)
        assert resp.status == JobStatus.SUCCESS
        assert resp.result["echoed"]["data"] == 123
    finally:
        pump_task.cancel()
        try:
            await pump_task
        except asyncio.CancelledError:
            pass


def test_bridge_extension_setup_and_token():
    ext = BridgeExtension()
    assert ext.token is not None
    assert len(ext.token) >= 32
    assert not ext._is_running

    try:
        ext.setup()
        assert ext._is_running is True
        assert ext.server is not None
        # Verify handlers registered
        assert "document.create" in ext.dispatcher._handlers
        assert "stroke.paint" in ext.dispatcher._handlers
        assert "brush.configure" in ext.dispatcher._handlers
        assert "visual.capture_canvas" in ext.dispatcher._handlers
    finally:
        ext.stop_ipc_bridge()
        assert ext._is_running is False


def test_dispatcher_get_result_pop():
    dispatcher = KritaMainThreadDispatcher(max_queue_size=10)
    dispatcher.register_handler("test.action", lambda p: {"ok": True})

    req = JobRequest(action="test.action", params={})
    dispatcher.enqueue(req)
    dispatcher.process_pending_jobs()

    # Peek without popping
    resp1 = dispatcher.get_result(req.job_id, pop=False)
    assert resp1 is not None
    assert resp1.status == JobStatus.SUCCESS

    # Pop
    resp2 = dispatcher.get_result(req.job_id, pop=True)
    assert resp2 is not None
    assert resp2.job_id == req.job_id

    # Should now be gone from cache
    resp3 = dispatcher.get_result(req.job_id)
    assert resp3 is None


def test_dispatcher_bounded_result_eviction():
    # Set small max_results limit
    dispatcher = KritaMainThreadDispatcher(max_queue_size=50, max_results=5)
    dispatcher.register_handler("echo", lambda p: p)

    job_ids = []
    for i in range(10):
        req = JobRequest(action="echo", params={"i": i})
        job_ids.append(req.job_id)
        dispatcher.enqueue(req)

    dispatcher.process_pending_jobs(max_batch=10)

    # Size must not exceed max_results
    assert len(dispatcher._results) == 5

    # Oldest 5 jobs must have been evicted (FIFO)
    for old_id in job_ids[:5]:
        assert dispatcher.get_result(old_id) is None

    # Newest 5 jobs must still be present
    for new_id in job_ids[5:]:
        assert dispatcher.get_result(new_id) is not None


def test_status_docker_widget():
    from plugins.krita_mcp_bridge.status_docker import StatusDocker
    docker = StatusDocker()
    assert docker.current_status == "READY"
    assert docker.queue_length == 0

    docker.update_status("BUSY", active_job_id="job_abc", queue_length=3)
    assert docker.current_status == "BUSY"
    assert docker.active_job_id == "job_abc"
    assert docker.queue_length == 3


def test_dispatcher_status_listener():
    from plugins.krita_mcp_bridge.status_docker import StatusDocker
    docker = StatusDocker()
    dispatcher = KritaMainThreadDispatcher(max_queue_size=10)
    dispatcher.register_status_listener(docker.update_status)
    dispatcher.register_handler("ping", lambda p: {"pong": True})

    req = JobRequest(action="ping", params={})
    dispatcher.enqueue(req)
    assert docker.current_status == "QUEUED"
    assert docker.queue_length == 1

    dispatcher.process_pending_jobs()
    assert docker.current_status == "READY"
    assert docker.queue_length == 0
