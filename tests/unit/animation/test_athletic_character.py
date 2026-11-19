import pytest
from krita_mcp_lazy.animation.athletic_character_rig import (
    AthleticRunnerPalette,
    AthleticRunnerCostume,
    create_athletic_character_metadata,
)


def test_athletic_runner_palette_values():
    palette = AthleticRunnerPalette()
    assert palette.tank_top == "#1A365D"  # Deep Cobalt Navy
    assert palette.shorts == "#102A43"    # Midnight Navy
    assert palette.trim_white == "#FFFFFF"
    assert palette.skin_base == "#FAD2B8"  # Warm Peach
    assert palette.skin_shadow == "#C47B56"  # Rich Warm Shadow
    assert palette.hair_base == "#4A2810"  # Rich Brunette
    assert palette.hair_specular == "#FFE082"  # Golden Sun Specular
    assert palette.sweatband == "#FFFFFF"
    assert palette.cel_shadow == "#1E152A"  # Deep Multiply


def test_athletic_runner_costume_components():
    costume = AthleticRunnerCostume()
    layers = costume.get_costume_layers()
    assert "Tank_Top" in layers
    assert "Running_Shorts" in layers
    assert "Sweatband_Head" in layers
    assert "Wristband_R" in layers
    assert "Sports_Trainers" in layers


def test_character_metadata_creation():
    meta = create_athletic_character_metadata(
        character_id="anime_creator_runner",
        name="Anime Creator (Athletic)",
        width=3840,
        height=2160,
    )
    assert meta.character_id == "anime_creator_runner"
    assert "tank_top" in meta.palette
    assert "neck" in meta.pivots
    assert "hip" in meta.pivots
