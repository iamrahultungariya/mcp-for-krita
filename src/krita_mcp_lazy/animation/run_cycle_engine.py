"""12-Frame Studio Cel Anime Run-Cycle Engine.

Generates an authentic 12-frame 2-step looping run cycle for Anime Creator:
- Kinematic stride phases: Contact, Recoil, Passing, Air Peak, Descent
- Opposing arm-leg momentum and torso compression/extension
- Secondary bounce: flowing ponytail, bouncing bangs, and sweat ejection
- High-fidelity anime character rendering via AnimeCharacterArtEngine
  (Polygonal hair ribbons, pointed anime facial anatomy, dual-glint eyes,
  athletic sports tank top and shorts, crisp cel-shadows and ink lineart).
"""

from __future__ import annotations

import base64
import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np

from krita_mcp_lazy.animation.athletic_character_rig import AthleticRunnerPalette
from krita_mcp_lazy.character.anime_artist_engine import (
    AnimeCharacterArtEngine,
    CharacterPose,
)

logger = logging.getLogger(__name__)


@dataclass
class StridePose:
    """Kinematic parameters for a single run-cycle frame."""
    frame_index: int
    phase_name: str
    vertical_bob_px: float       # Vertical torso displacement
    torso_tilt_deg: float        # Forward lean angle
    left_thigh_angle: float      # Degrees from vertical
    left_calf_angle: float
    right_thigh_angle: float
    right_calf_angle: float
    left_arm_angle: float        # Shoulder rotation
    right_arm_angle: float
    hair_offset_y: float         # Secondary hair inertia
    hair_offset_x: float
    sweat_burst: bool = False


class RunCycleEngine:
    """Manages the 12-frame cinematic anime run-cycle kinematics."""

    def __init__(self, width: int = 1920, height: int = 1080) -> None:
        self.width = width
        self.height = height
        self.palette = AthleticRunnerPalette()
        self.art_engine = AnimeCharacterArtEngine(width=width, height=height)

    def get_stride_poses(self) -> List[StridePose]:
        """Generate the 12 canonical athletic stride poses."""
        poses: List[StridePose] = []

        # 12-frame loop parameters:
        # Step 1: Frames 0..5 (Right leg drive, Left leg trail)
        # Step 2: Frames 6..11 (Left leg drive, Right leg trail)
        raw_data = [
            # idx, name, bob, tilt, L_thigh, L_calf, R_thigh, R_calf, L_arm, R_arm, hair_y, hair_x, sweat
            (0, "Contact_R",    0.0,  14.0,  -35.0,  45.0,   38.0,  -15.0,   45.0, -40.0,   2.0, -12.0, False),
            (1, "Recoil_Squash_R", 18.0, 16.0,  -20.0,  60.0,   25.0,  -40.0,   30.0, -30.0,   8.0,  -8.0, True),
            (2, "Passing_R",    8.0,  13.0,    5.0,  30.0,   -5.0,  -70.0,   10.0, -10.0,  -4.0, -15.0, False),
            (3, "High_Air_R",  -16.0, 11.0,   35.0,  10.0,  -40.0,  -50.0,  -25.0,  25.0, -12.0, -22.0, True),
            (4, "Air_Peak_R",  -20.0, 10.0,   42.0, -10.0,  -48.0,  -30.0,  -40.0,  40.0, -14.0, -26.0, False),
            (5, "Descent_R",    -6.0, 12.0,   30.0, -25.0,  -25.0,  -10.0,  -20.0,  20.0,  -6.0, -18.0, False),

            # Mirrored Step 2
            (6, "Contact_L",    0.0,  14.0,   38.0, -15.0,  -35.0,   45.0,  -40.0,  45.0,   2.0, -12.0, False),
            (7, "Recoil_Squash_L", 18.0, 16.0,  25.0, -40.0,  -20.0,   60.0,  -30.0,  30.0,   8.0,  -8.0, True),
            (8, "Passing_L",    8.0,  13.0,   -5.0, -70.0,    5.0,   30.0,  -10.0,  10.0,  -4.0, -15.0, False),
            (9, "High_Air_L",  -16.0, 11.0,  -40.0, -50.0,   35.0,   10.0,   25.0, -25.0, -12.0, -22.0, True),
            (10, "Air_Peak_L", -20.0, 10.0,  -48.0, -30.0,   42.0,  -10.0,   40.0, -40.0, -14.0, -26.0, False),
            (11, "Descent_L",   -6.0, 12.0,  -25.0, -10.0,   30.0,  -25.0,   20.0, -20.0,  -6.0, -18.0, False),
        ]

        for item in raw_data:
            poses.append(
                StridePose(
                    frame_index=item[0],
                    phase_name=item[1],
                    vertical_bob_px=item[2],
                    torso_tilt_deg=item[3],
                    left_thigh_angle=item[4],
                    left_calf_angle=item[5],
                    right_thigh_angle=item[6],
                    right_calf_angle=item[7],
                    left_arm_angle=item[8],
                    right_arm_angle=item[9],
                    hair_offset_y=item[10],
                    hair_offset_x=item[11],
                    sweat_burst=item[12],
                )
            )

        return poses

    def generate_all_stride_frames(self) -> List[np.ndarray]:
        """Pre-render and return all 12 stride cycle frames as composite RGBA buffers."""
        poses = self.get_stride_poses()
        frames: List[np.ndarray] = []
        for p in poses:
            f = render_stride_frame(p, self.width, self.height, self.palette)
            frames.append(f)
        return frames


