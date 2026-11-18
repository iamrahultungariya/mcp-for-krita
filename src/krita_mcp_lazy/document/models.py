"""Domain models and specifications for Krita documents."""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class ColorModel(str, Enum):
    """Supported color models in Krita."""

    RGBA = "RGBA"
    CMYK = "CMYK"
    GRAY = "GRAY"
    YCbCr = "YCbCr"


class BitDepth(str, Enum):
    """Supported channel bit depths in Krita."""

    U8 = "U8"
    U16 = "U16"
    F16 = "F16"
    F32 = "F32"


class DocumentSpec(BaseModel):
    """Specification parameters for creating a new Krita document."""

    name: str = Field(default="Artwork", description="Document label or title")
    width: int = Field(default=1920, gt=0, le=16384, description="Canvas width in pixels (1-16384)")
    height: int = Field(default=1080, gt=0, le=16384, description="Canvas height in pixels (1-16384)")
    resolution_dpi: float = Field(default=300.0, gt=0.0, description="Print/display resolution in DPI")
    color_model: ColorModel = Field(default=ColorModel.RGBA, description="Color model identifier")
    bit_depth: BitDepth = Field(default=BitDepth.U8, description="Channel precision / bit depth")
    color_profile: Optional[str] = Field(
        default="sRGB-elle-V2-srgbtrc.icc",
        description="ICC / OCIO color profile name",
    )


class DocumentInfo(BaseModel):
    """Inspection metadata summary for an open Krita document."""

    doc_id: str
    name: str
    width: int
    height: int
    resolution_dpi: float
    color_model: str
    bit_depth: str
    color_profile: str
    file_path: Optional[str] = None
    modified: bool = False
    layer_count: int = 0
