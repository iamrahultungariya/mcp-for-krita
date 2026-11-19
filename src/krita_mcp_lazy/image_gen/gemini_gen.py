"""Gemini Imagen & user key art generation wrapper."""

from __future__ import annotations

import io
import logging
import os
from typing import Optional

from PIL import Image

logger = logging.getLogger(__name__)


def _call_gemini_imagen(prompt: str, width: int, height: int) -> Optional[Image.Image]:
    """Call Gemini Imagen 3 model via google-genai SDK to generate key artwork."""
    try:
        from google import genai

        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            return None

        client = genai.Client(api_key=api_key)
        # Request generation from imagen-3.0-generate-002
        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=prompt,
            config={
                "number_of_images": 1,
                "output_mime_type": "image/png",
                "aspect_ratio": "3:4" if height > width else "1:1",
            },
        )

        if response.generated_images:
            raw_bytes = response.generated_images[0].image.image_bytes
            img = Image.open(io.BytesIO(raw_bytes))
            fitted = img.resize((width, height), Image.LANCZOS).convert("RGBA")
            return fitted
    except Exception as exc:
        logger.warning("Gemini Imagen generation failed, falling back to procedural: %s", exc)
        return None

    return None


def generate_character_art(
    prompt: str,
    width: int,
    height: int,
    user_image_path: Optional[str] = None,
) -> Optional[Image.Image]:
    """Generate or load character key art.

    Priority:
    1. If `user_image_path` provided and valid -> load and fit to canvas.
    2. If `GEMINI_API_KEY` environment variable exists -> query Imagen 3.
    3. Return None to allow procedural painter to construct soft-brushed figures.
    """
    if user_image_path and os.path.exists(user_image_path):
        try:
            user_img = Image.open(user_image_path)
            fitted = user_img.resize((width, height), Image.LANCZOS).convert("RGBA")
            logger.info("Loaded and adapted user-provided image from: %s", user_image_path)
            return fitted
        except Exception as err:
            logger.warning("Failed to load user image from %s: %s", user_image_path, err)

    if os.environ.get("GEMINI_API_KEY"):
        return _call_gemini_imagen(prompt, width, height)

    return None
