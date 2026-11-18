import time
import pytest
from krita_mcp_lazy.telemetry.tracker import OperationTracker, StageMetric


def test_wall_clock_tracking():
    tracker = OperationTracker()
    with tracker.track_stage("painting_stroke", points=10):
        time.sleep(0.06)

    metrics = tracker.get_stage_metrics("painting_stroke")
    assert len(metrics) == 1
    assert metrics[0].duration_ms >= 45.0  # Real wall clock, monotonic timer
    assert metrics[0].ram_usage_mb > 0.0
    assert metrics[0].metadata["points"] == 10


def test_telemetry_summary_and_reset():
    tracker = OperationTracker()
    with tracker.track_stage("document_create"):
        time.sleep(0.01)
    with tracker.track_stage("layer_create"):
        time.sleep(0.01)

    report = tracker.get_summary_report()
    assert report["total_operations"] >= 2
    assert "document_create" in report["stages"]
    assert "layer_create" in report["stages"]

    tracker.reset()
    assert len(tracker.get_stage_metrics()) == 0
    empty_report = tracker.get_summary_report()
    assert empty_report["total_operations"] == 0


def test_mcp_telemetry_tools_registered():
    from krita_mcp_lazy.server.app import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "krita_get_telemetry_report" in tool_names
    assert "krita_reset_telemetry" in tool_names
