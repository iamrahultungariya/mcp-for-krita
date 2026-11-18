"""Async loopback IPC server for krita-MCP-lazy."""

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Optional, Set

from krita_mcp_lazy.core.errors import ErrorCode
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus
from krita_mcp_lazy.core.security import AuthTokenManager
from krita_mcp_lazy.transport.protocol import DEFAULT_MAX_PAYLOAD_SIZE, ProtocolError, read_message, write_message

logger = logging.getLogger(__name__)

ALLOWED_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


class AsyncIPCServer:
    """Authenticated loopback IPC server listening for commands from FastMCP server."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 18812,
        valid_token: Optional[str] = None,
        handler: Optional[Callable[[JobRequest], Awaitable[JobResponse]]] = None,
        max_payload_size: int = DEFAULT_MAX_PAYLOAD_SIZE,
    ) -> None:
        if host not in ALLOWED_LOOPBACK_HOSTS:
            raise ValueError(
                f"IPC host must be a loopback address ({', '.join(ALLOWED_LOOPBACK_HOSTS)}), got '{host}'"
            )
        self.host = host
        self.port = port
        self.token_manager = AuthTokenManager(token=valid_token)
        self.handler = handler
        self.max_payload_size = max_payload_size
        self._server: Optional[asyncio.Server] = None
        self._client_writers: Set[asyncio.StreamWriter] = set()
        self._is_running = False

    async def start(self) -> None:
        """Start listening on the configured loopback socket."""
        self._server = await asyncio.start_server(
            self._handle_client,
            host=self.host,
            port=self.port,
        )
        self._is_running = True
        logger.info(f"AsyncIPCServer listening on {self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop server and terminate active client connections."""
        if self._server:
            self._server.close()
            try:
                await self._server.wait_closed()
            except Exception:
                pass
            self._server = None

        # Terminate and close all active client writers
        writers = list(self._client_writers)
        for writer in writers:
            try:
                if not writer.is_closing():
                    writer.close()
            except Exception:
                pass

        for writer in writers:
            try:
                await asyncio.wait_for(writer.wait_closed(), timeout=0.5)
            except Exception:
                pass

        self._client_writers.clear()
        self._is_running = False
        logger.info("AsyncIPCServer stopped")

    @property
    def is_running(self) -> bool:
        return self._is_running

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle incoming client connection with strict handshake authentication."""
        self._client_writers.add(writer)
        try:
            # 1. Perform Authentication Handshake
            try:
                auth_msg = await read_message(reader, self.max_payload_size)
            except ProtocolError:
                return

            candidate_token = auth_msg.get("token")
            if not candidate_token and "authorization" in auth_msg:
                auth_header = auth_msg.get("authorization", "")
                if auth_header.startswith("Bearer "):
                    candidate_token = auth_header[7:].strip()

            if not self.token_manager.validate_token(candidate_token):
                logger.warning("IPC Client authentication rejected: invalid token")
                try:
                    await write_message(
                        writer,
                        {
                            "type": "auth_fail",
                            "error": "Authentication failed",
                            "code": ErrorCode.AUTH_FAILED.value,
                        },
                        self.max_payload_size,
                    )
                except Exception:
                    pass
                return

            # Handshake successful
            await write_message(
                writer,
                {"type": "auth_ok", "status": "authenticated"},
                self.max_payload_size,
            )

            # 2. Main Request Loop
            while self._is_running:
                try:
                    msg = await read_message(reader, self.max_payload_size)
                except ProtocolError:
                    break

                if msg.get("type") == "job" and "request" in msg:
                    job_req = JobRequest.model_validate(msg["request"])
                    start_t = time.perf_counter()

                    try:
                        if self.handler:
                            response = await self.handler(job_req)
                        else:
                            response = JobResponse(
                                job_id=job_req.job_id,
                                status=JobStatus.FAILED,
                                error="No handler registered on server",
                                error_code=ErrorCode.INTERNAL_ERROR.value,
                            )
                    except Exception as exc:
                        logger.exception("Error executing handler for job %s", job_req.job_id)
                        response = JobResponse(
                            job_id=job_req.job_id,
                            status=JobStatus.FAILED,
                            error=str(exc),
                            error_code=ErrorCode.INTERNAL_ERROR.value,
                        )

                    if response.elapsed_ms is None:
                        response.elapsed_ms = (time.perf_counter() - start_t) * 1000.0

                    await write_message(
                        writer,
                        {"type": "job_result", "response": response.model_dump()},
                        self.max_payload_size,
                    )

        except Exception as e:
            logger.error("Unexpected error in client session: %s", e)
        finally:
            self._client_writers.discard(writer)
            if not writer.is_closing():
                try:
                    writer.close()
                    await asyncio.wait_for(writer.wait_closed(), timeout=0.5)
                except Exception:
                    pass
