"""MCP tools for visual quality control, canvas preview capture, and regional inspection."""

from typing import Any, Dict, Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.transport.client import AsyncIPCClient
from krita_mcp_lazy.visual_qa.capture import VisualCaptureService

_capture_service: Optional[VisualCaptureService] = None


def get_capture_service(config: Optional[KritaConfig] = None) -> VisualCaptureService:
    """Retrieve or initialize singleton VisualCaptureService."""
    global _capture_service
    if _capture_service is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _capture_service = VisualCaptureService(client=client)
    return _capture_service


def register_visual_qa_tools(server: Any, config: Optional[KritaConfig] = None) -> None:
    """Register all visual capture and inspection tools on the MCP server."""
    cfg = config or KritaConfig()

    @server.tool(
        name="krita_capture_preview",
        description="Capture full canvas projection as base64 PNG image for visual inspection and multi-modal LLM evaluation",
    )
    async def _tool_capture_preview(
        doc_id: str,
        max_dimension: int = 1920,
        format: str = "PNG",
    ) -> Dict[str, Any]:
        svc = get_capture_service(cfg)
        return await svc.capture_canvas(
            doc_id=doc_id,
            max_dimension=max_dimension,
            format=format,
        )

    @server.tool(
        name="krita_extract_region",
        description="Extract a cropped region bounding box from canvas or specific layer as base64 PNG",
    )
    async def _tool_extract_region(
        doc_id: str,
        x: int,
        y: int,
        width: int,
        height: int,
        layer_id: Optional[str] = None,
        format: str = "PNG",
    ) -> Dict[str, Any]:
        svc = get_capture_service(cfg)
        return await svc.extract_region(
            doc_id=doc_id,
            x=x,
            y=y,
            width=width,
            height=height,
            layer_id=layer_id,
            format=format,
        )
