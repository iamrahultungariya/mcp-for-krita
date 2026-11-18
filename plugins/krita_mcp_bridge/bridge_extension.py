"""Krita Python Extension bridging loopback IPC transport to Krita main-thread dispatcher."""

import asyncio
import logging
import threading
import time
from typing import Any, Optional

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus
from krita_mcp_lazy.transport.server import AsyncIPCServer
from plugins.krita_mcp_bridge.dispatcher import KritaMainThreadDispatcher
from plugins.krita_mcp_bridge.handlers_assets import register_asset_handlers
from plugins.krita_mcp_bridge.handlers_canvas import register_canvas_handlers
from plugins.krita_mcp_bridge.handlers_character import register_character_handlers
from plugins.krita_mcp_bridge.handlers_document import register_document_handlers
from plugins.krita_mcp_bridge.handlers_environment import register_environment_handlers
from plugins.krita_mcp_bridge.handlers_layers import register_layer_handlers
from plugins.krita_mcp_bridge.handlers_masks import register_mask_handlers
from plugins.krita_mcp_bridge.handlers_painting import register_painting_handlers
from plugins.krita_mcp_bridge.handlers_semantic import register_semantic_handlers
from plugins.krita_mcp_bridge.handlers_strokes import register_stroke_handlers

logger = logging.getLogger(__name__)

# Graceful fallback for headless environments without Krita runtime
try:
    from krita import Extension
except ImportError:
    class Extension:  # type: ignore[no-redef]
        def __init__(self, parent: Any = None) -> None:
            self.parent = parent

        def setup(self) -> None:
            pass

        def createActions(self, window: Any) -> None:
            pass


class BridgeExtension(Extension):
    """Krita Extension that registers with Krita's plugin manager and manages IPC bridge."""

    def __init__(
        self,
        parent: Any = None,
        host: str = "127.0.0.1",
        port: int = 18812,
        token: Optional[str] = None,
        max_queue_size: int = 100,
    ) -> None:
        super().__init__(parent)
        self.host = host
        self.port = port
        self.token = token
        self.dispatcher = KritaMainThreadDispatcher(max_queue_size=max_queue_size)
        self.server: Optional[AsyncIPCServer] = None
        self._server_thread: Optional[threading.Thread] = None
        self._server_loop: Optional[asyncio.AbstractEventLoop] = None
        self._is_running = False

    def setup(self) -> None:
        """Called by Krita upon application startup to initialize plugin."""
        self.dispatcher.attach_qtimer(interval_ms=16)
        self._register_default_handlers()
        register_document_handlers(self.dispatcher)
        register_canvas_handlers(self.dispatcher)
        register_layer_handlers(self.dispatcher)
        register_mask_handlers(self.dispatcher)
        register_semantic_handlers(self.dispatcher)
        register_painting_handlers(self.dispatcher)
        register_stroke_handlers(self.dispatcher)
        register_character_handlers(self.dispatcher)
        register_environment_handlers(self.dispatcher)
        register_asset_handlers(self.dispatcher)
        logger.info("krita-MCP-lazy BridgeExtension setup completed")

    def createActions(self, window: Any) -> None:
        """Called by Krita when a main window is created."""
        pass

    def _register_default_handlers(self) -> None:
        """Register fundamental system-level handlers."""
        self.dispatcher.register_handler("ping", lambda p: {"pong": True, "time": time.time()})
        self.dispatcher.register_handler("system.version", lambda p: {"engine": "krita-MCP-lazy", "version": "0.1.0"})

    async def dispatch_job_async(self, request: JobRequest, timeout_seconds: float = 30.0) -> JobResponse:
        """Enqueue request into main-thread dispatcher and await result asynchronously."""
        self.dispatcher.enqueue(request)
        start_t = time.perf_counter()
        deadline = start_t + (request.timeout_seconds or timeout_seconds)

        while time.perf_counter() < deadline:
            res = self.dispatcher.get_result(request.job_id)
            if res is not None:
                return res
            await asyncio.sleep(0.005)

        # Timed out waiting for main thread
        self.dispatcher.cancel_job(request.job_id)
        return JobResponse(
            job_id=request.job_id,
            status=JobStatus.FAILED,
            error=f"Job execution timed out on Krita main thread after {timeout_seconds:.1f}s",
            error_code=ErrorCode.TIMEOUT.value,
            elapsed_ms=(time.perf_counter() - start_t) * 1000.0,
        )

    def start_ipc_bridge(self) -> None:
        """Launch AsyncIPCServer on a dedicated background thread with its own asyncio loop."""
        if self._is_running:
            return

        def _run_server() -> None:
            self._server_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._server_loop)

            async def _ipc_handler(req: JobRequest) -> JobResponse:
                return await self.dispatch_job_async(req)

            self.server = AsyncIPCServer(
                host=self.host,
                port=self.port,
                valid_token=self.token,
                handler=_ipc_handler,
            )

            async def _main_coro() -> None:
                assert self.server is not None
                await self.server.start()
                while self._is_running:
                    await asyncio.sleep(0.1)
                await self.server.stop()

            self._server_loop.run_until_complete(_main_coro())
            self._server_loop.close()

        self._is_running = True
        self._server_thread = threading.Thread(target=_run_server, daemon=True, name="KritaIPCBridgeThread")
        self._server_thread.start()
        logger.info("IPC Bridge thread launched on %s:%d", self.host, self.port)

    def stop_ipc_bridge(self) -> None:
        """Stop background IPC bridge server thread."""
        self._is_running = False
        if self._server_thread and self._server_thread.is_alive():
            self._server_thread.join(timeout=2.0)
            self._server_thread = None
        self.server = None
