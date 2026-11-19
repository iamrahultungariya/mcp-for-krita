"""Cinematic 10-Second Anime Running Video Renderer.

Combines:
1. Multi-plane continuous parallax stadium background (Sky, Stands, Track)
2. 12-frame fluid athletic anime runner cycle (animated on 2s)
3. Dynamic flying sweat particle physics simulation with air drag
4. Camera impact bob (synchronized with foot strikes)
5. Speed lines, wind streaks, and cinematic golden-hour color grading
6. H.264 / MP4 240-frame 24 FPS video encoding
"""

from __future__ import annotations

import logging
import math
import os
import random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np

from krita_mcp_lazy.animation.athletic_character_rig import AthleticRunnerPalette
from krita_mcp_lazy.animation.cinematic_stadium_builder import create_cinematic_stadium_composite
from krita_mcp_lazy.animation.run_cycle_engine import RunCycleEngine, StridePose, render_stride_frame

logger = logging.getLogger(__name__)


@dataclass
class SweatParticle:
    """A physical sweat droplet with position, velocity, life, and radius."""
    x: float
    y: float
    vx: float
    vy: float
    life: float        # Remaining lifetime 0..1
    max_life: float
    radius: float


class SweatParticleSystem:
    """Simulates realistic sweat droplets flying off an athletic runner."""

    def __init__(self, gravity: float = 380.0, air_drag: float = 0.94) -> None:
        self.particles: List[SweatParticle] = []
        self.gravity = gravity
        self.air_drag = air_drag

    def emit(self, origin: Tuple[float, float], count: int = 4, base_speed: float = 18.0) -> None:
        """Emit fresh droplets from the athlete's forehead or neck."""
        ox, oy = origin
        for _ in range(count):
            # Spray backwards (negative X) with upward and downward dispersal
            angle_rad = math.radians(random.uniform(140.0, 215.0))
            speed = random.uniform(base_speed * 0.7, base_speed * 1.4)
            vx = speed * math.cos(angle_rad) * 25.0
            vy = speed * math.sin(angle_rad) * 15.0 - random.uniform(20.0, 60.0)
            
            life = random.uniform(0.35, 0.75)
            rad = random.uniform(2.2, 4.5)
            self.particles.append(
                SweatParticle(x=ox, y=oy, vx=vx, vy=vy, life=life, max_life=life, radius=rad)
            )

    def update(self, dt: float = 1.0 / 24.0) -> None:
        """Step physics simulation."""
        surviving: List[SweatParticle] = []
        for p in self.particles:
            p.life -= dt
            if p.life <= 0:
                continue
            p.vx *= self.air_drag
            p.vy += self.gravity * dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            surviving.append(p)
        self.particles = surviving

    def draw(self, canvas: np.ndarray, scale: float = 1.0) -> None:
        """Draw illuminated sweat particles with golden glint."""
        h, w = canvas.shape[:2]
        for p in self.particles:
            ix = int(p.x)
            iy = int(p.y)
            if 0 <= ix < w and 0 <= iy < h:
                alpha = max(0.0, min(1.0, p.life / p.max_life))
                r = max(1, int(p.radius * scale))
                # Brilliant white core with golden-sun halo
                glow_color = np.array([255, 245, 210], dtype=np.float32)  # Sunlight glint
                
                # Draw droplet teardrop / streak
                streak_len = max(2, int(abs(p.vx) * 0.04 * scale))
                cv2.line(canvas, (ix, iy), (min(w - 1, ix + streak_len), iy), (255, 255, 255), r, cv2.LINE_AA)
                cv2.circle(canvas, (ix, iy), r, (255, 255, 255), -1, cv2.LINE_AA)


def render_speed_lines(canvas: np.ndarray, frame_idx: int, speed: float = 1.0) -> None:
    """Overlay dynamic athletic anime speed lines along canvas margins."""
    h, w = canvas.shape[:2]
    np.random.seed(frame_idx * 17)
    
    # Draw horizontal motion wind streaks
    num_streaks = 18
    for _ in range(num_streaks):
        y = np.random.randint(int(h * 0.15), int(h * 0.88))
        x_end = np.random.randint(0, int(w * 0.45))
        length = np.random.randint(int(w * 0.08), int(w * 0.22))
        x_start = max(0, x_end - length)
        thickness = np.random.randint(1, 3)
        # Semi-transparent white wind streak
        cv2.line(canvas, (x_start, y), (x_end, y), (255, 255, 255), thickness, cv2.LINE_AA)


