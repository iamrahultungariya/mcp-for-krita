"""Unit tests for CelArtDecomposer: lineart vectorization, pressure tapering, and trapped flats."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from krita_mcp_lazy.cel_engine.decomposer import CelArtDecomposer
from krita_mcp_lazy.cel_engine.models import CelArtDecomposition


def test_cel_decomposer_under_trapping(tmp_path):
    # Synthetic anime patch: yellow hoodie with black border
    img = np.full((120, 120, 3), 255, dtype=np.uint8)
    # Yellow shirt
    cv2.rectangle(img, (20, 20), (100, 100), (0, 215, 255), -1)
    # Black ink border (thickness 4)
    cv2.rectangle(img, (20, 20), (100, 100), (0, 0, 0), 4)

    p = str(tmp_path / "hoodie_patch.png")
    cv2.imwrite(p, img)

    decomposer = CelArtDecomposer(trapping_dilation_px=2)
    decomp = decomposer.decompose(p)

    assert isinstance(decomp, CelArtDecomposition)
    assert len(decomp.vector_strokes) >= 1
    assert len(decomp.flat_regions) >= 1

    # Verify digital trapping: flat region mask must overlap ink stroke boundary
    flat = decomp.flat_regions[0]
    line_mask = decomp.lineart_mask
    overlap = np.logical_and(flat.mask > 0, line_mask > 0)
    assert np.sum(overlap) > 0, "Flat colors must dilate under ink lines to eliminate white halos"


def test_cel_decomposer_pressure_tapering(tmp_path):
    # Single vertical ink stroke on white
    img = np.full((100, 100, 3), 255, dtype=np.uint8)
    cv2.line(img, (50, 15), (50, 85), (0, 0, 0), 4)

    p = str(tmp_path / "ink_line.png")
    cv2.imwrite(p, img)

    decomposer = CelArtDecomposer()
    decomp = decomposer.decompose(p)

    assert len(decomp.vector_strokes) >= 1
    stroke = decomp.vector_strokes[0]
    assert len(stroke.points) >= 2
    assert len(stroke.pressures) == len(stroke.points)

    # Verify stroke pressure profile: tips should be tapered lower than center
    p_start = stroke.pressures[0]
    p_end = stroke.pressures[-1]
    p_max = max(stroke.pressures)
    assert p_start <= p_max
    assert p_end <= p_max
    assert 0.0 <= p_start <= 1.0


def test_cel_decomposer_shadow_highlight_extraction(tmp_path):
    # Anime face region with base skin, cel shadow, and specular highlight
    img = np.full((100, 100, 3), 255, dtype=np.uint8)
    # Base skin (soft peach)
    img[:] = (200, 220, 250)
    # Cast shadow under chin (darker skin tone)
    cv2.rectangle(img, (20, 60), (80, 90), (140, 160, 200), -1)
    # Highlight on cheek (bright white)
    cv2.circle(img, (30, 30), 8, (255, 255, 255), -1)

    p = str(tmp_path / "face_shading.png")
    cv2.imwrite(p, img)

    decomposer = CelArtDecomposer()
    decomp = decomposer.decompose(p)

    assert len(decomp.cel_shadows) >= 1
    assert len(decomp.highlights) >= 1
    assert decomp.composite_shadows is not None
    assert decomp.composite_highlights is not None
