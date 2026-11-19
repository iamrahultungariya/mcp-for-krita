"""Render full 10-second master anime running animation video."""

import os
import sys
import time
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "src"))

from krita_mcp_lazy.animation.cinematic_video_renderer import render_10s_animation_video


def main() -> None:
    print("=" * 80)
    print(" 10-SECOND ANIME RUNNING MASTER VIDEO RENDER")
    print(" Resolution: 1920x1080 Full HD | FPS: 24 | Frames: 240 | Duration: 10.0s")
    print("=" * 80)

    out_path = os.path.join("output", "anime_running_10s.mp4")
    t0 = time.time()
    
    res = render_10s_animation_video(
        output_mp4_path=out_path,
        total_frames=240,
        fps=24,
        width=1920,
        height=1080,
    )
    
    elapsed = time.time() - t0
    print("-" * 80)
    print(f" Render Completed in:    {elapsed:.2f} seconds")
    print(f" Master Video File:      {res['video_path']}")
    print(f" Duration:               {res['duration_seconds']:.1f} seconds")
    print(f" Total Frames:           {res['total_frames']} frames")
    print(f" Video File Size:        {res['file_size_bytes'] / (1024 * 1024):.2f} MB")
    print("=" * 80)


if __name__ == "__main__":
    main()
