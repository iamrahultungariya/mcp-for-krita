import pytest
from unittest.mock import AsyncMock
from pydantic import ValidationError
from krita_mcp_lazy.painting.stroke_engine import StrokeEngine, StrokePoint
from krita_mcp_lazy.core.errors import KritaError, ErrorCode


@pytest.mark.asyncio
async def test_native_stroke_execution():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "points_drawn": 4,
        "bounding_box": [10, 10, 100, 100],
        "layer_id": "lyr_lineart",
    }

    engine = StrokeEngine(client=mock_client)
    points = [
        StrokePoint(x=10, y=10, pressure=0.2),
        StrokePoint(x=40, y=50, pressure=0.8),
        StrokePoint(x=80, y=90, pressure=0.6),
        StrokePoint(x=100, y=100, pressure=0.1),
    ]
    res = await engine.draw_stroke(doc_id="doc_1", layer_id="lyr_lineart", points=points)
    assert res["points_drawn"] == 4
    assert res["layer_id"] == "lyr_lineart"
    mock_client.send_job.assert_awaited_once()
    action = mock_client.send_job.call_args[0][0]
    assert action == "stroke.paint"


@pytest.mark.asyncio
async def test_bezier_curve_generation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "points_drawn": 11,
        "bounding_box": [0, 0, 100, 100],
        "layer_id": "lyr_lineart",
    }

    engine = StrokeEngine(client=mock_client)
    start = StrokePoint(x=0, y=0, pressure=0.1)
    end = StrokePoint(x=100, y=100, pressure=0.1)
    control1 = (25.0, 75.0)
    control2 = (75.0, 25.0)

    res = await engine.draw_bezier_curve(
        doc_id="doc_1",
        layer_id="lyr_lineart",
        start=start,
        control1=control1,
        control2=control2,
        end=end,
        steps=10,
        taper=True,
    )
    assert res["points_drawn"] == 11
    mock_client.send_job.assert_awaited_once()
    payload = mock_client.send_job.call_args[0][1]
    assert len(payload["points"]) == 11
    # Check that pressure peaked in the middle due to taper=True
    mid_pressure = payload["points"][5]["pressure"]
    assert mid_pressure > payload["points"][0]["pressure"]


def test_stroke_point_validation():
    # Valid
    p = StrokePoint(x=50.0, y=60.0, pressure=0.7)
    assert p.x == 50.0
    assert p.pressure == 0.7

    # Invalid pressure > 1.0
    with pytest.raises(ValidationError):
        StrokePoint(x=0, y=0, pressure=1.5)

    # Invalid pressure < 0.0
    with pytest.raises(ValidationError):
        StrokePoint(x=0, y=0, pressure=-0.1)


@pytest.mark.asyncio
async def test_stroke_error_propagation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "error"
    mock_client.send_job.return_value.error = {
        "code": "PAINT_ERROR",
        "message": "Target layer is locked",
    }

    engine = StrokeEngine(client=mock_client)
    points = [StrokePoint(x=10, y=10, pressure=0.5), StrokePoint(x=20, y=20, pressure=0.5)]

    with pytest.raises(KritaError) as exc_info:
        await engine.draw_stroke(doc_id="doc_1", layer_id="locked_layer", points=points)

    assert exc_info.value.code == ErrorCode.PAINT_ERROR


def test_mcp_stroke_tools_registered():
    from krita_mcp_lazy.server.app import create_mcp_server
    server = create_mcp_server()
    # Check if tools are registered
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "krita_paint_stroke" in tool_names
    assert "krita_paint_bezier_curve" in tool_names
