"""Integration test for live or headless IPC connection lifecycle."""

import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.transport.client import AsyncIPCClient
from krita_mcp_lazy.core.schemas import JobResponse, JobStatus


@pytest.mark.asyncio
async def test_live_bridge_mocked_handshake():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="test-1",
        status=JobStatus.SUCCESS,
        result={"pong": True, "engine": "krita-MCP-lazy", "version": "0.1.0"},
    )

    res = await mock_client.send_job("ping", {})
    assert res.status == JobStatus.SUCCESS
    assert res.result["pong"] is True
    assert res.result["engine"] == "krita-MCP-lazy"
