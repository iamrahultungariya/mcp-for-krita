"""Perspective grid calculation, vanishing point alignment, and depth plane architecture."""

from typing import Any, Dict, List, Optional

from krita_mcp_lazy.core.errors import ErrorCode, KritaError
from krita_mcp_lazy.environment.models import PerspectiveGridSpec, PerspectiveType
from krita_mcp_lazy.transport.client import AsyncIPCClient


class PerspectiveGridEngine:
    """Manages 1-point, 2-point, and 3-point perspective grid generation and depth planes."""

    def __init__(self, client: Optional[AsyncIPCClient] = None) -> None:
        self.client = client or AsyncIPCClient()

    async def create_grid(
        self,
        doc_id: str,
        p_type: PerspectiveType = PerspectiveType.TWO_POINT,
        horizon_y: float = 1080.0,
        vp1_x: Optional[float] = None,
        vp2_x: Optional[float] = None,
        vp3_y: Optional[float] = None,
        line_density: int = 12,
        opacity: float = 0.4,
        color: str = "#00aaff",
    ) -> Dict[str, Any]:
        """Generate non-destructive perspective guide lines converging on calculated vanishing points."""
        payload = {
            "doc_id": doc_id,
            "perspective_type": p_type.value,
            "horizon_y": horizon_y,
            "vp1_x": vp1_x,
            "vp2_x": vp2_x,
            "vp3_y": vp3_y,
            "line_density": line_density,
            "opacity": opacity,
            "color": color,
        }

        resp = await self.client.send_job("environment.create_grid", payload)
        if resp.status == "error":
            err_dict = resp.error or {}
            err_code = err_dict.get("code", "DOCUMENT_ERROR")
            try:
                code_enum = ErrorCode(err_code)
            except ValueError:
                code_enum = ErrorCode.DOCUMENT_ERROR
            raise KritaError(code_enum, err_dict.get("message", "Perspective grid creation failed"))

        return resp.result or {}

    async def setup_environment_depth_planes(
        self,
        doc_id: str,
        planes: Optional[List[str]] = None,
        atmospheric_haze: bool = True,
    ) -> Dict[str, Any]:
        """Scaffold layered Z-depth groups (Sky, Far BG, Mid BG, Play Area, Near FG) with optional haze."""
        if not planes:
            planes = ["00_Sky", "01_Far_BG", "02_Mid_BG", "03_Play_Area", "04_Near_FG"]

        payload = {
            "doc_id": doc_id,
            "planes": planes,
            "atmospheric_haze": atmospheric_haze,
        }

        resp = await self.client.send_job("environment.setup_depth_planes", payload)
        if resp.status == "error":
            err_dict = resp.error or {}
            err_code = err_dict.get("code", "DOCUMENT_ERROR")
            try:
                code_enum = ErrorCode(err_code)
            except ValueError:
                code_enum = ErrorCode.DOCUMENT_ERROR
            raise KritaError(code_enum, err_dict.get("message", "Environment depth setup failed"))

        return resp.result or {}
