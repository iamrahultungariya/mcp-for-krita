"""Cel Engine module: Decomposer, FidelityGate, and data models for studio cel drawing and verification."""

from __future__ import annotations

from krita_mcp_lazy.cel_engine.decomposer import CelArtDecomposer
from krita_mcp_lazy.cel_engine.fidelity import FidelityGate, FidelityReport
from krita_mcp_lazy.cel_engine.models import (
    CelArtDecomposition,
    FlatRegion,
    HighlightRegion,
    ShadowRegion,
    TaperedStroke,
)

__all__ = [
    "CelArtDecomposer",
    "FidelityGate",
    "FidelityReport",
    "CelArtDecomposition",
    "FlatRegion",
    "HighlightRegion",
    "ShadowRegion",
    "TaperedStroke",
]
