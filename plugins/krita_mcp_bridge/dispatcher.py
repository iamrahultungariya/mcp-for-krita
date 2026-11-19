"""Main-thread queue dispatcher for running Krita API operations safely in the Qt event loop."""

import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus

logger = logging.getLogger(__name__)


class KritaMainThreadDispatcher:
    """Dispatches incoming IPC jobs safely into Krita's main GUI thread.

    Krita's C++/Qt API (KisDocument, KisNode, brush engine) must only be called from
    the main Qt GUI thread. This dispatcher queues requests and processes them
    via Qt's QTimer ticks or synchronous test ticks.
    """

    def __init__(self, max_queue_size: int = 100, max_results: int = 200, max_cancelled: int = 500) -> None:
        self.max_queue_size = max_queue_size
        self.max_results = max_results
        self.max_cancelled = max_cancelled
        self._queue: List[JobRequest] = []
        self._lock = threading.Lock()
        self._handlers: Dict[str, Callable[[dict[str, Any]], Any]] = {}
        self._results: Dict[str, JobResponse] = {}
        self._cancelled_job_ids: Set[str] = set()
        self._status_listeners: List[Callable[[str, Optional[str], int], None]] = []
        self._qtimer = None

    def register_status_listener(self, listener: Callable[[str, Optional[str], int], None]) -> None:
        """Register a callback for UI/docker telemetry updates (status, active_job_id, queue_length)."""
        with self._lock:
            self._status_listeners.append(listener)

    def _notify_status(self, status: str, active_job_id: Optional[str] = None) -> None:
        with self._lock:
            q_len = len(self._queue)
            listeners = list(self._status_listeners)
        for listener in listeners:
            try:
                listener(status, active_job_id, q_len)
            except Exception as exc:
                logger.debug("Failed notifying status listener: %s", exc)

    def register_handler(self, action: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        """Register a handler callback for a specific action namespace."""
        with self._lock:
            self._handlers[action] = handler

    def enqueue(self, request: JobRequest) -> None:
        """Enqueue a JobRequest for execution on the main Qt thread.

        Raises KritaError with QUEUE_FULL if pending queue exceeds max_queue_size.
        """
        with self._lock:
            if len(self._queue) >= self.max_queue_size:
                raise KritaError(
                    ErrorCode.QUEUE_FULL,
                    f"Dispatcher queue is full ({len(self._queue)}/{self.max_queue_size})",
                    job_id=request.job_id,
                )
            self._queue.append(request)
        self._notify_status("QUEUED", request.job_id)

    def queue_size(self) -> int:
        """Return the current number of pending jobs in queue."""
        with self._lock:
            return len(self._queue)

    def _store_result(self, job_id: str, response: JobResponse) -> None:
        """Store job response with bounded LRU/FIFO eviction."""
        while len(self._results) >= self.max_results:
            oldest_key = next(iter(self._results))
            del self._results[oldest_key]
        self._results[job_id] = response

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job by ID before execution."""
        with self._lock:
            for idx, req in enumerate(self._queue):
                if req.job_id == job_id:
                    self._queue.pop(idx)
                    self._store_result(
                        job_id,
                        JobResponse(
                            job_id=job_id,
                            status=JobStatus.CANCELLED,
                            error="Job was cancelled prior to execution",
                        ),
                    )
                    return True
            self._cancelled_job_ids.add(job_id)
            if len(self._cancelled_job_ids) > self.max_cancelled:
                self._cancelled_job_ids = set(list(self._cancelled_job_ids)[-self.max_cancelled // 2:])
            return False

    def get_result(self, job_id: str, pop: bool = False) -> Optional[JobResponse]:
        """Fetch cached result for a completed or failed job.

        If pop is True, removes the result from cache to prevent unbounded memory growth.
        """
        with self._lock:
            if pop:
                return self._results.pop(job_id, None)
            return self._results.get(job_id)

    def process_pending_jobs(self, max_batch: int = 10) -> int:
        """Drain and execute up to max_batch pending jobs on the calling thread.

        This method should be called on the Qt main GUI thread via QTimer.
        """
        jobs_to_process: List[JobRequest] = []
        with self._lock:
            count = min(max_batch, len(self._queue))
            for _ in range(count):
                jobs_to_process.append(self._queue.pop(0))

        processed_count = 0
        for job in jobs_to_process:
            self._notify_status("BUSY", job.job_id)
            if job.job_id in self._cancelled_job_ids:
                with self._lock:
                    self._store_result(
                        job.job_id,
                        JobResponse(
                            job_id=job.job_id,
                            status=JobStatus.CANCELLED,
                            error="Job was cancelled prior to execution",
                        ),
                    )
                processed_count += 1
                continue

            with self._lock:
                handler = self._handlers.get(job.action)

            if not handler:
                response = JobResponse(
                    job_id=job.job_id,
                    status=JobStatus.FAILED,
                    error=f"No handler registered for action '{job.action}'",
                    error_code=ErrorCode.NOT_FOUND.value,
                )
            else:
                start_time = time.perf_counter()
                try:
                    res = handler(job.params)
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0

                    if isinstance(res, JobResponse):
                        response = res
                        if response.elapsed_ms is None:
                            response.elapsed_ms = elapsed_ms
                    elif isinstance(res, dict):
                        response = JobResponse(
                            job_id=job.job_id,
                            status=JobStatus.SUCCESS,
                            result=res,
                            elapsed_ms=elapsed_ms,
                        )
                    else:
                        response = JobResponse(
                            job_id=job.job_id,
                            status=JobStatus.SUCCESS,
                            result={"value": res},
                            elapsed_ms=elapsed_ms,
                        )
                except Exception as exc:
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                    logger.exception("Exception occurred executing action '%s'", job.action)
                    response = JobResponse(
                        job_id=job.job_id,
                        status=JobStatus.FAILED,
                        error=str(exc),
                        error_code=ErrorCode.INTERNAL_ERROR.value,
                        elapsed_ms=elapsed_ms,
                    )

            with self._lock:
                self._store_result(job.job_id, response)
            processed_count += 1

        if processed_count > 0:
            self._notify_status("READY", None)

        return processed_count

    def attach_qtimer(self, interval_ms: int = 16) -> Any:
        """Attach a Qt QTimer to continuously pump pending jobs on the main thread."""
        try:
            try:
                from PyQt5.QtCore import QTimer
            except ImportError:
                from PyQt6.QtCore import QTimer

            timer = QTimer()
            timer.setInterval(interval_ms)
            timer.timeout.connect(lambda: self.process_pending_jobs())
            timer.start()
            self._qtimer = timer
            logger.info("Attached QTimer dispatcher pump (%d ms interval)", interval_ms)
            return timer
        except ImportError:
            logger.warning("PyQt not found; running dispatcher in headless tick mode")
            return None
