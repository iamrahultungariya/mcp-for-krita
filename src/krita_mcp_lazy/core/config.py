"""System configuration and environment settings for krita-MCP-lazy."""

from typing import Any, Optional

from krita_mcp_lazy.core.security import get_or_create_shared_token

try:
    from pydantic import BaseModel, Field, field_validator
    _HAS_PYDANTIC = True
except ImportError:
    _HAS_PYDANTIC = False


if _HAS_PYDANTIC:
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
        token: Optional[str] = Field(default_factory=get_or_create_shared_token, description="Pre-shared or generated session token")

        @field_validator("host")
        @classmethod
        def validate_loopback_host(cls, v: str) -> str:
            """Enforce strict loopback security policy. Never bind to public/external interfaces."""
            allowed_hosts = {"127.0.0.1", "localhost", "::1"}
            if v not in allowed_hosts:
                raise ValueError(f"IPC host must be a loopback address ({', '.join(allowed_hosts)}), got '{v}'")
            return v
else:
    class KritaConfig:
        """Lightweight pure-Python fallback for embedded Krita runtime without Pydantic."""

        def __init__(
            self,
            host: str = "127.0.0.1",
            port: int = 18812,
            queue_max_size: int = 100,
            socket_timeout: float = 30.0,
            max_payload_size: int = 32 * 1024 * 1024,
            memory_budget_bytes: int = 200 * 1024 * 1024,
            token: Optional[str] = None,
        ) -> None:
            allowed_hosts = {"127.0.0.1", "localhost", "::1"}
            if host not in allowed_hosts:
                raise ValueError(f"IPC host must be a loopback address ({', '.join(allowed_hosts)}), got '{host}'")
            self.host = host
            self.port = port
            self.queue_max_size = queue_max_size
            self.socket_timeout = socket_timeout
            self.max_payload_size = max_payload_size
            self.memory_budget_bytes = memory_budget_bytes
            self.token = token if token is not None else get_or_create_shared_token()

        def model_dump(self) -> dict[str, Any]:
            return {
                "host": self.host,
                "port": self.port,
                "queue_max_size": self.queue_max_size,
                "socket_timeout": self.socket_timeout,
                "max_payload_size": self.max_payload_size,
                "memory_budget_bytes": self.memory_budget_bytes,
                "token": self.token,
            }
