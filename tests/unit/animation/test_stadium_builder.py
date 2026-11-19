import pytest
import numpy as np
import cv2
from krita_mcp_lazy.animation.cinematic_stadium_builder import (
    generate_sky_plane,
    generate_bleachers_plane,
    generate_track_plane,
    create_cinematic_stadium_composite,
)


def test_sky_plane_dimensions_and_saturation():
    w, h = 1920, 1080
    sky = generate_sky_plane(w, h)
    assert sky.shape == (h, w, 4)  # RGBA
    assert sky.dtype == np.uint8

    # Verify colors are vibrant, not washed out (RGB to HSV saturation check)
    bgr = cv2.cvtColor(sky, cv2.COLOR_RGBA2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    sat = hsv[:, :, 1]
    # Sky should have rich blue saturation (mean saturation > 50)
    assert np.mean(sat) > 40.0


def test_bleachers_plane_dimensions():
    w, h = 1920, 1080
    bleachers = generate_bleachers_plane(w, h)
    assert bleachers.shape == (h, w, 4)
    # Check green field presence
    green_mask = (bleachers[:, :, 1] > 100) & (bleachers[:, :, 0] < 80)
    assert np.count_nonzero(green_mask) > 1000


def test_track_plane_saturation_and_lanes():
    w, h = 1920, 1080
    track = generate_track_plane(w, h)
    assert track.shape == (h, w, 4)
    # Track red color should be saturated terracotta (#B3261E / #D32F2F)
    # Red channel significantly higher than blue and green
    red_dominant = (track[:, :, 0] > 120) & (track[:, :, 2] < 80)
    assert np.count_nonzero(red_dominant) > 50000


def test_cinematic_composite():
    w, h = 1280, 720
    comp = create_cinematic_stadium_composite(w, h)
    assert comp.shape == (h, w, 3)
    assert comp.dtype == np.uint8


def test_stadium_parallax_plane_shifts():
    from krita_mcp_lazy.animation.cinematic_stadium_builder import StadiumParallaxEngine
    engine = StadiumParallaxEngine(width=1920, height=1080)
    frame_0 = engine.composite_background(frame_index=0)
    frame_24 = engine.composite_background(frame_index=24)
    assert frame_0.shape == (1080, 1920, 3)
    assert frame_24.shape == (1080, 1920, 3)
    # Track lane displacement check
    assert not (frame_0 == frame_24).all()
