"""Cinematic Stadium Multi-Plane Parallax Environment Builder.

Renders rich, vibrant, high-saturation anime background planes:
1. Far Sky & Morning Sunburst (slow parallax)
2. Mid Stadium Bleachers & Infield Turf (mid parallax)
3. Foreground Polyurethane Running Track with Crisp Lanes (fast parallax)
"""

from __future__ import annotations

import base64
import logging
import math
from typing import Any, Dict, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


def generate_sky_plane(width: int, height: int, offset_x: float = 0.0) -> np.ndarray:
    """Generate vibrant, cinematic morning sky with sun flare and stylized clouds (RGBA)."""
    # 1. Vertical Gradient: Deep Cerulean (#144B88) -> Vibrant Sky Blue (#2583DE) -> Soft Warm Horizon (#6EB5F7)
    y_coords = np.linspace(0, 1, height, dtype=np.float32)[:, np.newaxis]
    
    top_color = np.array([20, 75, 136], dtype=np.float32)      # Deep Rich Blue
    mid_color = np.array([37, 131, 222], dtype=np.float32)     # Radiant Anime Sky
    bot_color = np.array([125, 195, 250], dtype=np.float32)    # Warm Horizon Tint
    
    sky = np.zeros((height, width, 3), dtype=np.float32)
    split = 0.6
    
    # Upper half gradient
    upper_mask = (y_coords < split)[:, 0]
    norm_upper = (y_coords[upper_mask] / split)[:, :, np.newaxis]  # (N, 1, 1)
    grad_upper = (1.0 - norm_upper) * top_color + norm_upper * mid_color  # (N, 1, 3)
    sky[upper_mask] = grad_upper

    # Lower half gradient
    lower_mask = ~upper_mask
    norm_lower = ((y_coords[lower_mask] - split) / (1.0 - split))[:, :, np.newaxis]  # (M, 1, 1)
    grad_lower = (1.0 - norm_lower) * mid_color + norm_lower * bot_color  # (M, 1, 3)
    sky[lower_mask] = grad_lower

    # 2. Add Warm Golden Sun Flare (Top-Right / Angle of light)
    sun_x = int(width * 0.78 + (offset_x * 0.05) % width)
    sun_y = int(height * 0.22)
    yy, xx = np.ogrid[:height, :width]
    dist_sq = (xx - sun_x) ** 2 + (yy - sun_y) ** 2
    sun_radius = height * 0.55
    sun_flare = np.clip(1.0 - np.sqrt(dist_sq) / sun_radius, 0.0, 1.0) ** 2.2
    
    # Golden Sunlight (#FFF2B2)
    sun_rgb = np.array([255, 242, 178], dtype=np.float32)
    sky += sun_flare[:, :, np.newaxis] * (sun_rgb * 0.65)
    
    # 3. Stylized Fluffy Anime Clouds
    cloud_layer = np.zeros((height, width), dtype=np.float32)
    # 2 cloud clusters
    for i, (cx_rel, cy_rel, scale_r) in enumerate([
        (0.25, 0.38, 0.16), (0.42, 0.45, 0.12), (0.70, 0.35, 0.18), (0.85, 0.40, 0.14)
    ]):
        cx = int((width * cx_rel - offset_x * 0.1) % width)
        cy = int(height * cy_rel)
        cr = height * scale_r
        d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        puff = np.clip(1.0 - d / cr, 0.0, 1.0) ** 1.8
        cloud_layer = np.maximum(cloud_layer, puff)

    cloud_rgb = np.array([255, 255, 255], dtype=np.float32)
    sky = sky * (1.0 - cloud_layer[:, :, np.newaxis] * 0.85) + cloud_rgb * (cloud_layer[:, :, np.newaxis] * 0.85)
    
    sky = np.clip(sky, 0, 255).astype(np.uint8)
    alpha = np.full((height, width, 1), 255, dtype=np.uint8)
    return np.concatenate([sky, alpha], axis=2)


