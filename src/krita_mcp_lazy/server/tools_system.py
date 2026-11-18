"""System and health check MCP tools for krita-MCP-lazy."""

import sys
import time
from typing import Any, Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.core.errors import KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobStatus
from krita_mcp_lazy.transport.client import AsyncIPCClient


async def krita_get_version() -> dict[str, Any]:
    """Retrieve version, capability manifest, and runtime environment of krita-MCP-lazy."""
    return {
        "server_name": "krita-MCP-lazy",
        "engine": "ToonFlow Art Engine",
        "version": "0.1.0",
        "python_version": sys.version,
        "platform": sys.platform,
        "status": "ok",
    }


async def krita_health_check(
    host: str = "127.0.0.1",
    port: Optional[int] = None,
    token: Optional[str] = None,
) -> dict[str, Any]:
    """Check connectivity to Krita application bridge and measure real round-trip latency."""
    target_port = port if port is not None else 18812
    client = AsyncIPCClient(host=host, port=target_port, token=token, timeout=2.0)
    
    start_t = time.perf_counter()
    try:
        req = JobRequest(action="ping", params={})
        resp = await client.send_job(req)
        latency_ms = (time.perf_counter() - start_t) * 1000.0
        
        if resp.status == JobStatus.SUCCESS:
            return {
                "status": "healthy",
                "bridge_connected": True,
                "latency_ms": round(latency_ms, 2),
                "bridge_response": resp.result,
            }
        else:
            return {
                "status": "degraded",
                "bridge_connected": True,
                "latency_ms": round(latency_ms, 2),
                "error": resp.error,
                "error_code": resp.error_code,
            }
    except KritaError as exc:
        return {
            "status": "degraded",
            "bridge_connected": False,
            "error": exc.message,
            "error_code": exc.code.value,
        }
    except Exception as exc:
        return {
            "status": "degraded",
            "bridge_connected": False,
            "error": str(exc),
        }
    finally:
        await client.close()


def register_system_tools(server: Any, config: Optional[KritaConfig] = None) -> None:
    """Register all system inspection and health check tools on the MCP server."""
    cfg = config or KritaConfig()

    @server.tool(name="krita_get_version", description="Get version and platform diagnostics for krita-MCP-lazy")
    async def _tool_get_version() -> dict[str, Any]:
        return await krita_get_version()

    @server.tool(name="krita_health_check", description="Check health and IPC latency of the Krita desktop application bridge")
    async def _tool_health_check(
        host: str = cfg.host,
        port: int = cfg.port,
        token: Optional[str] = cfg.token,
    ) -> dict[str, Any]:
        return await krita_health_check(host=host, port=port, token=token)
