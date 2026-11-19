"""Tests for Krita studio native alpha-inheritance, SVG vector layer injection, and BGRA pixel handling."""

import pytest
from krita_mcp_lazy.core.schemas import JobRequest, JobStatus
from plugins.krita_mcp_bridge.dispatcher import KritaMainThreadDispatcher
from plugins.krita_mcp_bridge.handlers_layers import register_layer_handlers


def _run_job(dispatcher: KritaMainThreadDispatcher, action: str, params: dict):
    req = JobRequest(action=action, params=params)
    dispatcher.enqueue(req)
    dispatcher.process_pending_jobs()
    resp = dispatcher.get_result(req.job_id)
    return resp


def test_layer_set_inherit_alpha_handler():
    """Verify layer.set_inherit_alpha updates clipping mask flag on target layer."""
    dispatcher = KritaMainThreadDispatcher()
    register_layer_handlers(dispatcher)

    # 1. Create a base layer
    resp_create = _run_job(
        dispatcher,
        "layer.create",
        {"doc_id": "doc_test_studio", "name": "Face_Shade", "layer_type": "paintLayer"},
    )
    assert resp_create.status == JobStatus.SUCCESS

    # 2. Set inherit alpha to True
    resp_alpha = _run_job(
        dispatcher,
        "layer.set_inherit_alpha",
        {"doc_id": "doc_test_studio", "layer_name": "Face_Shade", "inherit_alpha": True},
    )
    assert resp_alpha.status == JobStatus.SUCCESS
    assert resp_alpha.result.get("updated") is True
    assert resp_alpha.result.get("inherit_alpha") is True

    # 3. Check layer.tree inspection preserves inherit_alpha property
    resp_tree = _run_job(dispatcher, "layer.tree", {"doc_id": "doc_test_studio"})
    layers = resp_tree.result.get("layers", [])
    target = next((l for l in layers if l["name"] == "Face_Shade"), None)
    assert target is not None
    assert target.get("inherit_alpha") is True


def test_layer_inject_svg_handler():
    """Verify layer.inject_svg creates/targets vectorLayer and injects SVG shapes."""
    dispatcher = KritaMainThreadDispatcher()
    register_layer_handlers(dispatcher)

    svg_data = '<svg width="200" height="200"><path d="M 10 10 L 90 90" stroke="black" stroke-width="3"/></svg>'
    resp = _run_job(
        dispatcher,
        "layer.inject_svg",
        {
            "doc_id": "doc_test_studio",
            "layer_name": "Vector_Lineart",
            "svg_string": svg_data,
        },
    )
    assert resp.status == JobStatus.SUCCESS
    assert resp.result.get("svg_injected") is True
    assert resp.result.get("layer_name") == "Vector_Lineart"
    assert resp.result.get("type") == "vectorLayer"
