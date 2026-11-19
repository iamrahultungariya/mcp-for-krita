"""Data models for studio cel decomposition, vector strokes, and trapped color flats."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


@dataclass
class TaperedStroke:
    """Continuous vector lineart stroke with pressure dynamics (tapered tips)."""

    stroke_id: str
    points: List[Tuple[float, float]]
    pressures: List[float]
    brush_preset: str = "f)_Ink-3_Gpen"
    color: str = "#000000"
    base_width: float = 3.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stroke_id": self.stroke_id,
            "points": [[round(x, 2), round(y, 2)] for x, y in self.points],
            "pressures": [round(p, 3) for p in self.pressures],
            "brush_preset": self.brush_preset,
            "color": self.color,
            "base_width": self.base_width,
        }


@dataclass
class FlatRegion:
    """Trapped color flat segment with binary mask and dominant color."""

    region_id: str
    color_hex: str
    mask: np.ndarray
    bbox: Tuple[int, int, int, int]
    pixel_count: int = 0


@dataclass
class ShadowRegion:
    """Alpha-locked cel shadow region for Multiply blend layers."""

    region_id: str
    mask: np.ndarray
    color_hex: str = "#201830"
    opacity: float = 0.5


@dataclass
class HighlightRegion:
    """Specular and rim highlight region for Screen/Addition blend layers."""

    region_id: str
    mask: np.ndarray
    color_hex: str = "#FFF0C0"
    opacity: float = 0.7


@dataclass
class CelArtDecomposition:
    """Full decomposition of an anime/illustration into vector strokes, trapped flats, and lighting."""

    vector_strokes: List[TaperedStroke] = field(default_factory=list)
    flat_regions: List[FlatRegion] = field(default_factory=list)
    cel_shadows: List[ShadowRegion] = field(default_factory=list)
    highlights: List[HighlightRegion] = field(default_factory=list)
    lineart_mask: np.ndarray = field(default_factory=lambda: np.zeros((1, 1), dtype=np.uint8))
    composite_flats: Optional[np.ndarray] = None
    composite_lineart: Optional[np.ndarray] = None
    composite_shadows: Optional[np.ndarray] = None
    composite_highlights: Optional[np.ndarray] = None
    width: int = 0
    height: int = 0
