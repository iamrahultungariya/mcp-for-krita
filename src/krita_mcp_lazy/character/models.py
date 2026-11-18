"""Data models and enums for character production and turnaround sheets."""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ViewAngle(str, Enum):
    """Standard turnaround angle views."""

    FRONT = "front"
    THREE_QUARTER = "three_quarter"
    SIDE = "side"
    BACK = "back"


class CharacterSheetSpec(BaseModel):
    """Specification for generating a character turnaround sheet with anatomical guides."""

    character_name: str
    head_height_ratio: float = Field(default=7.5, ge=5.0, le=10.0, description="Total body height in head units")
    views: List[ViewAngle] = Field(
        default_factory=lambda: [ViewAngle.FRONT, ViewAngle.THREE_QUARTER, ViewAngle.SIDE, ViewAngle.BACK]
    )
    clothing_tokens: Optional[List[str]] = Field(default_factory=list)
    color_tokens: Optional[Dict[str, str]] = Field(default_factory=dict)
    total_height_px: int = Field(default=1000, gt=100)
    top_offset_px: int = Field(default=100, ge=0)
