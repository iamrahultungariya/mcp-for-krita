"""Native stroke generation, pressure dynamics, and vector path interpolation."""

import math
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from krita_mcp_lazy.core.errors import ErrorCode, KritaError, check_job_response
from krita_mcp_lazy.transport.client import AsyncIPCClient


class StrokePoint(BaseModel):
    """Single point in a dynamic brush stroke with pressure and tilt dynamics."""

    x: float
    y: float
    pressure: float = Field(default=0.5, ge=0.0, le=1.0)
    tilt_x: float = Field(default=0.0, ge=-1.0, le=1.0)
    tilt_y: float = Field(default=0.0, ge=-1.0, le=1.0)
    time_offset_ms: Optional[float] = None


class StrokeEngine:
    """Orchestrates stroke generation, Bézier curve interpolation, and dispatch."""

    def __init__(self, client: Optional[AsyncIPCClient] = None) -> None:
        self.client = client or AsyncIPCClient()

    async def draw_stroke(
        self,
        doc_id: str,
        layer_id: str,
        points: List[StrokePoint],
        brush_preset: Optional[str] = None,
        color: Optional[str] = None,
        opacity: Optional[float] = None,
        size: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Paint an array of sequential pressure-sensitive points onto a layer."""
        if not points:
            raise ValueError("Stroke requires at least one point")

        payload = {
            "doc_id": doc_id,
            "layer_id": layer_id,
            "points": [p.model_dump() for p in points],
            "brush_preset": brush_preset,
            "color": color,
            "opacity": opacity,
            "size": size,
        }

        resp = await self.client.send_job("stroke.paint", payload)
        return check_job_response(resp, ErrorCode.PAINT_ERROR, "Stroke drawing failed")

    async def draw_bezier_curve(
        self,
        doc_id: str,
        layer_id: str,
        start: StrokePoint,
        control1: Tuple[float, float],
        control2: Tuple[float, float],
        end: StrokePoint,
        steps: int = 20,
        taper: bool = True,
        brush_preset: Optional[str] = None,
        color: Optional[str] = None,
        opacity: Optional[float] = None,
        size: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Generate a smooth cubic Bézier curve with pressure taper and paint it."""
        if steps < 1:
            steps = 1

        points: List[StrokePoint] = []
        p0 = (start.x, start.y)
        p1 = control1
        p2 = control2
        p3 = (end.x, end.y)

        for i in range(steps + 1):
            t = i / float(steps)
            # Cubic Bézier formula
            u = 1.0 - t
            tt = t * t
            uu = u * u
            uuu = uu * u
            ttt = tt * t

            x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
            y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]

            if taper:
                # Natural inking taper: blend linear base with sine envelope
                base_p = (1.0 - t) * start.pressure + t * end.pressure
                envelope = math.sin(math.pi * t)
                # Ensure peak pressure in middle is emphasized
                pressure = max(0.05, min(1.0, base_p * 0.3 + 0.7 * envelope))
            else:
                pressure = (1.0 - t) * start.pressure + t * end.pressure

            points.append(
                StrokePoint(
                    x=round(x, 2),
                    y=round(y, 2),
                    pressure=round(pressure, 3),
                    tilt_x=(1.0 - t) * start.tilt_x + t * end.tilt_x,
                    tilt_y=(1.0 - t) * start.tilt_y + t * end.tilt_y,
                )
            )

        return await self.draw_stroke(
            doc_id=doc_id,
            layer_id=layer_id,
            points=points,
            brush_preset=brush_preset,
            color=color,
            opacity=opacity,
            size=size,
        )
