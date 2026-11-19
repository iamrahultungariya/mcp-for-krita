"""CLI script to autonomously paint an anime movie poster directly onto Krita's canvas."""

import argparse
import asyncio
import os
import sys

# Ensure repository root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from krita_mcp_lazy.core.security import get_or_create_shared_token
from krita_mcp_lazy.server.tools_autonomous_painter import paint_poster
from krita_mcp_lazy.transport.client import AsyncIPCClient


async def main() -> None:
    parser = argparse.ArgumentParser(description="Autonomously paint anime movie poster directly onto Krita canvas.")
    parser.add_argument("--prompt", type=str, default="Whispers in the Starlight cute anime romance movie poster")
    parser.add_argument("--doc-id", type=str, default=None)
    parser.add_argument("--width", type=int, default=1240, help="Canvas width (default: 1240 for fast render, 2480 for 300 DPI A4)")
    parser.add_argument("--height", type=int, default=1754, help="Canvas height (default: 1754, 3508 for 300 DPI A4)")
    parser.add_argument("--user-image", type=str, default=None, help="Optional user reference image path")
    parser.add_argument("--output", type=str, default=None, help="Output flattened composite PNG path")
    args = parser.parse_args()

    token = get_or_create_shared_token()
    client = AsyncIPCClient(host="127.0.0.1", port=18812, token=token, timeout=10.0)

    is_live = False
    doc_id = args.doc_id

    try:
        await client.connect()
        ping_res = await client.send_job("ping", {})
        if ping_res.result.get("pong"):
            is_live = True
            print(">>> CONNECTED TO LIVE KRITA INSTANCE (Port 18812)")
    except Exception as exc:
        print(f">>> Krita live bridge not detected ({exc}). Running in headless synthesis mode.")

    if is_live and not doc_id:
        # Create fresh canvas document in Krita
        print(f">>> Initializing Krita canvas {args.width}x{args.height}...")
        res_doc = await client.send_job(
            "document.create",
            {
                "width": args.width,
                "height": args.height,
                "name": "Whispers_In_The_Starlight_Live",
                "resolution_dpi": 300.0,
                "color_model": "RGBA",
                "bit_depth": "U8",
            },
        )
        doc_id = res_doc.result.get("doc_id", "doc_live_01")
        print(f">>> Created Krita document with ID: {doc_id}")
    elif not doc_id:
        doc_id = "doc_headless_01"

    out_file = args.output or os.path.join("output", "anime_movie_poster_autonomous.png")
    print(f">>> Commencing autonomous layer-by-layer digital painting...")

    result = await paint_poster(
        prompt=args.prompt,
        doc_id=doc_id,
        width=args.width,
        height=args.height,
        client=client,
        user_image_path=args.user_image,
        output_png_path=out_file,
    )

    print("\n================ PAINTING SUMMARY ================")
    print(f"Target Document ID: {result['doc_id']}")
    print(f"Total Layers Streamed: {result['layers_painted']}")
    print("Streamed Layer Hierarchy:")
    for idx, lyr in enumerate(result["layer_names"], 1):
        print(f"  [{idx:02d}] {lyr}")
    print(f"Composite Presentation PNG: {result['output_png_path']}")
    print("==================================================\n")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
