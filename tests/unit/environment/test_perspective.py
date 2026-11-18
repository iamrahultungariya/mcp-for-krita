import pytest
from unittest.mock import AsyncMock

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.environment.models import DepthPlaneType, PerspectiveType
from krita_mcp_lazy.environment.perspective import PerspectiveGridEngine


@pytest.mark.asyncio
async def test_two_point_perspective_grid():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "perspective_type": "two_point",
        "vp_left": [-500.0, 1080.0],
        "vp_right": [4340.0, 1080.0],
        "horizon_y": 1080.0,
        "grid_layer_id": "lyr_grid_2pt",
    }

    engine = PerspectiveGridEngine(client=mock_client)
    res = await engine.create_grid(
        doc_id="doc_1",
        p_type=PerspectiveType.TWO_POINT,
        horizon_y=1080.0,
        vp1_x=-500.0,
        vp2_x=4340.0,
    )
    assert res["horizon_y"] == 1080.0
    assert "grid_layer_id" in res
    assert res["perspective_type"] == "two_point"
    mock_client.send_job.assert_awaited_once()
    action = mock_client.send_job.call_args[0][0]
    assert action == "environment.create_grid"


@pytest.mark.asyncio
async def test_setup_environment_depth_planes():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "planes_created": ["00_Sky", "01_Far_BG", "02_Mid_BG", "03_Play_Area", "04_Near_FG"],
        "atmospheric_haze": True,
        "depth_group_id": "grp_depth_planes",
    }

    engine = PerspectiveGridEngine(client=mock_client)
    res = await engine.setup_environment_depth_planes(
        doc_id="doc_1",
        atmospheric_haze=True,
    )
    assert len(res["planes_created"]) == 5
    assert res["atmospheric_haze"] is True
    mock_client.send_job.assert_awaited_once()
    action = mock_client.send_job.call_args[0][0]
    assert action == "environment.setup_depth_planes"


@pytest.mark.asyncio
async def test_perspective_error_propagation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "error"
    mock_client.send_job.return_value.error = {
        "code": "DOCUMENT_ERROR",
        "message": "Invalid canvas bounds for grid",
    }

    engine = PerspectiveGridEngine(client=mock_client)
    with pytest.raises(KritaError) as exc_info:
        await engine.create_grid(
            doc_id="doc_invalid",
            p_type=PerspectiveType.ONE_POINT,
            horizon_y=500.0,
        )
    assert exc_info.value.code == ErrorCode.DOCUMENT_ERROR


def test_mcp_environment_tools_registered():
    from krita_mcp_lazy.server.app import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "krita_create_perspective_grid" in tool_names
    assert "krita_setup_environment_depth_planes" in tool_names
