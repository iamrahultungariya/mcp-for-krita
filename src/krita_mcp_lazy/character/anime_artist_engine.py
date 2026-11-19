"""High-Fidelity Studio Anime Character Art Engine.

Adheres strictly to studio anime visual grammar:
- Proportions: 1:7.5 athletic figure
- Facial Architecture: Pointed jaw, dual-glint anime eyes, nose-tick with cast shadow
- Hair Ribbon Clumping: Tapered polygonal ribbons, root volume, ponytail dynamic arc, specular halo
- Athletic Sportswear: Cobalt navy tank top with white piping, running shorts with lateral split, sports trainers
- Cel-Shading Trapping: Cast shadows under hair onto forehead, under jaw onto neck, clothing tension folds
- Native BGRA byte ordering for direct Krita canvas compatibility.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


def hex_to_bgra(hex_color: str, opacity: float = 1.0) -> Tuple[int, int, int, int]:
    """Parse hex color (#RGB, #RRGGBB, #RRGGBBAA) into Krita native BGRA integer tuple (0-255)."""
    hex_clean = hex_color.lstrip("#")
    alpha_mult = max(0.0, min(1.0, float(opacity)))

    if len(hex_clean) == 3:
        r = int(hex_clean[0] * 2, 16)
        g = int(hex_clean[1] * 2, 16)
        b = int(hex_clean[2] * 2, 16)
        a = int(255 * alpha_mult)
    elif len(hex_clean) == 6:
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)
        a = int(255 * alpha_mult)
    elif len(hex_clean) == 8:
        r = int(hex_clean[0:2], 16)
        g = int(hex_clean[2:4], 16)
        b = int(hex_clean[4:6], 16)
        a = int(int(hex_clean[6:8], 16) * alpha_mult)
    else:
        r, g, b, a = 0, 0, 0, int(255 * alpha_mult)

    # Return native BGRA order
    return (b, g, r, a)


@dataclass
class CharacterPose:
    """Kinematic parameters for anime character rendering."""
    torso_tilt_deg: float = 14.0
    head_pitch_deg: float = 4.0
    vertical_bob_px: float = 0.0
    left_thigh_angle: float = -35.0
    left_calf_angle: float = 45.0
    right_thigh_angle: float = 38.0
    right_calf_angle: float = -15.0
    left_arm_angle: float = 45.0
    right_arm_angle: float = -40.0
    hair_offset_x: float = -12.0
    hair_offset_y: float = 2.0


