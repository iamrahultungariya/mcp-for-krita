"""Tests for the Gemini Imagen / Key art generator."""

import os
from unittest.mock import MagicMock, patch
from PIL import Image
import pytest


def test_returns_none_when_no_key_and_no_user_image():
    """Without an API key and without user image, should return None gracefully."""
    with patch.dict(os.environ, {}, clear=True):
        from krita_mcp_lazy.image_gen.gemini_gen import generate_character_art

        result = generate_character_art("anime lovers at night", 200, 300)
        assert result is None


def test_loads_user_image_when_path_provided(tmp_path):
    """When a user image is supplied, load and resize to target canvas."""
    from krita_mcp_lazy.image_gen.gemini_gen import generate_character_art

    ref = Image.new("RGBA", (100, 150), (255, 100, 150, 255))
    ref_path = str(tmp_path / "reference_lovers.png")
    ref.save(ref_path)

    result = generate_character_art("anime", 200, 300, user_image_path=ref_path)
    assert result is not None
    assert result.size == (200, 300)
    assert result.mode == "RGBA"


def test_calls_gemini_when_key_present():
    """When GEMINI_API_KEY is present, should invoke the model caller."""
    fake_img = Image.new("RGBA", (200, 300), (40, 20, 80, 255))
    with patch.dict(os.environ, {"GEMINI_API_KEY": "test_api_key"}):
        with patch("krita_mcp_lazy.image_gen.gemini_gen._call_gemini_imagen") as mock_api:
            mock_api.return_value = fake_img
            from krita_mcp_lazy.image_gen.gemini_gen import generate_character_art

            res = generate_character_art("anime hero couple", 200, 300)
            mock_api.assert_called_once()
            assert res is not None
            assert res.size == (200, 300)
