"""Autonomous Studio Cel-Hybrid drawing, modular rig packaging, and fidelity verification CLI."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock

# Add src to sys.path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT / "src"))

from krita_mcp_lazy.server.tools_cel_studio import live_paint_anime_character
from krita_mcp_lazy.transport.client import AsyncIPCClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("studio_anime")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Autonomous Studio Cel-Hybrid Anime Drawing & Modular Rig Engine"
    )
    parser.add_argument(
        "--input",
        type=str,
        default=r"C:\Users\Rahul\.gemini\antigravity\brain\47071ca1-a878-4bd8-8e36-2901894c7575\.user_uploaded\media_1795071083045_a1bcd4d7.jpg",
        help="Path to reference character or scene illustration",
    )
    parser.add_argument(
        "--doc-id",
        type=str,
        default="studio_anime_01",
        help="Target Krita document ID",
    )
    parser.add_argument(
        "--char-id",
        type=str,
        default="anime_creator",
        help="Modular character rig identifier",
    )
    parser.add_argument(
        "--char-name",
        type=str,
        default="Anime Creator",
        help="Display name for character rig",
    )
    parser.add_argument(
        "--live-tablet",
        action="store_true",
        help="Stream synthetic QTabletEvent strokes directly to Krita canvas viewport",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="Directory to save final composite PNG and debug artifacts",
    )
    parser.add_argument(
        "--library-root",
        type=str,
        default="asset_library/characters",
        help="Root path for reusable character rig manifests",
    )

    args = parser.parse_args()

    input_path = os.path.abspath(args.input)
    if not os.path.exists(input_path):
        print(f"ERROR: Reference image not found at: {input_path}")
        sys.exit(1)

    print("=" * 80)
    print(" STUDIO CEL-HYBRID ANIME DRAWING & MODULAR RIG ENGINE")
    print(f" Reference Art: {input_path}")
    print(f" Target Document: {args.doc_id}")
    print(f" Character ID: {args.char_id} ('{args.char_name}')")
    print(f" Live Tablet Strokes: {args.live_tablet}")
    print("=" * 80)

    # Attempt connection to live Krita IPC
    ipc_client: Any = AsyncIPCClient()
    is_live_krita = False
    try:
        await ipc_client.connect()
        is_live_krita = True
        print("[IPC] Successfully connected to live Krita instance (127.0.0.1:18812)!")
    except Exception as e:
        print(f"[IPC] Live Krita not reachable ({e}). Running in standalone studio simulation mode.")
        mock_client = AsyncMock()
        mock_client.send_job.return_value.result = {
            "created": True,
            "layer_id": "lyr_sim",
            "updated": True,
            "inherit_alpha": True,
        }
        ipc_client = mock_client

    out_png = os.path.join(args.output_dir, f"painted_cel_{args.doc_id}.png")

    try:
        res = await live_paint_anime_character(
            image_path=input_path,
            doc_id=args.doc_id,
            client=ipc_client,
            use_live_tablet=args.live_tablet,
            char_id=args.char_id,
            char_name=args.char_name,
            output_png_path=out_png,
            library_root=args.library_root,
        )

        fidelity = res.get("fidelity", {})
        print("\n" + "=" * 80)
        print(" PAINTING & MODULAR RIGGING EXECUTION SUMMARY")
        print("=" * 80)
        print(f" Success:                {res.get('success')}")
        print(f" Krita Document:         {res.get('doc_id')}")
        print(f" Modular Rig Groups:     {res.get('rig_groups')} groups scaffolded")
        print(f" Trapped Color Flats:    {res.get('flats_count')} regions")
        print(f" Vector Inking Strokes:  {res.get('vector_strokes_count')} strokes")
        print(f" Rig Manifest Saved To:  {res.get('manifest_path')}")
        print(f" Composite Output PNG:   {res.get('output_png_path')}")
        print("-" * 80)
        print(" VISION FIDELITY SCORECARD:")
        print(f"   * SSIM Score:         {fidelity.get('ssim', 0):.4f} (Threshold >= 0.88)")
        print(f"   * Edge IoU Score:     {fidelity.get('edge_iou', 0):.4f} (Threshold >= 0.80)")
        print(f"   * Mean Squared Error: {fidelity.get('mean_squared_error', 0):.4f}")
        print(f"   * Quality Certified:  {'APPROVED (Ditto Match)' if fidelity.get('is_approved') else 'REQUIRES RE-PASS'}")
        print("=" * 80)

    finally:
        if is_live_krita and hasattr(ipc_client, "disconnect"):
            await ipc_client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
