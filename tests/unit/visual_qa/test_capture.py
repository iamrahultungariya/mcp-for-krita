import pytest
from unittest.mock import AsyncMock

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.visual_qa.capture import VisualCaptureService

SAMPLE_PNG_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="


@pytest.mark.asyncio
async def test_canvas_preview_capture():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "image_base64": SAMPLE_PNG_B64,
        "width": 1920,
        "height": 1080,
        "format": "PNG",
        "doc_id": "doc_1",
    }

    svc = VisualCaptureService(client=mock_client)
    preview = await svc.capture_canvas(doc_id="doc_1", max_dimension=1920)
    assert preview["format"] == "PNG"
    assert preview["width"] == 1920
    assert len(preview["image_base64"]) > 0
    mock_client.send_job.assert_awaited_once()
    action = mock_client.send_job.call_args[0][0]
    assert action == "visual.capture_canvas"


@pytest.mark.asyncio
async def test_extract_canvas_region():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "success"
    mock_client.send_job.return_value.result = {
        "image_base64": SAMPLE_PNG_B64,
        "x": 200,
        "y": 150,
        "width": 512,
        "height": 512,
        "format": "PNG",
        "doc_id": "doc_1",
    }

    svc = VisualCaptureService(client=mock_client)
    region = await svc.extract_region(
        doc_id="doc_1",
        x=200,
        y=150,
        width=512,
        height=512,
    )
    assert region["x"] == 200
    assert region["width"] == 512
    assert region["format"] == "PNG"
    mock_client.send_job.assert_awaited_once()
    action = mock_client.send_job.call_args[0][0]
    assert action == "visual.extract_region"


@pytest.mark.asyncio
async def test_capture_error_propagation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value.status = "error"
    mock_client.send_job.return_value.error = {
        "code": "DOCUMENT_ERROR",
        "message": "Canvas projection is not ready",
    }

    svc = VisualCaptureService(client=mock_client)
    with pytest.raises(KritaError) as exc_info:
        await svc.capture_canvas(doc_id="doc_invalid")
    assert exc_info.value.code == ErrorCode.DOCUMENT_ERROR


def test_mcp_visual_capture_tools_registered():
    from krita_mcp_lazy.server.app import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "krita_capture_preview" in tool_names
    assert "krita_extract_region" in tool_names
