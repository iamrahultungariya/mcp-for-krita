import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus
from krita_mcp_lazy.painting.brush_service import BrushService
from krita_mcp_lazy.painting.models import BrushConfig, BrushPresetInfo
from krita_mcp_lazy.server.app import create_mcp_server


@pytest.mark.asyncio
async def test_brush_preset_discovery():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="job_list_presets",
        status=JobStatus.SUCCESS,
        result={
            "presets": [
                {"name": "b)_Basic-5_Size", "category": "Basic", "engine": "Pixel"},
                {"name": "c)_Pencil-2B", "category": "Pencil", "engine": "Pixel"},
            ]
        },
    )

    svc = BrushService(client=mock_client)
    presets = await svc.list_presets(category="Basic")
    assert len(presets) == 2
    assert presets[0]["name"] == "b)_Basic-5_Size"

    sent_req = mock_client.send_job.call_args[0][0]
    assert sent_req.action == "brush.list_presets"
    assert sent_req.params["category"] == "Basic"


@pytest.mark.asyncio
async def test_brush_select_and_configure():
    mock_client = AsyncMock()
    mock_client.send_job.side_effect = [
        JobResponse(
            job_id="job_select",
            status=JobStatus.SUCCESS,
            result={"preset_name": "c)_Pencil-2B", "selected": True},
        ),
        JobResponse(
            job_id="job_config",
            status=JobStatus.SUCCESS,
            result={"size": 25.0, "opacity": 0.85, "flow": 0.9, "color": "#ff0000", "configured": True},
        ),
    ]

    svc = BrushService(client=mock_client)
    select_res = await svc.select_preset("c)_Pencil-2B")
    assert select_res["selected"] is True

    config = BrushConfig(size=25.0, opacity=0.85, flow=0.9, color="#ff0000")
    config_res = await svc.configure_brush(config)
    assert config_res["configured"] is True
    assert config_res["size"] == 25.0


@pytest.mark.asyncio
async def test_get_current_brush():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="job_curr",
        status=JobStatus.SUCCESS,
        result={"current_preset": "c)_Pencil-2B", "size": 15.0, "color": "#000000"},
    )

    svc = BrushService(client=mock_client)
    curr = await svc.get_current_brush()
    assert curr["current_preset"] == "c)_Pencil-2B"
    assert curr["size"] == 15.0


@pytest.mark.asyncio
async def test_brush_service_error_handling():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="job_err",
        status=JobStatus.FAILED,
        error="Brush preset 'MissingPreset' not found in Krita resources",
        error_code=ErrorCode.PAINT_ERROR.value,
    )

    svc = BrushService(client=mock_client)
    with pytest.raises(KritaError) as exc_info:
        await svc.select_preset("MissingPreset")
    assert exc_info.value.code == ErrorCode.PAINT_ERROR
    assert "not found" in exc_info.value.message


@pytest.mark.asyncio
async def test_mcp_painting_tools_registered():
    server = create_mcp_server()
    tool_names = [tool.name for tool in await server.list_tools()]

    assert "krita_list_brush_presets" in tool_names
    assert "krita_select_brush_preset" in tool_names
    assert "krita_configure_brush" in tool_names
    assert "krita_get_current_brush" in tool_names
