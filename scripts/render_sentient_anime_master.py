"""Master script to render 10-second Anime Running Animation and sync with Krita canvas.

Combines:
1. BridgeStateOracle auto-sensing (checks live Krita without spoonfeeding)
2. High-fidelity anime character rendering (AnimeCharacterArtEngine)
3. Multi-plane stadium parallax conveyor (Sky, Bleachers, Polyurethane Track)
4. Dynamic sweat particle physics and wind speedlines
5. 240 frames, 24 FPS (exact 10.0s) high-definition master MP4 export
"""

import asyncio
import base64
import os
import sys
from pathlib import Path

import cv2
import numpy as np

# Ensure workspace root is in sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "src"))

from krita_mcp_lazy.animation.cinematic_stadium_builder import create_cinematic_stadium_composite
from krita_mcp_lazy.animation.cinematic_video_renderer import render_10s_animation_video
from krita_mcp_lazy.animation.run_cycle_engine import RunCycleEngine, render_stride_frame
from krita_mcp_lazy.bridge.oracle import get_oracle
from krita_mcp_lazy.color_grading.adjustments import ColorGradingManager
from krita_mcp_lazy.transport.client import AsyncIPCClient


async def scaffold_live_krita_layers(client: AsyncIPCClient, doc_id: str, width: int, height: int) -> None:
    """Scaffold full semantic layer hierarchy into live Krita document."""
    print(f"\n[Krita Sync] Scaffolding production layers into doc '{doc_id}' ({width}x{height})...")

    # 1. Background Composite
    print("  -> Generating stadium background plane...")
    bg_img = create_cinematic_stadium_composite(width, height, offset_x=0.0)
    bg_bgra = cv2.cvtColor(bg_img, cv2.COLOR_RGB2BGRA)
    _, buf = cv2.imencode(".png", bg_bgra)
    bg_b64 = base64.b64encode(buf).decode("ascii")

    await client.send_job("layer.create", {"doc_id": doc_id, "name": "01_Stadium_Background", "layer_type": "paintLayer"})
    await client.send_job("layer.set_pixel_tile", {
        "doc_id": doc_id, "layer_name": "01_Stadium_Background", "x": 0, "y": 0, "width": width, "height": height, "pixels_b64": bg_b64
    })

    # 2. Anime Character Stride Pose (Frame 0 Contact)
    print("  -> Rendering authentic anime character layers...")
    engine = RunCycleEngine(width=width, height=height)
    pose = engine.get_stride_poses()[0]
    char_layers = engine.art_engine.render_cel_layers(
        engine.art_engine.__class__.__name__ and None or
        __import__("krita_mcp_lazy.character.anime_artist_engine", fromlist=["CharacterPose"]).CharacterPose(
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
    )

    layers_to_push = [
        ("02_Char_Flats", char_layers["Flats"], "normal", 255),
        ("03_Char_Cel_Shadows", char_layers["Cel_Shadows"], "multiply", 210),
        ("04_Char_Hair_Rim", char_layers["Hair_Specular"], "screen", 240),
        ("05_Char_Lineart", char_layers["Lineart"], "normal", 255),
    ]

    for lyr_name, lyr_arr, b_mode, opac in layers_to_push:
        print(f"  -> Streaming layer '{lyr_name}' ({b_mode})...")
        _, lyr_buf = cv2.imencode(".png", lyr_arr)
        lyr_b64 = base64.b64encode(lyr_buf).decode("ascii")
        await client.send_job("layer.create", {
            "doc_id": doc_id, "name": lyr_name, "layer_type": "paintLayer", "blending_mode": b_mode, "opacity": opac
        })
        await client.send_job("layer.set_pixel_tile", {
            "doc_id": doc_id, "layer_name": lyr_name, "x": 0, "y": 0, "width": width, "height": height, "pixels_b64": lyr_b64
        })

    # Enable alpha inheritance on Cel Shadows
    await client.send_job("layer.set_inherit_alpha", {"doc_id": doc_id, "layer_name": "03_Char_Cel_Shadows", "inherit_alpha": True})

    # 3. Apply In-App Color Grading Stack
    print("  -> Applying native Krita color grading stack (Golden Hour)...")
    grading_mgr = ColorGradingManager()
    await grading_mgr.scaffold_color_grading_stack(client, doc_id=doc_id, profile="golden_hour_anime")

    # Refresh canvas
    await client.send_job("document.refresh", {"doc_id": doc_id})
    print("  [OK] Successfully synchronized all layers to Krita canvas!")


def main() -> None:
    print("=" * 75)
    print("SENTIENT KRITA ANIME ENGINE - MASTER 10-SECOND VIDEO PRODUCTION")
    print("Character: Anime Creator (Athletic Redesign)")
    print("Output: output/anime_running_10s_master.mp4 (240 Frames @ 24 FPS, 10.0s)")
    print("=" * 75)

    # 1. Proactive Environment Auto-Sensing
    oracle = get_oracle()
    state = oracle.probe(query_doc=True)
    print(f"\n[Oracle] Bridge Status: live={state.bridge_live}, port={state.port}")
    if state.bridge_live and state.active_document:
        doc = state.active_document
        print(f"[Oracle] Auto-detected open Krita document: '{doc.get('name')}' ({doc.get('width')}x{doc.get('height')})")
        doc_id = doc.get("doc_id", "active")
        w = int(doc.get("width", 1920))
        h = int(doc.get("height", 1080))
        # Sync layers into Krita
        try:
            client = AsyncIPCClient(host=oracle.host, port=oracle.port)
            asyncio.run(client.connect())
            asyncio.run(scaffold_live_krita_layers(client, doc_id=doc_id, width=w, height=h))
            asyncio.run(client.disconnect())
        except Exception as exc:
            print(f"[Oracle Warning] Could not sync layers to Krita: {exc}")
    else:
        print("[Oracle] Krita is not currently open or no active document. Proceeding with master video render...")

    # 2. Render Master 10-Second Video
    output_mp4 = "output/anime_running_10s_master.mp4"
    print(f"\n[Render] Encoding 240 frames at 24 FPS (10.0s) to '{output_mp4}'...")
    res = render_10s_animation_video(
        output_mp4_path=output_mp4,
        total_frames=240,
        fps=24,
        width=1920,
        height=1080,
    )

    if res.get("success"):
        file_size_mb = os.path.getsize(output_mp4) / (1024 * 1024)
        print("\n" + "=" * 75)
        print("MASTER VIDEO PRODUCTION COMPLETE!")
        print(f"Deliverable Path: {os.path.abspath(output_mp4)}")
        print(f"Duration: 10.0 seconds ({res.get('total_frames')} frames @ {res.get('fps')} fps)")
        print(f"File Size: {file_size_mb:.2f} MB")
        print("=" * 75)
    else:
        print(f"\n[ERROR] Video rendering failed: {res.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
