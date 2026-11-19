"""Streams pixel layer buffers into Krita canvas in manageable memory-safe tiles."""

from __future__ import annotations

import base64
import logging
from typing import Any, Dict

from krita_mcp_lazy.painting_director.layers import LayerBuffer

logger = logging.getLogger(__name__)


class KritaPusher:
    """Manages layer creation, tile streaming, and instant viewport projection refresh."""

    def __init__(self, client: Any, tile_height: int = 256) -> None:
        self.client = client
        self.tile_height = max(16, tile_height)

    async def push_layer(self, doc_id: str, layer_buf: LayerBuffer) -> Dict[str, Any]:
        """Create new paint layer in Krita and stream pixel data row-by-row in tiles."""
        logger.info("Streaming layer '%s' to document '%s'...", layer_buf.name, doc_id)

        # 1. Create target paint layer with proper blending mode
        res_create = await self.client.send_job(
            "layer.create",
            {
                "doc_id": doc_id,
                "name": layer_buf.name,
                "layer_type": "paintLayer",
                "opacity": layer_buf.opacity,
                "blending_mode": layer_buf.blend_mode,
            },
        )
        layer_id = res_create.result.get("layer_id", layer_buf.name) if hasattr(res_create, "result") else layer_buf.name

        # 2. Stream tiles
        stride = layer_buf.width * 4
        total_h = layer_buf.height

        for y_start in range(0, total_h, self.tile_height):
            tile_h = min(self.tile_height, total_h - y_start)
            byte_start = y_start * stride
            byte_end = byte_start + (tile_h * stride)
            tile_bytes = layer_buf.pixels[byte_start:byte_end]

            tile_b64 = base64.b64encode(tile_bytes).decode("ascii")

            await self.client.send_job(
                "layer.set_pixel_tile",
                {
                    "doc_id": doc_id,
                    "layer_id": layer_id,
                    "layer_name": layer_buf.name,
                    "x": 0,
                    "y": y_start,
                    "width": layer_buf.width,
                    "height": tile_h,
                    "pixels_b64": tile_b64,
                },
            )

        # 3. Trigger immediate viewport refresh so changes appear on screen in Krita
        await self.client.send_job(
            "document.refresh",
            {
                "doc_id": doc_id,
            },
        )

        logger.info("Finished streaming layer '%s'.", layer_buf.name)
        return {
            "layer_id": layer_id,
            "name": layer_buf.name,
            "tiles_streamed": (total_h + self.tile_height - 1) // self.tile_height,
        }
