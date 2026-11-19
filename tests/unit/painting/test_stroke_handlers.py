import pytest
from plugins.krita_mcp_bridge.dispatcher import KritaMainThreadDispatcher
from plugins.krita_mcp_bridge.handlers_strokes import (
    register_stroke_handlers,
    render_stroke_points_pil,
    hex_to_rgba,
)
from plugins.krita_mcp_bridge.handlers_canvas import register_canvas_handlers
from plugins.krita_mcp_bridge.handlers_painting import register_painting_handlers
from krita_mcp_lazy.core.schemas import JobRequest, JobStatus


def test_hex_to_rgba_parsing():
    assert hex_to_rgba("#ff0000") == (255, 0, 0, 255)
    assert hex_to_rgba("#00ff00", opacity=0.5) == (0, 255, 0, 127)
    assert hex_to_rgba("#12345678") == (0x12, 0x34, 0x56, 0x78)
    assert hex_to_rgba("#fff") == (255, 255, 255, 255)


def test_render_stroke_points_pil_stamping():
    bbox = [0, 0, 100, 100]
    points = [
        {"x": 10, "y": 10, "pressure": 0.5},
        {"x": 50, "y": 50, "pressure": 1.0},
        {"x": 90, "y": 90, "pressure": 0.2},
    ]
    color_rgba = (255, 0, 0, 255)
    raw_bytes = render_stroke_points_pil(bbox, points, color_rgba, base_size=10.0)
    assert len(raw_bytes) == 100 * 100 * 4
    # Ensure non-zero alpha pixels were stamped
    has_colored_pixels = any(raw_bytes[i + 3] > 0 for i in range(0, len(raw_bytes), 4))
    assert has_colored_pixels is True


def test_stroke_handler_dispatch():
    dispatcher = KritaMainThreadDispatcher()
    register_stroke_handlers(dispatcher)

    req = JobRequest(
        action="stroke.paint",
        params={
            "doc_id": "test_doc",
            "layer_id": "test_layer",
            "points": [
                {"x": 20, "y": 20, "pressure": 0.5},
                {"x": 80, "y": 80, "pressure": 0.8},
            ],
            "color": "#ff00aa",
            "size": 12.0,
        },
    )
    dispatcher.enqueue(req)
    processed = dispatcher.process_pending_jobs()
    assert processed == 1

    resp = dispatcher.get_result(req.job_id)
    assert resp is not None
    assert resp.status == JobStatus.SUCCESS
    assert resp.result["points_drawn"] == 2
    assert resp.result["rendered"] is True
    assert resp.result["size"] == 12.0
    assert resp.result["color"] == "#ff00aa"
    assert resp.result["bounding_box"][0] <= 20
    assert resp.result["bounding_box"][2] >= 80


def test_canvas_bounds_and_sample_pixel_handlers():
    dispatcher = KritaMainThreadDispatcher()
    register_canvas_handlers(dispatcher)

    # Test canvas.bounds
    req_bounds = JobRequest(action="canvas.bounds", params={"doc_id": "doc_1"})
    dispatcher.enqueue(req_bounds)
    dispatcher.process_pending_jobs()
    resp_bounds = dispatcher.get_result(req_bounds.job_id)
    assert resp_bounds.status == JobStatus.SUCCESS
    assert resp_bounds.result["x"] == 0
    assert resp_bounds.result["y"] == 0
    assert resp_bounds.result["width"] > 0

    # Test canvas.sample_pixel
    req_sample = JobRequest(action="canvas.sample_pixel", params={"doc_id": "doc_1", "x": 10, "y": 10})
    dispatcher.enqueue(req_sample)
    dispatcher.process_pending_jobs()
    resp_sample = dispatcher.get_result(req_sample.job_id)
    assert resp_sample.status == JobStatus.SUCCESS
    assert "sampled_color" in resp_sample.result
