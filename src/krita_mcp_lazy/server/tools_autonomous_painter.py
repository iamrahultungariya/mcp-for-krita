"""Autonomous painting orchestration tool executing multi-layer professional digital painting."""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from krita_mcp_lazy.art_planning.poster_concept import get_whispers_in_starlight_spec
from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.image_gen.gemini_gen import generate_character_art
from krita_mcp_lazy.krita_pusher.pusher import KritaPusher
from krita_mcp_lazy.painting_director.director import PaintingDirector, composite_to_png
from krita_mcp_lazy.transport.client import AsyncIPCClient

logger = logging.getLogger(__name__)


async def paint_poster(
    prompt: str,
    doc_id: str,
    width: int = 2480,
    height: int = 3508,
    client: Optional[Any] = None,
    user_image_path: Optional[str] = None,
    output_png_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute autonomous painting pass, streaming layers directly to Krita canvas in tiles."""
    ipc_client = client
    own_client = False
    if ipc_client is None:
        ipc_client = AsyncIPCClient()
        await ipc_client.connect()
        own_client = True

    try:
        spec = get_whispers_in_starlight_spec()
        director = PaintingDirector(spec)

        # 1. Key character art synthesis (via Gemini Imagen or user reference if provided)
        logger.info("Evaluating character art source for prompt: '%s'...", prompt)
        char_art = generate_character_art(prompt, width, height, user_image_path=user_image_path)

        # 2. Render all 11 professional layers in memory
        logger.info("Rendering all 11 semantic layers at %dx%d...", width, height)
        layer_buffers = director.render_all_layers(width, height, gemini_art=char_art)

        # 3. Stream each layer to Krita live canvas via tile pusher
        pusher = KritaPusher(ipc_client)
        pushed_layers: List[str] = []
        for lbuf in layer_buffers:
            res = await pusher.push_layer(doc_id, lbuf)
            pushed_layers.append(res["name"])

        # 4. Save flat high-resolution composite artifact
        if not output_png_path:
            os.makedirs("output", exist_ok=True)
            output_png_path = os.path.join("output", f"painted_poster_{doc_id}.png")

        composite_to_png(layer_buffers, width, height, output_png_path)
        logger.info("Autonomous painting complete. Output saved to %s", output_png_path)

        return {
            "doc_id": doc_id,
            "layers_painted": len(pushed_layers),
            "layer_names": pushed_layers,
            "output_png_path": output_png_path,
            "success": True,
        }
    finally:
        if own_client and ipc_client is not None:
            await ipc_client.close()


def register_autonomous_painter_tools(server: Any, config: Optional[KritaConfig] = None) -> None:
    """Register autonomous painting tools with the FastMCP server."""

    @server.tool(name="krita_paint_poster", description="Autonomously paint a professional anime movie poster layer-by-layer directly onto Krita's canvas.")
    async def handle_paint_poster(
        prompt: str = "Whispers in the Starlight cute anime movie love poster",
        doc_id: str = "default",
        width: int = 2480,
        height: int = 3508,
        user_image_path: Optional[str] = None,
        output_png_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Autonomously render an authentic anime illustration with celestial sky, lover silhouettes, and typography."""
        return await paint_poster(
            prompt=prompt,
            doc_id=doc_id,
            width=width,
            height=height,
            user_image_path=user_image_path,
            output_png_path=output_png_path,
        )
