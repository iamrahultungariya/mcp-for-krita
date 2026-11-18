"""Pydantic schemas and enums for visual art direction and composition specs."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class CompositionRule(str, Enum):
    """Composition frameworks for layout planning."""

    RULE_OF_THIRDS = "RULE_OF_THIRDS"
    GOLDEN_RATIO = "GOLDEN_RATIO"
    CENTER_FOCUS = "CENTER_FOCUS"
    DIAGONAL = "DIAGONAL"
    TRIANGLE = "TRIANGLE"


class StyleProfile(str, Enum):
    """Aesthetic art style profiles."""

    ANIME_CINEMATIC = "ANIME_CINEMATIC"
    STYLIZED_TOON = "STYLIZED_TOON"
    WESTERN_COMIC = "WESTERN_COMIC"
    CONCEPT_ART = "CONCEPT_ART"
    PAINTERLY = "PAINTERLY"


class CanvasDimensions(BaseModel):
    """Pixel dimensions and print resolution."""

    width: int = Field(gt=0)
    height: int = Field(gt=0)
    dpi: int = Field(default=300, gt=0)


class LightSource(BaseModel):
    """Directional or ambient illumination source."""

    role: str
    direction: str
    color_temp_k: int
    intensity: float = Field(ge=0.0, le=2.0)
    color_hex: str


class LightingScheme(BaseModel):
    """Standard 3-point lighting plus ambient bounce scheme."""

    key_light: LightSource
    fill_light: LightSource
    rim_light: LightSource
    ambient_bounce: Optional[str] = None


class DepthPlanes(BaseModel):
    """Z-depth structural elements."""

    foreground: List[str] = Field(default_factory=list)
    midground: List[str] = Field(default_factory=list)
    background: List[str] = Field(default_factory=list)


class VisualProductionSpec(BaseModel):
    """Complete art direction and production plan for a Krita artwork."""

    subject: str
    style: StyleProfile
    composition: CompositionRule
    aspect_ratio: str
    dimensions: CanvasDimensions
    color_palette: List[str] = Field(default_factory=list)
    depth_plan: DepthPlanes
    layer_blueprint: List[str] = Field(default_factory=list)
    lighting: LightingScheme
    notes: Optional[str] = None
