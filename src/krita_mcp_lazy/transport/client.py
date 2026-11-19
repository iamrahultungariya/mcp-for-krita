"""Async loopback IPC client communicating with Krita bridge extension."""

import asyncio
import logging
from typing import Any, Dict, Optional, Union

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse
from krita_mcp_lazy.transport.protocol import (
    DEFAULT_MAX_PAYLOAD_SIZE,
    ProtocolError,
    read_message,
    write_message,
)

logger = logging.getLogger(__name__)

ALLOWED_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


class AsyncIPCClient:
    """Client for dispatching JobRequests to Krita's native IPC server."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 18812,
        token: Optional[str] = None,
        timeout: float = 30.0,
        max_payload_size: int = DEFAULT_MAX_PAYLOAD_SIZE,
    ) -> None:
        if host not in ALLOWED_LOOPBACK_HOSTS:
            raise ValueError(
                f"IPC host must be a loopback address ({', '.join(ALLOWED_LOOPBACK_HOSTS)}), got '{host}'"
            )
        self.host = host
        self.port = port
        self.token = token
        self.timeout = timeout
        self.max_payload_size = max_payload_size
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        """Establish connection to Krita IPC server and perform handshake authentication."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout,
            )
        except (OSError, ConnectionRefusedError, asyncio.TimeoutError) as exc:
            raise KritaError(
                ErrorCode.KRITA_UNAVAILABLE,
                f"Failed to connect to Krita bridge on {self.host}:{self.port}: {exc}",
            ) from exc

        # Send authentication handshake
        try:
            auth_payload = {
                "type": "auth",
                "token": self.token or "",
                "authorization": f"Bearer {self.token or ''}",
            }
            await write_message(writer, auth_payload, self.max_payload_size)
            auth_resp = await asyncio.wait_for(
                read_message(reader, self.max_payload_size),
                timeout=self.timeout,
            )
        except Exception as exc:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            if isinstance(exc, KritaError):
                raise
            raise KritaError(
                ErrorCode.KRITA_UNAVAILABLE,
                f"Handshake failed with Krita bridge: {exc}",
            ) from exc

        if auth_resp.get("type") == "auth_fail" or auth_resp.get("status") != "authenticated":
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
            raw_code = auth_resp.get("code", ErrorCode.AUTH_FAILED.value)
            code = ErrorCode.AUTH_FAILED
            for member in ErrorCode:
                if member.value == raw_code:
                    code = member
                    break
            raise KritaError(
                code=code,
                message=auth_resp.get("error", "Authentication rejected by Krita bridge"),
            )

        self._reader = reader
        self._writer = writer

    async def close(self) -> None:
        """Close connection and reset reader/writer streams."""
        async with self._lock:
            if self._writer and not self._writer.is_closing():
                self._writer.close()
                try:
                    await self._writer.wait_closed()
                except Exception:
                    pass
            self._writer = None
            self._reader = None

    async def send_job(
        self,
        request_or_action: Union[JobRequest, str],
        params: Optional[Dict[str, Any]] = None,
        timeout_seconds: Optional[float] = None,
    ) -> JobResponse:
        """Send a JobRequest or (action, params) to Krita bridge and await JobResponse."""
        if isinstance(request_or_action, str):
            request = JobRequest(
                action=request_or_action,
                params=params or {},
                timeout_seconds=timeout_seconds,
            )
        elif isinstance(request_or_action, JobRequest):
            request = request_or_action
            if timeout_seconds is not None:
                request.timeout_seconds = timeout_seconds
        else:
            raise TypeError(
                f"send_job expects a JobRequest instance or action string, got {type(request_or_action)}"
            )

        async with self._lock:
            # Reconnect if connection was closed or never established
            if not self._writer or self._writer.is_closing():
                await self.connect()

            timeout = request.timeout_seconds or self.timeout
            try:
                payload = {"type": "job", "request": request.model_dump()}
                await write_message(self._writer, payload, self.max_payload_size)

                resp_msg = await asyncio.wait_for(
                    read_message(self._reader, self.max_payload_size),
                    timeout=timeout,
                )

                if resp_msg.get("type") == "job_result" and "response" in resp_msg:
                    return JobResponse.model_validate(resp_msg["response"])

                raise KritaError(
                    ErrorCode.INTERNAL_ERROR,
                    f"Unexpected response format from Krita bridge: {resp_msg}",
                    job_id=request.job_id,
                )

            except asyncio.TimeoutError as exc:
                await self._force_close()
                raise KritaError(
                    ErrorCode.TIMEOUT,
                    f"Execution for job '{request.job_id}' timed out after {timeout} seconds",
                    job_id=request.job_id,
                ) from exc
            except (ProtocolError, ConnectionResetError, BrokenPipeError) as exc:
                await self._force_close()
                raise KritaError(
                    ErrorCode.KRITA_UNAVAILABLE,
                    f"Krita bridge socket disconnected during job '{request.job_id}': {exc}",
                    job_id=request.job_id,
                ) from exc

    async def _force_close(self) -> None:
        """Force-close streams on transport error without acquiring lock."""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        self._writer = None
        self._reader = None
