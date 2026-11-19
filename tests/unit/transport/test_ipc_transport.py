import asyncio
import pytest
from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus
from krita_mcp_lazy.transport.client import AsyncIPCClient
from krita_mcp_lazy.transport.server import AsyncIPCServer


@pytest.mark.asyncio
async def test_authenticated_ipc_roundtrip():
    token = "test_secret_token_1234567890abcdef"
    
    async def handler(request: JobRequest) -> JobResponse:
        return JobResponse(
            job_id=request.job_id,
            status=JobStatus.SUCCESS,
            result={"echo": request.params},
        )

    server = AsyncIPCServer(host="127.0.0.1", port=19999, valid_token=token, handler=handler)
    await server.start()
    
    client = AsyncIPCClient(host="127.0.0.1", port=19999, token=token)
    bad_client = AsyncIPCClient(host="127.0.0.1", port=19999, token="bad_token")
    try:
        req = JobRequest(action="ping", params={"msg": "hello"})
        res = await client.send_job(req)
        assert res.status == JobStatus.SUCCESS
        assert res.result["echo"]["msg"] == "hello"
        
        # Test invalid token rejection
        with pytest.raises(KritaError) as exc_info:
            await bad_client.send_job(req)
        assert exc_info.value.code == ErrorCode.AUTH_FAILED
    finally:
        await client.close()
        await bad_client.close()
        await server.stop()


@pytest.mark.asyncio
async def test_multiple_sequential_jobs():
    token = "session_token_multi_test_12345"

    async def handler(request: JobRequest) -> JobResponse:
        count = request.params.get("count", 0)
        return JobResponse(
            job_id=request.job_id,
            status=JobStatus.SUCCESS,
            result={"doubled": count * 2},
        )

    server = AsyncIPCServer(host="127.0.0.1", port=19998, valid_token=token, handler=handler)
    await server.start()

    client = AsyncIPCClient(host="127.0.0.1", port=19998, token=token)
    try:
        for i in range(5):
            req = JobRequest(action="math.double", params={"count": i})
            res = await client.send_job(req)
            assert res.status == JobStatus.SUCCESS
            assert res.result["doubled"] == i * 2
    finally:
        await client.close()
        await server.stop()


@pytest.mark.asyncio
async def test_handler_error_propagation():
    token = "session_token_error_test_12345"

    async def error_handler(request: JobRequest) -> JobResponse:
        raise ValueError("Simulated handler crash")

    server = AsyncIPCServer(host="127.0.0.1", port=19997, valid_token=token, handler=error_handler)
    await server.start()

    client = AsyncIPCClient(host="127.0.0.1", port=19997, token=token)
    try:
        req = JobRequest(action="crash", params={})
        res = await client.send_job(req)
        assert res.status == JobStatus.FAILED
        assert "Simulated handler crash" in res.error
        assert res.error_code == ErrorCode.INTERNAL_ERROR.value
    finally:
        await client.close()
        await server.stop()


@pytest.mark.asyncio
async def test_server_loopback_binding_restriction():
    token = "test_token"
    async def dummy_handler(req: JobRequest) -> JobResponse:
        return JobResponse(job_id=req.job_id, status=JobStatus.SUCCESS)

    with pytest.raises(ValueError, match="IPC host must be a loopback address"):
        AsyncIPCServer(host="0.0.0.0", port=19996, valid_token=token, handler=dummy_handler)


@pytest.mark.asyncio
async def test_client_connection_failure():
    # Attempt connecting to a port where no server is running
    client = AsyncIPCClient(host="127.0.0.1", port=29999, token="dummy")
    req = JobRequest(action="test", params={})
    with pytest.raises(KritaError) as exc_info:
        await client.send_job(req)
    assert exc_info.value.code == ErrorCode.KRITA_UNAVAILABLE


@pytest.mark.asyncio
async def test_client_send_job_overload_action_params():
    token = "overload_test_token"
    async def handler(req: JobRequest) -> JobResponse:
        return JobResponse(job_id=req.job_id, status=JobStatus.SUCCESS, result={"action": req.action, "p": req.params})

    server = AsyncIPCServer(host="127.0.0.1", port=19994, valid_token=token, handler=handler)
    await server.start()

    client = AsyncIPCClient(host="127.0.0.1", port=19994, token=token)
    try:
        # Call with (action, params) directly
        res = await client.send_job("test.overload", {"foo": "bar"})
        assert res.status == JobStatus.SUCCESS
        assert res.result["action"] == "test.overload"
        assert res.result["p"]["foo"] == "bar"
    finally:
        await client.close()
        await server.stop()