def render_stride_frame(
    pose: StridePose,
    width: int,
    height: int,
    palette: AthleticRunnerPalette | None = None,
) -> np.ndarray:
    """Render a single authentic studio anime runner stride frame."""
    art_engine = AnimeCharacterArtEngine(width=width, height=height)

    char_pose = CharacterPose(
        torso_tilt_deg=pose.torso_tilt_deg,
        head_pitch_deg=4.0,
        vertical_bob_px=pose.vertical_bob_px,
        left_thigh_angle=pose.left_thigh_angle,
        left_calf_angle=pose.left_calf_angle,
        right_thigh_angle=pose.right_thigh_angle,
        right_calf_angle=pose.right_calf_angle,
        left_arm_angle=pose.left_arm_angle,
        right_arm_angle=pose.right_arm_angle,
        hair_offset_x=pose.hair_offset_x,
        hair_offset_y=pose.hair_offset_y,
    )

    layers = art_engine.render_cel_layers(char_pose)

    flats = layers["Flats"]
    shadows = layers["Cel_Shadows"]
    lineart = layers["Lineart"]
    specular = layers["Hair_Specular"]

    # Composite into master 4-channel frame
    comp = np.zeros((height, width, 4), dtype=np.uint8)

    # 1. Base Flats
    mask_flats = flats[:, :, 3] > 0
    comp[mask_flats] = flats[mask_flats]

    # 2. Cel Shadows (Multiply blend over flats)
    mask_sh = (shadows[:, :, 3] > 0) & mask_flats
    if np.any(mask_sh):
        base_f = comp[mask_sh, :3].astype(np.float32)
        sh_f = shadows[mask_sh, :3].astype(np.float32)
        alpha_sh = (shadows[mask_sh, 3].astype(np.float32) / 255.0)[:, np.newaxis]
        multiplied = (base_f * sh_f) / 255.0
        blended = base_f * (1.0 - alpha_sh) + multiplied * alpha_sh
        comp[mask_sh, :3] = np.clip(blended, 0, 255).astype(np.uint8)

    # 3. Hair Specular (Screen blend over flats)
    mask_spec = (specular[:, :, 3] > 0) & mask_flats
    if np.any(mask_spec):
        base_f = comp[mask_spec, :3].astype(np.float32)
        spec_f = specular[mask_spec, :3].astype(np.float32)
        alpha_spec = (specular[mask_spec, 3].astype(np.float32) / 255.0)[:, np.newaxis]
        screened = 255.0 - ((255.0 - base_f) * (255.0 - spec_f) / 255.0)
        blended = base_f * (1.0 - alpha_spec) + screened * alpha_spec
        comp[mask_spec, :3] = np.clip(blended, 0, 255).astype(np.uint8)

    # 4. Master Lineart (Direct overlay)
    mask_line = lineart[:, :, 3] > 0
    comp[mask_line] = lineart[mask_line]

    return comp
