import pytest
from unittest.mock import AsyncMock, patch
from krita_mcp_lazy.server.app import create_mcp_server
from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.core.schemas import JobResponse, JobStatus


@pytest.mark.asyncio
async def test_mcp_server_initialization():
    server = create_mcp_server()
    assert server is not None
    
    # Verify tools registered
    tool_names = [tool.name for tool in await server.list_tools()]
    assert "krita_health_check" in tool_names
    assert "krita_get_version" in tool_names


@pytest.mark.asyncio
async def test_krita_get_version_tool():
    server = create_mcp_server()
    # Call the tool function directly from server
    from krita_mcp_lazy.server.tools_system import krita_get_version
    version_info = await krita_get_version()
    assert version_info["server_name"] == "krita-MCP-lazy"
    assert "version" in version_info
    assert version_info["status"] == "ok"


@pytest.mark.asyncio
async def test_krita_health_check_offline():
    from krita_mcp_lazy.server.tools_system import krita_health_check
    # When bridge is not running, health check reports bridge_connected=False without crashing
    health = await krita_health_check(port=39999)
    assert health["bridge_connected"] is False
    assert health["status"] == "degraded"


@pytest.mark.asyncio
async def test_krita_health_check_online():
    from krita_mcp_lazy.server.tools_system import krita_health_check
    from krita_mcp_lazy.transport.server import AsyncIPCServer
    from krita_mcp_lazy.core.schemas import JobRequest

    token = "health_test_token_12345"

    async def ping_handler(req: JobRequest) -> JobResponse:
        return JobResponse(job_id=req.job_id, status=JobStatus.SUCCESS, result={"pong": True})

    ipc_server = AsyncIPCServer(host="127.0.0.1", port=19995, valid_token=token, handler=ping_handler)
    await ipc_server.start()

    try:
        health = await krita_health_check(port=19995, token=token)
        assert health["bridge_connected"] is True
        assert health["status"] == "healthy"
        assert health["latency_ms"] is not None
    finally:
        await ipc_server.stop()
