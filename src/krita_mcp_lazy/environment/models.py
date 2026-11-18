"""Data models and enums for perspective grids and environment depth planes."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class PerspectiveType(str, Enum):
    """Perspective projection types."""

    ONE_POINT = "one_point"
    TWO_POINT = "two_point"
    THREE_POINT = "three_point"


class DepthPlaneType(str, Enum):
    """Standard Z-depth environment planes."""

    SKY = "sky"
    FAR_BG = "far_bg"
    MID_BG = "mid_bg"
    PLAY_AREA = "play_area"
    NEAR_FG = "near_fg"


class PerspectiveGridSpec(BaseModel):
    """Specification for calculating and rendering perspective grid guidelines."""

    perspective_type: PerspectiveType = PerspectiveType.TWO_POINT
    horizon_y: float
    vp1_x: Optional[float] = None
    vp2_x: Optional[float] = None
    vp3_y: Optional[float] = None
    line_density: int = Field(default=12, ge=4, le=48)
    opacity: float = Field(default=0.4, ge=0.1, le=1.0)
    color: str = "#00aaff"
