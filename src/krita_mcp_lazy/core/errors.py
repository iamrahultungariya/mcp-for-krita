"""Core error taxonomy and exception types for krita-MCP-lazy."""

from enum import Enum
from typing import Any, Optional


class ErrorCode(str, Enum):
    """Standardized error codes for IPC and MCP tool operations."""

    AUTH_FAILED = "AUTH_FAILED"
    QUEUE_FULL = "QUEUE_FULL"
    TIMEOUT = "TIMEOUT"
    KRITA_UNAVAILABLE = "KRITA_UNAVAILABLE"
    DOCUMENT_ERROR = "DOCUMENT_ERROR"
    LAYER_ERROR = "LAYER_ERROR"
    PAINT_ERROR = "PAINT_ERROR"
    INVALID_PARAMS = "INVALID_PARAMS"
    NOT_FOUND = "NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class KritaError(Exception):
    """Base exception class for all krita-MCP-lazy domain errors."""

    def __init__(
        self,
        code: ErrorCode | str,
        message: str,
        details: Optional[dict[str, Any]] = None,
        job_id: Optional[str] = None,
    ) -> None:
        super().__init__(f"[{code if isinstance(code, str) else code.value}] {message}")
        self.code = code if isinstance(code, ErrorCode) else ErrorCode(code)
        self.message = message
        self.details = details or {}
        self.job_id = job_id

    def to_dict(self) -> dict[str, Any]:
        """Serialize error details for JSON-safe responses."""
        return {
            "code": self.code.value,
            "message": self.message,
            "details": self.details,
            "job_id": self.job_id,
        }


def check_job_response(
    resp: Any,
    default_error_code: ErrorCode,
    default_message: str = "Operation failed",
) -> dict[str, Any]:
    """Validate JobResponse status and raise KritaError with proper taxonomy code if failed."""
    status_val = getattr(resp.status, "value", str(resp.status)).upper() if hasattr(resp, "status") else ""
    if status_val not in ("SUCCESS", "JOBSTATUS.SUCCESS") and getattr(resp, "status", None) != "success":
        code = default_error_code
        err_msg = default_message

        err_obj = getattr(resp, "error", None)
        if isinstance(err_obj, dict):
            err_msg = err_obj.get("message", default_message)
            raw_code = err_obj.get("code")
            if raw_code:
                for member in ErrorCode:
                    if member.value == raw_code:
                        code = member
                        break
        elif isinstance(err_obj, str) and not err_obj.startswith("<AsyncMock"):
            err_msg = err_obj

        raw_err_code = getattr(resp, "error_code", None)
        if raw_err_code:
            for member in ErrorCode:
                if member.value == raw_err_code:
                    code = member
                    break

        raise KritaError(code=code, message=err_msg, job_id=getattr(resp, "job_id", None))

    return getattr(resp, "result", None) or {}
