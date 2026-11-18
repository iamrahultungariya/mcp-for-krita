"""Data models and enums for reusable prop assets and material shading profiles."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class MaterialType(str, Enum):
    """PBR-inspired stylized material profiles."""

    WOOD = "wood"
    METAL = "metal"
    FABRIC = "fabric"
    GLASS = "glass"
    STONE = "stone"
    SKIN = "skin"
    WATER = "water"


class PropSpec(BaseModel):
    """Specification for authoring modular prop assets."""

    prop_name: str
    material: MaterialType = MaterialType.WOOD
    category: str = "General"
    bounding_box: Optional[List[float]] = None
    pivot_x: float = Field(default=0.5, ge=0.0, le=1.0)
    pivot_y: float = Field(default=1.0, ge=0.0, le=1.0)
