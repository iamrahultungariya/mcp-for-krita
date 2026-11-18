"""Modular prop assets, material shading templates, and asset metadata."""

from krita_mcp_lazy.assets.models import MaterialType, PropSpec
from krita_mcp_lazy.assets.prop_engine import MATERIAL_LAYER_TEMPLATES, PropEngine

__all__ = [
    "MATERIAL_LAYER_TEMPLATES",
    "MaterialType",
    "PropEngine",
    "PropSpec",
]
