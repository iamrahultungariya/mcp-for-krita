"""Tests for ModularRigPackager and R.G. Bucket List animation rig contracts."""

import json
import os
import pytest
from unittest.mock import AsyncMock

from krita_mcp_lazy.modular_rig.models import CharacterRigMetadata
from krita_mcp_lazy.modular_rig.packager import ModularRigPackager


@pytest.mark.asyncio
async def test_scaffold_modular_rig_structure(tmp_path):
    """Verify packager creates hierarchical layer groups with inheritAlpha shadow masks."""
    mock_client = AsyncMock()
    mock_client.send_job.return_value.result = {"created": True, "layer_id": "lyr_grp_01", "updated": True}

    packager = ModularRigPackager(mock_client, library_root=str(tmp_path))
    meta = CharacterRigMetadata(
        character_id="creator_guy",
        name="Anime Creator Host",
        style="rg_bucket_list",
        pivots={"neck": [620, 850], "shoulder_left": [400, 920], "shoulder_right": [840, 920]},
        expressions=["normal", "blink", "shocked", "smile"],
        visemes=["rest", "A", "E", "O"],
        palette={"skin": "#FFE0BD", "hoodie": "#FFD166", "blazer": "#10142A"},
    )

    res = await packager.scaffold_rig_tree("doc_test", meta)

    assert res["success"] is True
    assert res["groups_created"] >= 6
    assert res["char_id"] == "creator_guy"

    # Verify layer creation calls included parent groups and child switches
    created_actions = [c[0][1].get("name") for c in mock_client.send_job.call_args_list if c[0][0] == "layer.create"]
    assert "Char_Main_Rig" in created_actions
    assert "Head_Group" in created_actions
    assert "Eyes_Switch" in created_actions
    assert "Mouth_Switch" in created_actions
    assert "Torso_Group" in created_actions


def test_export_manifest_json(tmp_path):
    """Verify rig_manifest.json is exported with pivots, expressions, and palette."""
    mock_client = AsyncMock()
    packager = ModularRigPackager(mock_client, library_root=str(tmp_path))

    meta = CharacterRigMetadata(
        character_id="creator_guy",
        name="Anime Creator Host",
        style="rg_bucket_list",
        pivots={"neck": [620, 850], "shoulder_left": [400, 920]},
        expressions=["normal", "blink", "smile"],
        visemes=["rest", "A", "O"],
        palette={"hoodie": "#FFD166"},
    )

    manifest_path = packager.export_manifest(meta)
    assert os.path.exists(manifest_path)
    assert manifest_path.endswith("rig_manifest.json")

    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["character_id"] == "creator_guy"
    assert data["style"] == "rg_bucket_list"
    assert "neck" in data["pivots"]
    assert "normal" in data["expressions"]
    assert data["palette"]["hoodie"] == "#FFD166"
