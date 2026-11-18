"""Data models and enums for raster animation, keyframing, and onion skinning."""

from enum import Enum
from pydantic import BaseModel, Field


class KeyframeType(str, Enum):
    """Types of raster keyframes."""

    BLANK = "blank"
    DUPLICATE = "duplicate"


class OnionSkinConfig(BaseModel):
    """Configuration for visual onion skin tinting and display offsets."""

    tint_previous: str = "#ff0000"
    tint_future: str = "#00ff00"
    prev_frames: int = Field(default=2, ge=0, le=10)
    next_frames: int = Field(default=2, ge=0, le=10)
    opacity: float = Field(default=0.5, ge=0.0, le=1.0)
