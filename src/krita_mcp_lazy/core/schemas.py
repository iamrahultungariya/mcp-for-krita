"""Shared Pydantic data schemas for IPC communication and job lifecycle."""

import time
import uuid
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    """Lifecycle status of a dispatched job."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


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
