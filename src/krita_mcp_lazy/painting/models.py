"""Domain models for brushes, presets, colors, and stroke parameters."""

from typing import Optional
from pydantic import BaseModel, Field


class ColorRGB(BaseModel):
    """8-bit RGBA color representation."""

    r: int = Field(default=0, ge=0, le=255)
    g: int = Field(default=0, ge=0, le=255)
    b: int = Field(default=0, ge=0, le=255)
    a: int = Field(default=255, ge=0, le=255)


class BrushPresetInfo(BaseModel):
    """Metadata describing a Krita brush preset resource."""

    name: str = Field(..., description="Unique brush preset identifier")
    category: str = Field(default="General", description="Brush category / tag")
    engine: str = Field(default="Pixel", description="Krita paint op engine (e.g. Pixel, ColorSmudge, Curve)")
    description: Optional[str] = Field(default=None, description="Optional description or tooltip")


class BrushConfig(BaseModel):
    """Configurable runtime parameters for the active painting brush."""

    size: float = Field(default=10.0, gt=0.0, le=1000.0, description="Brush diameter in pixels")
    opacity: float = Field(default=1.0, ge=0.0, le=1.0, description="Brush opacity between 0.0 and 1.0")
    flow: float = Field(default=1.0, ge=0.0, le=1.0, description="Brush paint flow rate between 0.0 and 1.0")
    color: Optional[str] = Field(default="#000000", description="Foreground painting color (Hex or CSS format)")
    background_color: Optional[str] = Field(default="#ffffff", description="Background color (Hex or CSS format)")
