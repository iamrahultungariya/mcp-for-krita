"""System configuration and environment settings for krita-MCP-lazy."""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class KritaConfig(BaseModel):
    """Runtime configuration for loopback IPC transport and MCP server."""

    host: str = Field(default="127.0.0.1", description="Loopback host address strictly bound to localhost")
    port: int = Field(default=18812, ge=1024, le=65535, description="TCP port for IPC bridge")
    queue_max_size: int = Field(default=100, gt=0, description="Max pending jobs in main-thread queue")
    socket_timeout: float = Field(default=30.0, gt=0.0, description="Socket timeout in seconds")
    max_payload_size: int = Field(default=32 * 1024 * 1024, gt=0, description="Max IPC payload buffer (32 MiB)")
    memory_budget_bytes: int = Field(
        default=200 * 1024 * 1024,
        gt=0,
        description="Memory throughput budget (200 MiB/s limit)",
    )
    token: Optional[str] = Field(default=None, description="Pre-shared or generated session token")

    @field_validator("host")
    @classmethod
    def validate_loopback_host(cls, v: str) -> str:
        """Enforce strict loopback security policy. Never bind to public/external interfaces."""
        allowed_hosts = {"127.0.0.1", "localhost", "::1"}
        if v not in allowed_hosts:
            raise ValueError(f"IPC host must be a loopback address ({', '.join(allowed_hosts)}), got '{v}'")
        return v