def apply_cinematic_color_grade(frame: np.ndarray) -> np.ndarray:
    """Apply rich, high-contrast, saturated golden-hour anime color grading."""
    # Convert BGR to float [0, 1]
    f = frame.astype(np.float32) / 255.0
    
    # 1. S-Curve Contrast Enhancement (rich blacks, punchy mids)
    f = 3.0 * (f ** 2) - 2.0 * (f ** 3)
    
    # 2. Warm Golden Sunlight Cast
    # Slightly boost Red and Green in highlights
    warm_tint = np.array([0.96, 1.02, 1.06], dtype=np.float32)  # BGR order
    f = f * warm_tint
    
    # 3. Vignette along borders
    h, w = frame.shape[:2]
    yy, xx = np.ogrid[:h, :w]
    cx, cy = w / 2.0, h / 2.0
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    max_d = np.sqrt(cx ** 2 + cy ** 2)
    vignette = 1.0 - 0.22 * (dist / max_d) ** 2
    f = f * vignette[:, :, np.newaxis]
    
    return np.clip(f * 255.0, 0, 255).astype(np.uint8)


def render_10s_animation_video(
    output_mp4_path: str = "output/anime_running_10s.mp4",
    total_frames: int = 240,       # 10.0 seconds at 24 fps
    fps: int = 24,
    width: int = 1920,
    height: int = 1080,
) -> Dict[str, Any]:
    """Render full 10-second master running animation video with parallax & physics."""
    os.makedirs(os.path.dirname(os.path.abspath(output_mp4_path)), exist_ok=True)
    logger.info("Starting master 10s video render (%d frames, %dx%d @ %dfps)...", total_frames, width, height, fps)
    
    engine = RunCycleEngine()
    poses = engine.get_stride_poses()  # 12 poses
    
    # Pre-render the 12 character stride frames for speed and stability
    logger.info("Pre-rendering 12 athletic character stride poses...")
    char_frames = [render_stride_frame(p, width, height, engine.palette) for p in poses]
    
    # Initialize VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_mp4_path, fourcc, float(fps), (width, height))
    
    if not writer.isOpened():
        raise RuntimeError(f"Failed to open VideoWriter for path: {output_mp4_path}")

    sweat_system = SweatParticleSystem()
    parallax_offset = 0.0
    track_speed_px = 16.0  # Pixels per frame forward momentum
    
    for frame_idx in range(total_frames):
        # 1. Compute Stride Index (animated on 2s = each stride pose shown for 2 video frames)
        stride_idx = (frame_idx // 2) % 12
        pose = poses[stride_idx]
        char_rgba = char_frames[stride_idx]
        
        # 2. Camera Impact Shake (subtle vertical bob on foot-strikes at contact frames)
        cam_shake_y = 0
        if stride_idx in (0, 6):  # Foot-strike impact frames
            cam_shake_y = 3 if (frame_idx % 2 == 0) else -2
            
        # 3. Update Multi-Plane Parallax Background
        parallax_offset += track_speed_px
        bg_frame = create_cinematic_stadium_composite(width, height, offset_x=parallax_offset)
        
        # Apply vertical camera bob to background
        if cam_shake_y != 0:
            M = np.float32([[1, 0, 0], [0, 1, cam_shake_y]])
            bg_frame = cv2.warpAffine(bg_frame, M, (width, height), borderMode=cv2.BORDER_REFLECT)
            
        # 4. Composite Character onto Background
        alpha = (char_rgba[:, :, 3].astype(np.float32) / 255.0)[:, :, np.newaxis]
        char_rgb = char_rgba[:, :, :3].astype(np.float32)
        composite = bg_frame.astype(np.float32) * (1.0 - alpha) + char_rgb * alpha
        composite = np.clip(composite, 0, 255).astype(np.uint8)
        
        # 5. Emit & Update Flying Sweat Particles
        head_x = int(width * 0.48 + 28 * (height / 1080.0))
        head_y = int(height * 0.62 - 130 * (height / 1080.0) + pose.vertical_bob_px * (height / 1080.0))
        if pose.sweat_burst and (frame_idx % 2 == 0):
            sweat_system.emit(origin=(head_x - 30, head_y), count=random.randint(4, 7), base_speed=14.0)
            
        sweat_system.update(dt=1.0 / fps)
        sweat_system.draw(composite, scale=height / 1080.0)
        
        # 6. Motion Speed Lines
        render_speed_lines(composite, frame_idx)
        
        # 7. Cinematic Color Grade (Warm, saturated, punchy contrast)
        graded = apply_cinematic_color_grade(composite)
        
        # Write frame to video
        writer.write(graded)

    writer.release()
    file_size = os.path.getsize(output_mp4_path)
    logger.info("Video successfully written to %s (Size: %.2f MB)", output_mp4_path, file_size / (1024 * 1024))
    
    return {
        "success": True,
        "video_path": output_mp4_path,
        "duration_seconds": total_frames / fps,
        "total_frames": total_frames,
        "fps": fps,
        "resolution": f"{width}x{height}",
        "file_size_bytes": file_size,
    }
