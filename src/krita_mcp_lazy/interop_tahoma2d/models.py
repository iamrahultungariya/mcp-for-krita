"""Data models and schemas for Tahoma2D cutout asset manifests and pivot metadata."""

from typing import List, Optional
from pydantic import BaseModel, Field


class CutoutPartMeta(BaseModel):
    """Metadata for a single cutout body part or prop element."""

    name: str
    file: str
    pivot_x: float = Field(default=0.5, ge=0.0, le=1.0)
    pivot_y: float = Field(default=0.5, ge=0.0, le=1.0)
    z_order: int = 0
    bounds: Optional[List[int]] = None


class CutoutManifest(BaseModel):
    """Complete character cutout manifest defining parts, hierarchy, and canvas coordinates."""

    character: str
    parts: List[CutoutPartMeta] = Field(default_factory=list)
    canvas_width: int = Field(default=1920, gt=0)
    canvas_height: int = Field(default=1080, gt=0)
