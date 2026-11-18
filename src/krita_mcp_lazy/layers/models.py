"""Domain models, enums, and specifications for Krita layer hierarchy."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class LayerType(str, Enum):
    """Supported layer types in Krita."""

    PAINT = "paint"
    GROUP = "group"
    VECTOR = "vector"
    FILE = "file"
    CLONE = "clone"
    FILTER = "filter"
    FILL = "fill"


class BlendingMode(str, Enum):
    """Standard layer blending modes."""

    NORMAL = "normal"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    DARKEN = "darken"
    LIGHTEN = "lighten"
    COLOR_DODGE = "color_dodge"
    COLOR_BURN = "color_burn"
    HARD_LIGHT = "hard_light"
    SOFT_LIGHT = "soft_light"
    DIFFERENCE = "difference"
    ADD = "add"


class ReorderPosition(str, Enum):
    """Relative placement position when reordering layers."""

    ABOVE = "above"
    BELOW = "below"
    INSIDE = "inside"


class LayerSpec(BaseModel):
    """Specification parameters for creating a new layer or group."""

    name: str = Field(..., description="Unique or descriptive layer name")
    type: LayerType = Field(default=LayerType.PAINT, description="Type of layer to create")
    opacity: int = Field(default=255, ge=0, le=255, description="Layer opacity from 0 (transparent) to 255 (opaque)")
    blending_mode: BlendingMode = Field(default=BlendingMode.NORMAL, description="Composite blending mode")
    visible: bool = Field(default=True, description="Initial visibility state")
    locked: bool = Field(default=False, description="Initial lock state")
    parent_group: Optional[str] = Field(default=None, description="Optional parent group name or ID")


class LayerNode(BaseModel):
    """Node in the recursive layer tree hierarchy."""

    id: str
    name: str
    type: str
    opacity: int = 255
    blending_mode: str = "normal"
    visible: bool = True
    locked: bool = False
    children: List["LayerNode"] = Field(default_factory=list)
