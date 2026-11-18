"""MCP tools for real-time telemetry, stage duration tracing, and memory profiling."""

from typing import Any, Dict, Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.telemetry.tracker import OperationTracker

_tracker: Optional[OperationTracker] = None


def get_operation_tracker() -> OperationTracker:
    """Retrieve singleton OperationTracker."""
    global _tracker
    if _tracker is None:
        _tracker = OperationTracker()
    return _tracker


def register_telemetry_tools(server: Any, config: Optional[KritaConfig] = None) -> None:
    """Register all telemetry reporting and profiling tools on the MCP server."""

    @server.tool(
        name="krita_get_telemetry_report",
        description="Query real monotonic wall-clock timing, stage latency, and RAM memory footprint metrics",
    )
    async def _tool_get_telemetry_report() -> Dict[str, Any]:
        tracker = get_operation_tracker()
        return tracker.get_summary_report()

    @server.tool(
        name="krita_reset_telemetry",
        description="Reset and clear all accumulated telemetry metrics for a new benchmark run",
    )
    async def _tool_reset_telemetry() -> Dict[str, Any]:
        tracker = get_operation_tracker()
        tracker.reset()
        return {"status": "reset", "metrics_cleared": True}
