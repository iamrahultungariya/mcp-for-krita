"""MCP tools for Krita document management."""

from typing import Any, List, Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.document.models import BitDepth, ColorModel, DocumentSpec
from krita_mcp_lazy.document.service import DocumentService
from krita_mcp_lazy.transport.client import AsyncIPCClient

_doc_service: Optional[DocumentService] = None


def get_document_service(config: Optional[KritaConfig] = None) -> DocumentService:
    """Retrieve or initialize singleton DocumentService instance."""
    global _doc_service
    if _doc_service is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _doc_service = DocumentService(client=client)
    return _doc_service


def register_document_tools(server: Any, config: Optional[KritaConfig] = None) -> None:
    """Register all document CRUD and inspection tools on the MCP server."""
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