def generate_bleachers_plane(width: int, height: int, offset_x: float = 0.0) -> np.ndarray:
    """Generate vibrant stadium grandstands, field turf, and light towers (RGBA)."""
    img = np.zeros((height, width, 4), dtype=np.uint8)
    
    # Mid-ground horizon starts at height * 0.48
    horizon_y = int(height * 0.48)
    track_top_y = int(height * 0.68)
    
    # 1. Lush Green Field Turf (#1E8238 with warm sun highlights)
    field_h = track_top_y - horizon_y
    if field_h > 0:
        turf = np.zeros((field_h, width, 4), dtype=np.uint8)
        turf[:, :, 0] = 30   # R
        turf[:, :, 1] = 142  # G (Vibrant green)
        turf[:, :, 2] = 56   # B
        turf[:, :, 3] = 255  # A
        
        # Add subtle vertical mowing stripes
        stripe_w = max(10, int(width * 0.04))
        for x in range(0, width, stripe_w * 2):
            x_end = min(width, x + stripe_w)
            turf[:, x:x_end, 1] = np.clip(turf[:, x:x_end, 1].astype(int) + 18, 0, 255).astype(np.uint8)
            
        img[horizon_y:track_top_y, :] = turf

    # 2. Distant Stadium Bleachers & Grandstand Arches
    bleacher_top_y = int(height * 0.35)
    bleacher_h = horizon_y - bleacher_top_y
    if bleacher_h > 0:
        bleachers = np.zeros((bleacher_h, width, 4), dtype=np.uint8)
        # Stadium concrete tiers (#5E6B7E / #7E8C9F)
        bleachers[:, :, 0] = 95
        bleachers[:, :, 1] = 110
        bleachers[:, :, 2] = 130
        bleachers[:, :, 3] = 255
        
        # Step horizontal lines
        step_h = max(3, bleacher_h // 12)
        for y in range(0, bleacher_h, step_h):
            bleachers[y:min(bleacher_h, y + 2), :, :3] = [140, 155, 175]
            
        # Stadium roof canopy silhouette
        canopy_y = int(bleacher_h * 0.15)
        bleachers[:canopy_y, :, :3] = [70, 80, 95]
        
        img[bleacher_top_y:horizon_y, :] = bleachers

    # 3. Stadium Floodlight Mast Silhouettes
    mast_w = max(4, int(width * 0.008))
    for mast_rel in [0.15, 0.50, 0.85]:
        mx = int((width * mast_rel - offset_x * 0.4) % width)
        m_top = int(height * 0.20)
        m_bot = horizon_y
        img[m_top:m_bot, max(0, mx - mast_w // 2):min(width, mx + mast_w // 2)] = [50, 58, 70, 255]
        # Light array head
        head_w = mast_w * 5
        head_h = max(6, int(height * 0.03))
        hx1 = max(0, mx - head_w // 2)
        hx2 = min(width, mx + head_w // 2)
        img[m_top:m_top + head_h, hx1:hx2] = [230, 235, 245, 255]

    return img


def generate_track_plane(width: int, height: int, offset_x: float = 0.0) -> np.ndarray:
    """Generate high-saturation terracotta running track with curved perspective lanes (RGBA)."""
    img = np.zeros((height, width, 4), dtype=np.uint8)
    track_top_y = int(height * 0.65)
    track_h = height - track_top_y
    
    if track_h <= 0:
        return img
        
    # Saturated Terracotta Crimson: #C62828 / #B71C1C
    track = np.zeros((track_h, width, 4), dtype=np.uint8)
    
    # Vertical gradient on track to give sunlight depth
    y_ratios = np.linspace(0.85, 1.15, track_h)[:, np.newaxis]
    base_red = np.array([205, 38, 38], dtype=np.float32)  # Rich Terracotta
    
    shaded_red = np.clip(base_red * y_ratios, 0, 255).astype(np.uint8)  # (track_h, 3)
    track[:, :, 0] = shaded_red[:, np.newaxis, 0]
    track[:, :, 1] = shaded_red[:, np.newaxis, 1]
    track[:, :, 2] = shaded_red[:, np.newaxis, 2]
    track[:, :, 3] = 255
    
    # Polyurethane track speckled texture
    np.random.seed(42)
    noise = (np.random.randn(track_h, width) * 7).astype(np.int16)
    track_r = np.clip(track[:, :, 0].astype(np.int16) + noise, 0, 255).astype(np.uint8)
    track_g = np.clip(track[:, :, 1].astype(np.int16) + (noise * 0.3).astype(np.int16), 0, 255).astype(np.uint8)
    track[:, :, 0] = track_r
    track[:, :, 1] = track_g
    
    # White Lane Lines with dynamic perspective
    # 4 distinct running lanes
    lane_ys = [
        int(track_h * 0.18),
        int(track_h * 0.42),
        int(track_h * 0.68),
        int(track_h * 0.94),
    ]
    
    for idx, ly in enumerate(lane_ys):
        line_thickness = max(3, int(4 + idx * 2))
        y1 = max(0, ly - line_thickness // 2)
        y2 = min(track_h, ly + line_thickness // 2)
        # White lane line with subtle yellow sunlight tint
        track[y1:y2, :, :3] = [255, 255, 245]

    # Staggered Distance / Lane Hash Marks (moving across parallax offset_x)
    hash_spacing = max(60, int(width * 0.12))
    shifted_offset = int(offset_x) % hash_spacing
    for x in range(-hash_spacing, width + hash_spacing, hash_spacing):
        hx = x - shifted_offset
        if 0 <= hx < width - 15:
            # White hash marks across lanes
            for ly in lane_ys:
                hy1 = max(0, ly - 8)
                hy2 = min(track_h, ly + 8)
                track[hy1:hy2, hx:hx + 6, :3] = [255, 255, 255]

    img[track_top_y:, :] = track
    return img


def create_cinematic_stadium_composite(
    width: int,
    height: int,
    offset_x: float = 0.0,
) -> np.ndarray:
    """Composite all 3 stadium layers into full RGB frame."""
    sky = generate_sky_plane(width, height, offset_x=offset_x * 0.1)
    bleachers = generate_bleachers_plane(width, height, offset_x=offset_x * 0.4)
    track = generate_track_plane(width, height, offset_x=offset_x * 1.0)
    
    # Alpha blend onto sky
    comp = sky[:, :, :3].astype(np.float32)
    
    for layer in [bleachers, track]:
        alpha = (layer[:, :, 3].astype(np.float32) / 255.0)[:, :, np.newaxis]
        comp = comp * (1.0 - alpha) + layer[:, :, :3].astype(np.float32) * alpha
        
    return np.clip(comp, 0, 255).astype(np.uint8)


class StadiumParallaxEngine:
    """Manages multi-plane continuous parallax background generation."""

    def __init__(self, width: int = 1920, height: int = 1080) -> None:
        self.width = width
        self.height = height

    def composite_background(self, frame_index: int, speed: float = 18.0) -> np.ndarray:
        """Generate composited stadium background shifted for frame_index."""
        offset_x = frame_index * speed
        return create_cinematic_stadium_composite(self.width, self.height, offset_x=offset_x)


async def scaffold_stadium_in_krita(
    client: Any,
    doc_id: str = "doc_4",
    width: int = 3840,
    height: int = 2160,
) -> Dict[str, Any]:
    """Scaffold high-saturation multi-plane stadium layers into live Krita document."""
    logger.info("Scaffolding cinematic stadium layers in Krita doc %s (%dx%d)...", doc_id, width, height)
    
    # 1. Create BG_Environment Group Layer
    await client.send_job(
        "layer.create",
        {
            "doc_id": doc_id,
            "name": "BG_Environment",
            "layer_type": "groupLayer",
        },
    )
    
    # Helper to push an RGBA plane to Krita as BGRA PNG tile
    async def _push_plane(layer_name: str, rgba_data: np.ndarray):
        # Convert RGBA to Krita BGRA
        bgra = cv2.cvtColor(rgba_data, cv2.COLOR_RGBA2BGRA)
        _, buf = cv2.imencode(".png", bgra)
        b64_data = base64.b64encode(buf).decode("ascii")
        
        await client.send_job(
            "layer.create",
            {
                "doc_id": doc_id,
                "name": layer_name,
                "layer_type": "paintLayer",
                "parent_group": "BG_Environment",
            },
        )
        await client.send_job(
            "layer.set_pixel_tile",
            {
                "doc_id": doc_id,
                "layer_name": layer_name,
                "tile_index": 0,
                "x": 0,
                "y": 0,
                "width": width,
                "height": height,
                "data_base64": b64_data,
            },
        )

    # 2. Render & Push Sky Plane
    sky_rgba = generate_sky_plane(width, height)
    await _push_plane("01_BG_Sky_Sun", sky_rgba)
    
    # 3. Render & Push Bleachers & Infield Plane
    bleachers_rgba = generate_bleachers_plane(width, height)
    await _push_plane("02_BG_Stadium_Stands", bleachers_rgba)
    
    # 4. Render & Push Running Track Plane
    track_rgba = generate_track_plane(width, height)
    await _push_plane("03_Track_Polyurethane", track_rgba)
    
    logger.info("Successfully pushed all 3 stadium planes to Krita!")
    return {
        "success": True,
        "doc_id": doc_id,
        "planes": ["01_BG_Sky_Sun", "02_BG_Stadium_Stands", "03_Track_Polyurethane"],
    }
