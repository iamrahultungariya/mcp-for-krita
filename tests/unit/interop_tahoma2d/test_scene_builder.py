import os
import pytest
from krita_mcp_lazy.interop_tahoma2d.scene_builder import Tahoma2DSceneBuilder


def test_scene_tnz_generation(tmp_path):
    builder = Tahoma2DSceneBuilder()
    manifest = {
        "character": "Hero",
        "canvas_width": 1920,
        "canvas_height": 1080,
        "parts": [
            {"name": "Head", "file": "Head.png", "pivot_x": 0.5, "pivot_y": 0.9, "z_order": 5},
            {"name": "Torso", "file": "Torso.png", "pivot_x": 0.5, "pivot_y": 0.5, "z_order": 4},
        ],
    }
    tnz_path = builder.generate_scene_xml(manifest=manifest, output_dir=str(tmp_path))
    assert tnz_path.endswith(".tnz")
    assert tmp_path.joinpath("scene.tnz").exists()

    with open(tnz_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "<generator>Tahoma2D</generator>" in content
    assert "Head.png" in content
    assert "Torso.png" in content


def test_verify_roundtrip(tmp_path):
    builder = Tahoma2DSceneBuilder()
    manifest = {
        "character": "Hero",
        "canvas_width": 1920,
        "canvas_height": 1080,
        "parts": [
            {"name": "Head", "file": "Head.png", "pivot_x": 0.5, "pivot_y": 0.9, "z_order": 5},
            {"name": "Torso", "file": "Torso.png", "pivot_x": 0.5, "pivot_y": 0.5, "z_order": 4},
        ],
    }
    tnz_path = builder.generate_scene_xml(manifest=manifest, output_dir=str(tmp_path))
    verification = builder.verify_roundtrip(manifest=manifest, tnz_path=tnz_path)
    assert verification["valid"] is True
    assert verification["parts_count"] == 2
    assert len(verification["issues"]) == 0


def test_mcp_tahoma2d_scene_tools_registered():
    from krita_mcp_lazy.server.app import create_mcp_server

    server = create_mcp_server()
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "krita_build_tahoma2d_scene" in tool_names
    assert "krita_verify_tahoma2d_roundtrip" in tool_names
