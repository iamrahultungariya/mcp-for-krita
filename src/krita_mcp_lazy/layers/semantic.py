"""Semantic layer scaffolding and flexible production hierarchy generator."""

import logging
from typing import Any, Dict, List, Optional

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.core.schemas import JobRequest, JobStatus
from krita_mcp_lazy.transport.client import AsyncIPCClient

logger = logging.getLogger(__name__)

ARCHETYPE_PRESETS: Dict[str, Dict[str, Any]] = {
    "character_production": {
        "Rough_Sketch": ["Gesture", "Anatomy_Rough"],
        "LineArt": ["Outlines", "Internal_Lines"],
        "Color_Base": ["Skin_Base", "Hair_Base", "Costume_Base"],
        "Render_Shading": ["Ambient_Occlusion", "Key_Shadows", "Highlights"],
        "FX_Atmosphere": ["Rim_Light", "Color_Filter"],
    },
    "environment_depth": {
        "Sky_Background": ["Sky_Gradient", "Distant_Clouds", "Horizon"],
        "Far_Background": ["Mountains", "Silhouette_Buildings"],
        "Midground": ["Architecture_Structures", "Props_Midground"],
        "Foreground": ["Hero_Ground", "Foliage_Framing"],
        "Atmosphere_VFX": ["Fog_Layers", "Volumetric_Light"],
    },
    "prop_asset": {
        "Reference_Blockout": ["Scale_Reference", "Rough_Silhouette"],
        "LineArt": ["Contour_Lines", "Seams_Bolts"],
        "Materials": ["Base_Metal_Wood", "Decals", "Dirt_Decay"],
        "Highlights_Shadows": ["Contact_Shadow", "Specular_Pings"],
    },
}


class SemanticLayerOrganizer:
    """Orchestrates structured semantic layer hierarchies for professional art workflows."""

    def __init__(self, client: AsyncIPCClient) -> None:
        self.client = client

    def _ensure_success(self, resp: Any, default_message: str) -> dict[str, Any]:
        """Validate response status or raise KritaError with proper taxonomy code."""
        if resp.status != JobStatus.SUCCESS:
            code = ErrorCode.LAYER_ERROR
            if resp.error_code:
                for member in ErrorCode:
                    if member.value == resp.error_code:
                        code = member
                        break
            raise KritaError(
                code=code,
                message=resp.error or default_message,
                job_id=resp.job_id,
            )
        return resp.result or {}

    async def scaffold_hierarchy(
        self,
        doc_id: str,
        schema: Optional[Dict[str, Any]] = None,
        preset: Optional[str] = None,
    ) -> dict[str, Any]:
        """Scaffold customizable layer and group structure on the target document."""
        if schema is not None and not schema:
            raise KritaError(ErrorCode.LAYER_ERROR, "Invalid hierarchy schema: empty dictionary")

        target_schema = schema
        if not target_schema:
            if not preset:
                raise KritaError(ErrorCode.LAYER_ERROR, "Either 'schema' or 'preset' must be specified")
            if preset not in ARCHETYPE_PRESETS:
                raise KritaError(
                    ErrorCode.LAYER_ERROR,
                    f"Unknown archetype preset '{preset}'. Available: {list(ARCHETYPE_PRESETS.keys())}",
                )
            target_schema = ARCHETYPE_PRESETS[preset]

        params = {
            "doc_id": doc_id,
            "schema": target_schema,
            "preset": preset,
        }
        req = JobRequest(action="layer.scaffold_semantic", params=params)
        resp = await self.client.send_job(req)
        return self._ensure_success(resp, f"Failed to scaffold semantic structure in doc '{doc_id}'")
