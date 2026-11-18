import pytest
from unittest.mock import AsyncMock
from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobResponse, JobStatus
from krita_mcp_lazy.document.canvas import CanvasService
from krita_mcp_lazy.server.app import create_mcp_server


@pytest.mark.asyncio
async def test_canvas_resize_and_sample():
    mock_client = AsyncMock()
    mock_client.send_job.side_effect = [
        JobResponse(
            job_id="job_resize",
            status=JobStatus.SUCCESS,
            result={"doc_id": "doc_1", "width": 2560, "height": 1440, "resized": True},
        ),
        JobResponse(
            job_id="job_sample",
            status=JobStatus.SUCCESS,
            result={"sampled_color": {"r": 255, "g": 128, "b": 0, "a": 255}},
        ),
    ]

    canvas_svc = CanvasService(client=mock_client)
    resize_res = await canvas_svc.resize_canvas(doc_id="doc_1", width=2560, height=1440)
    assert resize_res["resized"] is True
    assert resize_res["width"] == 2560

    sample_res = await canvas_svc.sample_pixel(doc_id="doc_1", x=100, y=200)
    assert sample_res["r"] == 255
    assert sample_res["g"] == 128
    assert sample_res["b"] == 0
    assert sample_res["a"] == 255


@pytest.mark.asyncio
async def test_canvas_crop_and_rotate():
    mock_client = AsyncMock()
    mock_client.send_job.side_effect = [
        JobResponse(
            job_id="job_crop",
            status=JobStatus.SUCCESS,
            result={"doc_id": "doc_1", "x": 50, "y": 50, "width": 800, "height": 600, "cropped": True},
        ),
        JobResponse(
            job_id="job_rotate",
            status=JobStatus.SUCCESS,
            result={"doc_id": "doc_1", "angle_degrees": 90.0, "rotated": True},
        ),
    ]

    canvas_svc = CanvasService(client=mock_client)
    crop_res = await canvas_svc.crop_canvas(doc_id="doc_1", x=50, y=50, width=800, height=600)
    assert crop_res["cropped"] is True

    rotate_res = await canvas_svc.rotate_canvas(doc_id="doc_1", angle_degrees=90.0)
    assert rotate_res["rotated"] is True


@pytest.mark.asyncio
async def test_canvas_bounds():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="job_bounds",
        status=JobStatus.SUCCESS,
        result={"doc_id": "doc_1", "width": 1920, "height": 1080, "x": 0, "y": 0},
    )

    canvas_svc = CanvasService(client=mock_client)
    bounds = await canvas_svc.get_canvas_bounds(doc_id="doc_1")
    assert bounds["width"] == 1920
    assert bounds["height"] == 1080


@pytest.mark.asyncio
async def test_canvas_error_propagation():
    mock_client = AsyncMock()
    mock_client.send_job.return_value = JobResponse(
        job_id="fail_job",
        status=JobStatus.FAILED,
        error="Invalid dimensions for canvas resize",
        error_code=ErrorCode.DOCUMENT_ERROR.value,
    )

    canvas_svc = CanvasService(client=mock_client)
    with pytest.raises(KritaError) as exc_info:
        await canvas_svc.resize_canvas(doc_id="doc_1", width=-100, height=1080)
    assert exc_info.value.code == ErrorCode.DOCUMENT_ERROR
    assert "Invalid dimensions" in exc_info.value.message


@pytest.mark.asyncio
async def test_canvas_mcp_tools_registered():
    server = create_mcp_server()
    tool_names = [tool.name for tool in await server.list_tools()]

    assert "krita_resize_canvas" in tool_names
    assert "krita_crop_canvas" in tool_names
    assert "krita_rotate_canvas" in tool_names
    assert "krita_get_canvas_bounds" in tool_names
    assert "krita_sample_pixel" in tool_names
