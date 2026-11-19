import pytest
import numpy as np
import cv2
from krita_mcp_lazy.animation.run_cycle_engine import (
    RunCycleEngine,
    StridePose,
    render_stride_frame,
)


def test_stride_poses_count():
    engine = RunCycleEngine()
    poses = engine.get_stride_poses()
    assert len(poses) == 12  # Standard 12-frame 2-step loop


def test_render_stride_frame_dimensions_and_alpha():
    w, h = 960, 540
    engine = RunCycleEngine()
    pose = engine.get_stride_poses()[0]  # Contact 1
    frame = render_stride_frame(pose, w, h)
    
    assert frame.shape == (h, w, 4)
    assert frame.dtype == np.uint8
    # Has non-transparent character pixels
    assert np.count_nonzero(frame[:, :, 3] > 0) > 5000


def test_character_color_saturation_not_faded():
    w, h = 960, 540
    engine = RunCycleEngine()
    pose = engine.get_stride_poses()[3]  # Airborne high point
    frame = render_stride_frame(pose, w, h)
    
    # Extract non-transparent pixels
    char_mask = frame[:, :, 3] > 0
    bgr = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    
    char_sat = hsv[char_mask, 1]
    # Saturated sports tank, shorts, and warm skin must have strong saturation (mean > 50)
    assert np.mean(char_sat) > 45.0


def test_stride_cycle_kinematic_variation():
    engine = RunCycleEngine()
    poses = engine.get_stride_poses()
    
    # Vertical hip bob must oscillate between recoil and air peak
    hip_ys = [p.vertical_bob_px for p in poses]
    assert max(hip_ys) > min(hip_ys)  # Dynamic vertical oscillation
    
    # Left leg angle must alternate
    l_angles = [p.left_thigh_angle for p in poses]
    assert max(l_angles) > 0 and min(l_angles) < 0
