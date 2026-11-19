"""Unit tests for Whispers in the Starlight anime movie poster specification."""

import pytest
from src.krita_mcp_lazy.art_planning.poster_concept import get_whispers_in_starlight_spec


def test_anime_poster_spec_generation():
    spec = get_whispers_in_starlight_spec()
    assert spec["title"]["english"] == "Whispers in the Starlight"
    assert spec["title"]["japanese"] == "星空の約束"
    assert spec["canvas"]["width"] == 2480
    assert spec["canvas"]["height"] == 3508
    assert spec["canvas"]["dpi"] == 300
    assert len(spec["layers"]) == 6
    assert "#0B1026" in spec["palette"].values()
    assert "00_Sky_Celestial" in spec["layers"]
    assert "03_Lovers_Hero" in spec["layers"]
    assert "05_Typography_Title" in spec["layers"]
