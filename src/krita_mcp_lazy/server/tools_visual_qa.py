"""MCP tools for visual quality control, canvas preview capture, regional inspection, scorecard evaluations, and checkpoints."""

from typing import Any, Dict, Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.transport.client import AsyncIPCClient
from krita_mcp_lazy.visual_qa.capture import VisualCaptureService
from krita_mcp_lazy.visual_qa.rollback import CheckpointManager
from krita_mcp_lazy.visual_qa.scorecard import QualityCriteria, ScorecardEvaluator

_capture_service: Optional[VisualCaptureService] = None
_checkpoint_mgr: Optional[CheckpointManager] = None
_scorecard_evaluator: Optional[ScorecardEvaluator] = None


def get_capture_service(config: Optional[KritaConfig] = None) -> VisualCaptureService:
    """Retrieve or initialize singleton VisualCaptureService."""
    global _capture_service
    if _capture_service is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _capture_service = VisualCaptureService(client=client)
    return _capture_service


def get_checkpoint_manager(config: Optional[KritaConfig] = None) -> CheckpointManager:
    """Retrieve or initialize singleton CheckpointManager."""
    global _checkpoint_mgr
    if _checkpoint_mgr is None:
        cfg = config or KritaConfig()
        client = AsyncIPCClient(host=cfg.host, port=cfg.port, token=cfg.token)
        _checkpoint_mgr = CheckpointManager(client=client)
    return _checkpoint_mgr


def get_scorecard_evaluator() -> ScorecardEvaluator:
    """Retrieve singleton ScorecardEvaluator."""
    global _scorecard_evaluator
    if _scorecard_evaluator is None:
        _scorecard_evaluator = ScorecardEvaluator()
    return _scorecard_evaluator


def register_visual_qa_tools(server: Any, config: Optional[KritaConfig] = None) -> None:
    """Register all visual capture, quality evaluation, and checkpoint tools on the MCP server."""
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

    @server.tool(
        name="krita_evaluate_visual_quality",
        description="Evaluate artwork across the 8 professional studio pillars (anatomy, lines, composition, lighting, color, reference, detail, layers) against 85/100 gate",
    )
    async def _tool_evaluate_visual_quality(
        anatomy_proportions: float,
        line_quality: float,
        composition_perspective: float,
        lighting_shading: float,
        color_materials: float,
        reference_fidelity: float,
        detail_finish: float,
        layer_editability: float,
        threshold: float = 85.0,
    ) -> Dict[str, Any]:
        evaluator = get_scorecard_evaluator()
        criteria = QualityCriteria(
            anatomy_proportions=anatomy_proportions,
            line_quality=line_quality,
            composition_perspective=composition_perspective,
            lighting_shading=lighting_shading,
            color_materials=color_materials,
            reference_fidelity=reference_fidelity,
            detail_finish=detail_finish,
            layer_editability=layer_editability,
        )
        return evaluator.evaluate(criteria=criteria, threshold=threshold)

    @server.tool(
        name="krita_create_checkpoint",
        description="Create a named checkpoint snapshot before destructive paint or layer modifications",
    )
    async def _tool_create_checkpoint(doc_id: str, label: str) -> Dict[str, Any]:
        mgr = get_checkpoint_manager(cfg)
        return await mgr.create_checkpoint(doc_id=doc_id, label=label)

    @server.tool(
        name="krita_rollback_checkpoint",
        description="Roll back the canvas state to a previously saved checkpoint snapshot upon visual QA rejection",
    )
    async def _tool_rollback_checkpoint(doc_id: str, checkpoint_id: str) -> Dict[str, Any]:
        mgr = get_checkpoint_manager(cfg)
        return await mgr.rollback_checkpoint(doc_id=doc_id, checkpoint_id=checkpoint_id)
