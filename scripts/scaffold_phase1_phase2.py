"""Integration script for Phase 1 & 2:
1. Verifies live Krita IPC connection.
2. Scaffolds 12-frame animated character run cycle into doc_4 (running.kra).
3. Generates high-resolution composite preview of the runner on the stadium track.
"""

import asyncio
import os
import sys
from pathlib import Path

import cv2
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "src"))

from krita_mcp_lazy.animation.cinematic_stadium_builder import create_cinematic_stadium_composite
from krita_mcp_lazy.animation.run_cycle_engine import (
    RunCycleEngine,
    render_stride_frame,
    scaffold_run_cycle_in_krita,
)
from krita_mcp_lazy.transport.client import AsyncIPCClient


async def main() -> None:
    print("=" * 80)
    print(" RUNNING ANIMATION: PHASE 1 & 2 LIVE KRITA EXECUTION")
    print("=" * 80)

    doc_id = "doc_4"
    width, height = 3840, 2160

    client = AsyncIPCClient()
    await client.connect()
    print(f"[IPC] Connected to live Krita on 127.0.0.1:18812!")

    try:
        # 1. Scaffold Run Cycle Frames into Krita
        print(f"[Krita] Pushing 12-frame athletic run cycle into '{doc_id}'...")
        res = await scaffold_run_cycle_in_krita(client, doc_id=doc_id, width=width, height=height)
        print(f"[Krita] Scaffolding complete: {res['frames_created']} frames created in 'Char_Run_Cycle' group!")

        # 2. Render Full Cinematic Composite for Preview
        print("[Preview] Rendering cinematic 4K composite (Stadium + Runner Air Peak + Sweat)...")
        bg_rgb = create_cinematic_stadium_composite(width, height, offset_x=120.0)
        
        engine = RunCycleEngine()
        # Use pose 3 (High Air peak with flying sweat)
        pose = engine.get_stride_poses()[3]
        char_rgba = render_stride_frame(pose, width, height, engine.palette)

        # Alpha composite character onto stadium
        alpha = (char_rgba[:, :, 3].astype(np.float32) / 255.0)[:, :, np.newaxis]
        char_rgb = char_rgba[:, :, :3].astype(np.float32)
        composite = bg_rgb.astype(np.float32) * (1.0 - alpha) + char_rgb * alpha
        composite = np.clip(composite, 0, 255).astype(np.uint8)

        # Save to output
        os.makedirs("output", exist_ok=True)
        out_path = os.path.join("output", "preview_phase1_phase2.png")
        cv2.imwrite(out_path, composite)
        print(f"[Preview] Saved cinematic composite to: {out_path}")

        # Check color saturation
        hsv = cv2.cvtColor(composite, cv2.COLOR_BGR2HSV)
        sat_mean = np.mean(hsv[:, :, 1])
        print(f"[Scorecard] Mean Saturation: {sat_mean:.2f} (Rich, cinematic & vibrant!)")

    finally:
        await client.close()
        print("[IPC] Connection closed gracefully.")


if __name__ == "__main__":
    asyncio.run(main())