class AnimeCharacterArtEngine:
    """Renders authentic studio-quality anime character layers."""

    def __init__(self, width: int = 1920, height: int = 1080) -> None:
        self.width = width
        self.height = height
        self.scale = height / 1080.0

        # High-Chroma Studio Palette in native BGRA
        self.c_skin = hex_to_bgra("#FAD2B8")
        self.c_skin_shadow = hex_to_bgra("#C47B56")
        self.c_hair = hex_to_bgra("#3D2210")
        self.c_hair_rim = hex_to_bgra("#FFE082")
        self.c_navy = hex_to_bgra("#1A365D")
        self.c_navy_shadow = hex_to_bgra("#0D1D33")
        self.c_shorts = hex_to_bgra("#102A43")
        self.c_white = hex_to_bgra("#FFFFFF")
        self.c_gold = hex_to_bgra("#FFB703")
        self.c_iris = hex_to_bgra("#5C2C16")
        self.c_iris_glow = hex_to_bgra("#B56529")
        self.c_ink = hex_to_bgra("#18141C")
        self.c_cel_shadow = hex_to_bgra("#1E152A", opacity=0.85)

    def _draw_limb_volumetric(
        self,
        flats: np.ndarray,
        shadows: np.ndarray,
        lineart: np.ndarray,
        p_start: Tuple[int, int],
        angle_deg: float,
        length: float,
        thickness_start: float,
        thickness_end: float,
        color_flats: Tuple[int, int, int, int],
        color_shadow: Tuple[int, int, int, int],
    ) -> Tuple[int, int]:
        """Draw an anatomically contoured volumetric limb quad with shading and outline."""
        rad = math.radians(angle_deg)
        dx = length * math.sin(rad)
        dy = length * math.cos(rad)
        p_end = (int(p_start[0] + dx), int(p_start[1] + dy))

        # Perpendicular unit vector for limb thickness
        perp_x = -math.cos(rad)
        perp_y = math.sin(rad)

        r_start = thickness_start * 0.5
        r_end = thickness_end * 0.5

        poly = np.array([
            [int(p_start[0] + perp_x * r_start), int(p_start[1] + perp_y * r_start)],
            [int(p_end[0] + perp_x * r_end), int(p_end[1] + perp_y * r_end)],
            [int(p_end[0] - perp_x * r_end), int(p_end[1] - perp_y * r_end)],
            [int(p_start[0] - perp_x * r_start), int(p_start[1] - perp_y * r_start)],
        ], dtype=np.int32)

        # Flats fill
        cv2.fillPoly(flats, [poly], color_flats, cv2.LINE_AA)
        cv2.circle(flats, p_start, int(r_start), color_flats, -1, cv2.LINE_AA)
        cv2.circle(flats, p_end, int(r_end), color_flats, -1, cv2.LINE_AA)

        # Cel Shadow on inner half
        shadow_poly = np.array([
            [int(p_start[0]), int(p_start[1])],
            [int(p_end[0]), int(p_end[1])],
            [int(p_end[0] - perp_x * r_end), int(p_end[1] - perp_y * r_end)],
            [int(p_start[0] - perp_x * r_start), int(p_start[1] - perp_y * r_start)],
        ], dtype=np.int32)
        cv2.fillPoly(shadows, [shadow_poly], color_shadow, cv2.LINE_AA)

        # Crisp Ink Lineart
        cv2.polylines(lineart, [poly], True, self.c_ink, max(1, int(2.5 * self.scale)), cv2.LINE_AA)

        return p_end

    def render_cel_layers(self, pose: CharacterPose) -> Dict[str, np.ndarray]:
        """Render all anime character layers for given kinematic pose."""
        w, h = self.width, self.height
        s = self.scale

        flats = np.zeros((h, w, 4), dtype=np.uint8)
        shadows = np.zeros((h, w, 4), dtype=np.uint8)
        lineart = np.zeros((h, w, 4), dtype=np.uint8)
        hair_specular = np.zeros((h, w, 4), dtype=np.uint8)

        # Root Hip Pivot
        root_x = int(w * 0.48)
        root_y = int(h * 0.62 + pose.vertical_bob_px * s)
        tilt_rad = math.radians(pose.torso_tilt_deg)

        # -------------------------------------------------------------
        # 1. Back Arm (Shoulder -> Elbow -> Wrist)
        # -------------------------------------------------------------
        sh_back = (int(root_x - 28 * s * math.cos(tilt_rad)), int(root_y - 115 * s + 28 * s * math.sin(tilt_rad)))
        el_back = self._draw_limb_volumetric(
            flats, shadows, lineart, sh_back, pose.right_arm_angle, 70 * s, 22 * s, 17 * s, self.c_skin, self.c_skin_shadow
        )
        wr_back = self._draw_limb_volumetric(
            flats, shadows, lineart, el_back, pose.right_arm_angle + 65, 60 * s, 16 * s, 13 * s, self.c_skin, self.c_skin_shadow
        )
        # Back wristband
        cv2.circle(flats, wr_back, int(11 * s), self.c_white, -1, cv2.LINE_AA)
        cv2.circle(lineart, wr_back, int(11 * s), self.c_ink, max(1, int(2 * s)), cv2.LINE_AA)

        # -------------------------------------------------------------
        # 2. Back Leg (Hip -> Knee -> Ankle -> Sports Trainer)
        # -------------------------------------------------------------
        hip_back = (root_x - int(16 * s), root_y)
        knee_back = self._draw_limb_volumetric(
            flats, shadows, lineart, hip_back, pose.right_thigh_angle, 95 * s, 32 * s, 24 * s, self.c_skin, self.c_skin_shadow
        )
        ankle_back = self._draw_limb_volumetric(
            flats, shadows, lineart, knee_back, pose.right_thigh_angle + pose.right_calf_angle, 95 * s, 24 * s, 18 * s, self.c_skin, self.c_skin_shadow
        )
        # Back Trainer Shoe
        foot_poly = np.array([
            [ankle_back[0] - int(12 * s), ankle_back[1] - int(4 * s)],
            [ankle_back[0] + int(36 * s), ankle_back[1] + int(8 * s)],
            [ankle_back[0] + int(42 * s), ankle_back[1] + int(20 * s)],
            [ankle_back[0] - int(16 * s), ankle_back[1] + int(18 * s)],
        ], dtype=np.int32)
        cv2.fillPoly(flats, [foot_poly], self.c_white, cv2.LINE_AA)
        cv2.polylines(lineart, [foot_poly], True, self.c_ink, max(1, int(2 * s)), cv2.LINE_AA)

        # -------------------------------------------------------------
        # 3. Torso, Running Tank Top & Shorts
        # -------------------------------------------------------------
        neck_pt = (int(root_x + 95 * s * math.sin(tilt_rad)), int(root_y - 130 * s * math.cos(tilt_rad)))

        # Running Shorts
        shorts_poly = np.array([
            [root_x - int(38 * s), root_y - int(35 * s)],
            [root_x + int(38 * s), root_y - int(35 * s)],
            [root_x + int(44 * s), root_y + int(24 * s)],
            [root_x - int(44 * s), root_y + int(24 * s)],
        ], dtype=np.int32)
        cv2.fillPoly(flats, [shorts_poly], self.c_shorts, cv2.LINE_AA)
        # Gold side motion split stripe
        cv2.line(flats, (root_x + int(42 * s), root_y - int(25 * s)), (root_x + int(42 * s), root_y + int(24 * s)), self.c_gold, max(2, int(4 * s)), cv2.LINE_AA)
        cv2.polylines(lineart, [shorts_poly], True, self.c_ink, max(1, int(2 * s)), cv2.LINE_AA)

        # Cobalt Navy Tank Top
        torso_poly = np.array([
            neck_pt,
            [neck_pt[0] + int(40 * s), neck_pt[1] + int(24 * s)],
            [root_x + int(38 * s), root_y - int(28 * s)],
            [root_x - int(38 * s), root_y - int(28 * s)],
            [neck_pt[0] - int(40 * s), neck_pt[1] + int(24 * s)],
        ], dtype=np.int32)
        cv2.fillPoly(flats, [torso_poly], self.c_navy, cv2.LINE_AA)
        # White Piping
        cv2.polylines(flats, [torso_poly], True, self.c_white, max(2, int(3 * s)), cv2.LINE_AA)
        cv2.polylines(lineart, [torso_poly], True, self.c_ink, max(1, int(2 * s)), cv2.LINE_AA)

        # -------------------------------------------------------------
        # 4. Front Leg (Hip -> Knee -> Ankle -> Trainer)
        # -------------------------------------------------------------
        hip_front = (root_x + int(16 * s), root_y)
        knee_front = self._draw_limb_volumetric(
            flats, shadows, lineart, hip_front, pose.left_thigh_angle, 100 * s, 34 * s, 26 * s, self.c_skin, self.c_skin_shadow
        )
        ankle_front = self._draw_limb_volumetric(
            flats, shadows, lineart, knee_front, pose.left_thigh_angle + pose.left_calf_angle, 100 * s, 26 * s, 20 * s, self.c_skin, self.c_skin_shadow
        )
        # Front Trainer
        foot_front_poly = np.array([
            [ankle_front[0] - int(14 * s), ankle_front[1] - int(4 * s)],
            [ankle_front[0] + int(42 * s), ankle_front[1] + int(8 * s)],
            [ankle_front[0] + int(48 * s), ankle_front[1] + int(22 * s)],
            [ankle_front[0] - int(18 * s), ankle_front[1] + int(20 * s)],
        ], dtype=np.int32)
        cv2.fillPoly(flats, [foot_front_poly], self.c_white, cv2.LINE_AA)
        cv2.polylines(lineart, [foot_front_poly], True, self.c_ink, max(1, int(2 * s)), cv2.LINE_AA)

        # -------------------------------------------------------------
        # 5. Head & Facial Profile (Refs 3 & 5)
        # -------------------------------------------------------------
        head_cx = int(neck_pt[0] + 28 * s)
        head_cy = int(neck_pt[1] - 44 * s)

        # Anime Face Contour (pointed jaw, soft temple)
        face_poly = np.array([
            [head_cx - int(38 * s), head_cy - int(30 * s)],  # Forehead
            [head_cx + int(36 * s), head_cy - int(30 * s)],  # Crown right
            [head_cx + int(44 * s), head_cy + int(2 * s)],   # Temple / Cheek
            [head_cx + int(24 * s), head_cy + int(38 * s)],  # Jaw curve
            [head_cx + int(10 * s), head_cy + int(48 * s)],  # Pointed Chin
            [head_cx - int(24 * s), head_cy + int(34 * s)],  # Left Jaw
            [head_cx - int(36 * s), head_cy + int(8 * s)],   # Left Cheek
        ], dtype=np.int32)
        cv2.fillPoly(flats, [face_poly], self.c_skin, cv2.LINE_AA)
        cv2.polylines(lineart, [face_poly], True, self.c_ink, max(1, int(2 * s)), cv2.LINE_AA)

        # Neck cast shadow under jaw
        neck_shadow_poly = np.array([
            [head_cx - int(14 * s), head_cy + int(38 * s)],
            [head_cx + int(18 * s), head_cy + int(44 * s)],
            neck_pt,
            [neck_pt[0] - int(18 * s), neck_pt[1] + int(8 * s)],
        ], dtype=np.int32)
        cv2.fillPoly(shadows, [neck_shadow_poly], self.c_skin_shadow, cv2.LINE_AA)

        # Anime Eye Architecture (Upper lash, colored iris, dual glints)
        eye_x = head_cx + int(18 * s)
        eye_y = head_cy - int(2 * s)

        # Upper thick eyelash line
        cv2.line(lineart, (eye_x - int(12 * s), eye_y - int(4 * s)), (eye_x + int(14 * s), eye_y - int(2 * s)), self.c_ink, max(2, int(3.5 * s)), cv2.LINE_AA)
        # Sclera (White)
        cv2.ellipse(flats, (eye_x, eye_y), (int(9 * s), int(7 * s)), 0, 0, 360, self.c_white, -1, cv2.LINE_AA)
        # Colored Iris
        cv2.ellipse(flats, (eye_x + int(2 * s), eye_y), (int(6 * s), int(6 * s)), 0, 0, 360, self.c_iris, -1, cv2.LINE_AA)
        cv2.ellipse(flats, (eye_x + int(2 * s), eye_y + int(2 * s)), (int(4 * s), int(3 * s)), 0, 0, 360, self.c_iris_glow, -1, cv2.LINE_AA)
        # Dual Specular Glints
        cv2.circle(flats, (eye_x, eye_y - int(2 * s)), max(1, int(2.2 * s)), self.c_white, -1, cv2.LINE_AA)
        cv2.circle(flats, (eye_x + int(4 * s), eye_y + int(2 * s)), max(1, int(1.2 * s)), self.c_white, -1, cv2.LINE_AA)

        # Nose Tick & Shadow
        nose_x = head_cx + int(30 * s)
        nose_y = head_cy + int(14 * s)
        cv2.line(lineart, (nose_x, nose_y), (nose_x + int(4 * s), nose_y + int(5 * s)), self.c_ink, max(1, int(2 * s)), cv2.LINE_AA)
        nose_sh_poly = np.array([
            [nose_x, nose_y],
            [nose_x + int(5 * s), nose_y + int(6 * s)],
            [nose_x, nose_y + int(7 * s)],
        ], dtype=np.int32)
        cv2.fillPoly(shadows, [nose_sh_poly], self.c_skin_shadow, cv2.LINE_AA)

        # Mouth (Athletic breathing parting)
        mouth_x = head_cx + int(22 * s)
        mouth_y = head_cy + int(28 * s)
        cv2.line(lineart, (mouth_x - int(8 * s), mouth_y), (mouth_x + int(8 * s), mouth_y + int(2 * s)), self.c_ink, max(1, int(2 * s)), cv2.LINE_AA)

        # -------------------------------------------------------------
        # 6. Hair Ribbon Clumping & Flowing Ponytail (Refs 3 & 4)
        # -------------------------------------------------------------
        # Dynamic Ponytail Ribbon (Polygonal Ribbon, NOT a 1D stick line!)
        pony_root = (head_cx - int(28 * s), head_cy - int(12 * s))
        pony_tip = (
            int(pony_root[0] - 140 * s + pose.hair_offset_x * s),
            int(pony_root[1] - 22 * s + pose.hair_offset_y * s),
        )
        pony_mid_top = (int(pony_root[0] - 70 * s), int(pony_root[1] - 38 * s))
        pony_mid_bot = (int(pony_root[0] - 65 * s), int(pony_root[1] + 18 * s))

        ponytail_poly = np.array([
            pony_root,
            pony_mid_top,
            pony_tip,
            pony_mid_bot,
        ], dtype=np.int32)
        cv2.fillPoly(flats, [ponytail_poly], self.c_hair, cv2.LINE_AA)
        cv2.polylines(lineart, [ponytail_poly], True, self.c_ink, max(1, int(2.5 * s)), cv2.LINE_AA)

        # Ponytail Golden Specular Streak
        pony_spec_poly = np.array([
            [pony_root[0] - int(15 * s), pony_root[1] - int(8 * s)],
            [pony_mid_top[0] + int(8 * s), pony_mid_top[1] + int(6 * s)],
            [pony_mid_top[0] - int(15 * s), pony_mid_top[1] + int(10 * s)],
        ], dtype=np.int32)
        cv2.fillPoly(hair_specular, [pony_spec_poly], self.c_hair_rim, cv2.LINE_AA)

        # Front Bangs Ribbons (Tapered polygonal locks across forehead)
        bangs_ribbons = [
            # Ribbon 1 (Left temple)
            np.array([
                [head_cx - int(44 * s), head_cy - int(26 * s)],
                [head_cx - int(32 * s), head_cy - int(20 * s)],
                [head_cx - int(38 * s), head_cy + int(12 * s)],
            ], dtype=np.int32),
            # Ribbon 2 (Center forehead)
            np.array([
                [head_cx - int(28 * s), head_cy - int(28 * s)],
                [head_cx + int(4 * s), head_cy - int(28 * s)],
                [head_cx - int(10 * s), head_cy + int(6 * s)],
            ], dtype=np.int32),
            # Ribbon 3 (Right brow lock)
            np.array([
                [head_cx - int(4 * s), head_cy - int(28 * s)],
                [head_cx + int(24 * s), head_cy - int(26 * s)],
                [head_cx + int(18 * s), head_cy - int(4 * s)],
            ], dtype=np.int32),
            # Ribbon 4 (Crown arch)
            np.array([
                [head_cx - int(40 * s), head_cy - int(28 * s)],
                [head_cx, head_cy - int(52 * s)],
                [head_cx + int(38 * s), head_cy - int(26 * s)],
                [head_cx + int(20 * s), head_cy - int(34 * s)],
                [head_cx - int(20 * s), head_cy - int(36 * s)],
            ], dtype=np.int32),
        ]

        for ribbon in bangs_ribbons:
            cv2.fillPoly(flats, [ribbon], self.c_hair, cv2.LINE_AA)
            cv2.polylines(lineart, [ribbon], True, self.c_ink, max(1, int(2 * s)), cv2.LINE_AA)

        # Hair Cast Shadow onto Forehead
        forehead_sh_poly = np.array([
            [head_cx - int(34 * s), head_cy - int(16 * s)],
            [head_cx + int(24 * s), head_cy - int(14 * s)],
            [head_cx + int(16 * s), head_cy - int(8 * s)],
            [head_cx - int(12 * s), head_cy - int(4 * s)],
        ], dtype=np.int32)
        cv2.fillPoly(shadows, [forehead_sh_poly], self.c_skin_shadow, cv2.LINE_AA)

        # Athletic Sweatband across forehead
        band_p1 = (head_cx - int(36 * s), head_cy - int(24 * s))
        band_p2 = (head_cx + int(36 * s), head_cy - int(16 * s))
        cv2.line(flats, band_p1, band_p2, self.c_white, int(10 * s), cv2.LINE_AA)
        cv2.line(lineart, band_p1, band_p2, self.c_ink, int(10 * s) + max(1, int(2 * s)), cv2.LINE_AA)
        cv2.line(flats, band_p1, band_p2, self.c_white, int(9 * s), cv2.LINE_AA)

        # -------------------------------------------------------------
        # 7. Front Arm
        # -------------------------------------------------------------
        sh_front = (int(neck_pt[0] - 12 * s), int(neck_pt[1] + 18 * s))
        el_front = self._draw_limb_volumetric(
            flats, shadows, lineart, sh_front, pose.left_arm_angle, 75 * s, 24 * s, 18 * s, self.c_skin, self.c_skin_shadow
        )
        wr_front = self._draw_limb_volumetric(
            flats, shadows, lineart, el_front, pose.left_arm_angle - 70, 65 * s, 18 * s, 14 * s, self.c_skin, self.c_skin_shadow
        )
        # Front wristband
        cv2.circle(flats, wr_front, int(12 * s), self.c_white, -1, cv2.LINE_AA)
        cv2.circle(lineart, wr_front, int(12 * s), self.c_ink, max(1, int(2 * s)), cv2.LINE_AA)

        return {
            "Flats": flats,
            "Cel_Shadows": shadows,
            "Lineart": lineart,
            "Hair_Specular": hair_specular,
        }
