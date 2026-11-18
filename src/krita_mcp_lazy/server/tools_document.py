"""MCP tools for Krita document and canvas management."""

from typing import Any, List, Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.document.canvas import CanvasService
from krita_mcp_lazy.document.models import BitDepth, ColorModel, DocumentSpec
from krita_mcp_lazy.document.service import DocumentService
from krita_mcp_lazy.transport.client import AsyncIPCClient

_doc_service: Optional[DocumentService] = None
_canvas_service: Optional[CanvasService] = None


def get_document_service(config: Optional[KritaConfig] = None) -> DocumentService:
    """Retrieve or initialize singleton DocumentService instance."""
    global _doc_service
    if _doc_service is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _doc_service = DocumentService(client=client)
    return _doc_service


def get_canvas_service(config: Optional[KritaConfig] = None) -> CanvasService:
    """Retrieve or initialize singleton CanvasService instance."""
    global _canvas_service
    if _canvas_service is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _canvas_service = CanvasService(client=client)
    return _canvas_service


def register_document_tools(server: Any, config: Optional[KritaConfig] = None) -> None:
    """Register all document CRUD, inspection, and canvas geometric tools on the MCP server."""
    cfg = config or KritaConfig()

    @server.tool(
        name="krita_create_document",
        description="Create a new Krita document with dimensions, DPI, color model (RGBA, CMYK, GRAY), and bit depth (U8, U16, F32)",
    )
    async def _tool_create_document(
        width: int = 1920,
        height: int = 1080,
        name: str = "Artwork",
        resolution_dpi: float = 300.0,
        color_model: str = "RGBA",
        bit_depth: str = "U8",
        color_profile: str = "sRGB-elle-V2-srgbtrc.icc",
    ) -> dict[str, Any]:
        svc = get_document_service(cfg)
        spec = DocumentSpec(
            name=name,
            width=width,
            height=height,
            resolution_dpi=resolution_dpi,
            color_model=ColorModel(color_model.upper()),
            bit_depth=BitDepth(bit_depth.upper()),
            color_profile=color_profile,
        )
        return await svc.create_document(spec)

    @server.tool(
        name="krita_open_document",
        description="Open an existing .kra or supported image file into Krita",
    )
    async def _tool_open_document(file_path: str) -> dict[str, Any]:
        svc = get_document_service(cfg)
        return await svc.open_document(file_path)

    @server.tool(
        name="krita_save_document",
        description="Save an open Krita document to .kra or export to target image format",
    )
    async def _tool_save_document(
        doc_id: str,
        file_path: Optional[str] = None,
        export_format: str = "kra",
    ) -> dict[str, Any]:
        svc = get_document_service(cfg)
        return await svc.save_document(doc_id=doc_id, file_path=file_path, export_format=export_format)

    @server.tool(
        name="krita_close_document",
        description="Close an open Krita document",
    )
    async def _tool_close_document(doc_id: str, force: bool = False) -> dict[str, Any]:
        svc = get_document_service(cfg)
        return await svc.close_document(doc_id=doc_id, force=force)

    @server.tool(
        name="krita_inspect_document",
        description="Inspect document properties, active layer, canvas dimensions, and color management",
    )
    async def _tool_inspect_document(doc_id: Optional[str] = None) -> dict[str, Any]:
        svc = get_document_service(cfg)
        return await svc.inspect_document(doc_id)

    @server.tool(
        name="krita_list_documents",
        description="List all currently open documents in the active Krita instance",
    )
    async def _tool_list_documents() -> List[dict[str, Any]]:
        svc = get_document_service(cfg)
        return await svc.list_documents()

    # --- Canvas Operations ---

    @server.tool(
        name="krita_resize_canvas",
        description="Resize canvas dimensions with optional x/y offset anchors",
    )
    async def _tool_resize_canvas(
        doc_id: str,
        width: int,
        height: int,
        x_offset: int = 0,
        y_offset: int = 0,
    ) -> dict[str, Any]:
        canvas_svc = get_canvas_service(cfg)
        return await canvas_svc.resize_canvas(
            doc_id=doc_id,
            width=width,
            height=height,
            x_offset=x_offset,
            y_offset=y_offset,
        )

    @server.tool(
        name="krita_crop_canvas",
        description="Crop the canvas to a rectangular bounding box (x, y, width, height)",
    )
    async def _tool_crop_canvas(
        doc_id: str,
        x: int,
        y: int,
        width: int,
        height: int,
    ) -> dict[str, Any]:
        canvas_svc = get_canvas_service(cfg)
        return await canvas_svc.crop_canvas(doc_id=doc_id, x=x, y=y, width=width, height=height)

    @server.tool(
        name="krita_rotate_canvas",
        description="Rotate the entire canvas image by a specified angle in degrees",
    )
    async def _tool_rotate_canvas(doc_id: str, angle_degrees: float) -> dict[str, Any]:
        canvas_svc = get_canvas_service(cfg)
        return await canvas_svc.rotate_canvas(doc_id=doc_id, angle_degrees=angle_degrees)

    @server.tool(
        name="krita_get_canvas_bounds",
        description="Retrieve the current pixel bounds, dimensions, and resolution of the active or specified canvas",
    )
    async def _tool_get_canvas_bounds(doc_id: Optional[str] = None) -> dict[str, Any]:
        canvas_svc = get_canvas_service(cfg)
        return await canvas_svc.get_canvas_bounds(doc_id=doc_id)

    @server.tool(
        name="krita_sample_pixel",
        description="Sample exact RGBA color values at (x, y) coordinates from the canvas or specific layer",
    )
    async def _tool_sample_pixel(
        doc_id: str,
        x: int,
        y: int,
        layer_name: Optional[str] = None,
    ) -> dict[str, Any]:
        canvas_svc = get_canvas_service(cfg)
        return await canvas_svc.sample_pixel(doc_id=doc_id, x=x, y=y, layer_name=layer_name)
