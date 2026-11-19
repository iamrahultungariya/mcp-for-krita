"""Shared data schemas for IPC communication and job lifecycle with dual Pydantic/dataclass support."""

import json
import time
import uuid
from enum import Enum
from typing import Any, Optional

class JobStatus(str, Enum):
    """Lifecycle status of a dispatched job."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


try:
    from pydantic import BaseModel, Field
    _HAS_PYDANTIC = True
except ImportError:
    _HAS_PYDANTIC = False


if _HAS_PYDANTIC:
    class JobRequest(BaseModel):
        """Structured request payload dispatched from FastMCP server to Krita IPC extension."""

        job_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Globally unique UUID for job tracking")
        action: str = Field(..., description="Action namespace and method name, e.g. 'document.create'")
        params: dict[str, Any] = Field(default_factory=dict, description="Parameters dictionary for the action")
        timeout_seconds: Optional[float] = Field(default=None, description="Optional per-job execution timeout")
        created_at: float = Field(default_factory=time.time, description="Monotonic creation timestamp in epoch seconds")

    class JobResponse(BaseModel):
        """Structured response payload returned from Krita IPC extension to FastMCP server."""

        job_id: str = Field(..., description="UUID corresponding to original JobRequest")
        status: JobStatus = Field(..., description="Execution status")
        result: Optional[dict[str, Any]] = Field(default=None, description="Action result data if successful")
        error: Optional[str] = Field(default=None, description="Human-readable error description if failed")
        error_code: Optional[str] = Field(default=None, description="Standardized ErrorCode string if failed")
        elapsed_ms: Optional[float] = Field(default=None, description="Real wall-clock execution duration in milliseconds")

else:
    class JobRequest:
        """Lightweight pure-python fallback for embedded Krita runtime without Pydantic."""

        def __init__(
            self,
            action: str,
            params: Optional[dict[str, Any]] = None,
            job_id: Optional[str] = None,
            timeout_seconds: Optional[float] = None,
            created_at: Optional[float] = None,
        ) -> None:
            self.job_id = job_id if job_id is not None else str(uuid.uuid4())
            self.action = action
            self.params = params if params is not None else {}
            self.timeout_seconds = timeout_seconds
            self.created_at = created_at if created_at is not None else time.time()

        @classmethod
        def model_validate(cls, data: dict[str, Any]) -> "JobRequest":
            return cls(
                job_id=data.get("job_id"),
                action=data["action"],
                params=data.get("params", {}),
                timeout_seconds=data.get("timeout_seconds"),
                created_at=data.get("created_at"),
            )

        @classmethod
        def model_validate_json(cls, json_str: str) -> "JobRequest":
            data = json.loads(json_str)
            return cls.model_validate(data)

        def model_dump(self) -> dict[str, Any]:
            return {
                "job_id": self.job_id,
                "action": self.action,
                "params": self.params,
                "timeout_seconds": self.timeout_seconds,
                "created_at": self.created_at,
            }

        def model_dump_json(self) -> str:
            return json.dumps(self.model_dump())

    class JobResponse:
        """Lightweight pure-python fallback for embedded Krita runtime without Pydantic."""

        def __init__(
            self,
            job_id: str,
            status: Any,
            result: Optional[dict[str, Any]] = None,
            error: Optional[str] = None,
            error_code: Optional[str] = None,
            elapsed_ms: Optional[float] = None,
        ) -> None:
            self.job_id = job_id
            self.status = status if isinstance(status, JobStatus) else JobStatus(status)
            self.result = result
            self.error = error
            self.error_code = error_code
            self.elapsed_ms = elapsed_ms

        @classmethod
        def model_validate(cls, data: dict[str, Any]) -> "JobResponse":
            return cls(
                job_id=data["job_id"],
                status=data["status"],
                result=data.get("result"),
                error=data.get("error"),
                error_code=data.get("error_code"),
                elapsed_ms=data.get("elapsed_ms"),
            )

        @classmethod
        def model_validate_json(cls, json_str: str) -> "JobResponse":
            data = json.loads(json_str)
            return cls.model_validate(data)

        def model_dump(self) -> dict[str, Any]:
            status_val = self.status.value if hasattr(self.status, "value") else str(self.status)
            return {
                "job_id": self.job_id,
                "status": status_val,
                "result": self.result,
                "error": self.error,
                "error_code": self.error_code,
                "elapsed_ms": self.elapsed_ms,
            }

        def model_dump_json(self) -> str:
            return json.dumps(self.model_dump())
