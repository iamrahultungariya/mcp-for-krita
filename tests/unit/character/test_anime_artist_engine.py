"""Unit tests for AnimeCharacterArtEngine."""

import pytest
import numpy as np
from krita_mcp_lazy.character.anime_artist_engine import (
    AnimeCharacterArtEngine,
    CharacterPose,
)


def test_anime_character_renders_facial_features_and_hair_ribbons():
    engine = AnimeCharacterArtEngine(width=1920, height=1080)
    pose = CharacterPose(torso_tilt_deg=14.0, head_pitch_deg=5.0)
    layers = engine.render_cel_layers(pose)

    assert "Lineart" in layers
    assert "Flats" in layers
    assert "Cel_Shadows" in layers
    assert "Hair_Specular" in layers

    lineart_arr = layers["Lineart"]
    assert lineart_arr.shape == (1080, 1920, 4)
    assert np.count_nonzero(lineart_arr[:, :, 3]) > 1000

    flats_arr = layers["Flats"]
    assert flats_arr.shape == (1080, 1920, 4)
    assert np.count_nonzero(flats_arr[:, :, 3]) > 5000

    # Ensure cel-shadows exist and are not empty
    shadows_arr = layers["Cel_Shadows"]
    assert np.count_nonzero(shadows_arr[:, :, 3]) > 500


def test_character_pose_deformation_differs():
    engine = AnimeCharacterArtEngine(width=1920, height=1080)
    pose1 = CharacterPose(left_thigh_angle=35.0, right_thigh_angle=-40.0)
    pose2 = CharacterPose(left_thigh_angle=-35.0, right_thigh_angle=40.0)

    layers1 = engine.render_cel_layers(pose1)
    layers2 = engine.render_cel_layers(pose2)

    # Flats pixel arrangement should change between contrasting poses
    assert not np.array_equal(layers1["Flats"], layers2["Flats"])
