"""Modular character rig packager and manifest exporter for Krita."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from krita_mcp_lazy.modular_rig.models import CharacterRigMetadata

logger = logging.getLogger(__name__)


class ModularRigPackager:
    """Manages the creation, scaffolding, and serialization of modular animation rigs in Krita."""

    def __init__(self, client: Any, library_root: str = "asset_library/characters") -> None:
        self.client = client
        self.library_root = library_root

    async def scaffold_rig_tree(
        self,
        doc_id: str,
        metadata: CharacterRigMetadata,
    ) -> Dict[str, Any]:
        """Scaffold standard Studio Cel-Hybrid modular layer tree in Krita canvas."""
        logger.info(
            "Scaffolding modular rig '%s' (%s) into document %s...",
            metadata.name,
            metadata.character_id,
            doc_id,
        )

        groups_created = 0

        # Helper to create layer via IPC
        async def _create(
            name: str,
            layer_type: str = "paintLayer",
            parent: Optional[str] = None,
            blend: str = "normal",
            inherit_alpha: bool = False,
        ):
            nonlocal groups_created
            res = await self.client.send_job(
                "layer.create",
                {
                    "doc_id": doc_id,
                    "name": name,
                    "layer_type": layer_type,
                    "parent_group": parent,
                    "blending_mode": blend,
                },
            )
            if inherit_alpha:
                await self.client.send_job(
                    "layer.set_inherit_alpha",
                    {
                        "doc_id": doc_id,
                        "layer_name": name,
                        "inherit_alpha": True,
                    },
                )
            if "group" in layer_type.lower():
                groups_created += 1
            return res

        # 1. Main Character Root Group
        root_name = "Char_Main_Rig"
        await _create(root_name, layer_type="groupLayer")

        # 2. Head Group & Swappable Facial Expression Subgroups
        await _create("Head_Group", layer_type="groupLayer", parent=root_name)
        await _create("Eyes_Switch", layer_type="groupLayer", parent="Head_Group")
        for exp in metadata.expressions:
            await _create(f"Eyes_{exp}", layer_type="paintLayer", parent="Eyes_Switch")

        await _create("Mouth_Switch", layer_type="groupLayer", parent="Head_Group")
        for vis in metadata.visemes:
            await _create(f"Mouth_{vis}", layer_type="paintLayer", parent="Mouth_Switch")

        await _create("Hair_Front_Line", layer_type="paintLayer", parent="Head_Group")
        await _create("Face_Shade", layer_type="paintLayer", parent="Head_Group", blend="multiply", inherit_alpha=True)
        await _create("Face_Base", layer_type="paintLayer", parent="Head_Group")

        # 3. Torso Group
        await _create("Torso_Group", layer_type="groupLayer", parent=root_name)
        await _create("Torso_Lineart", layer_type="paintLayer", parent="Torso_Group")
        await _create("Torso_Shadow", layer_type="paintLayer", parent="Torso_Group", blend="multiply", inherit_alpha=True)
        await _create("Torso_Flats", layer_type="paintLayer", parent="Torso_Group")

        # 4. Limbs
        await _create("Arm_L_Group", layer_type="groupLayer", parent=root_name)
        await _create("Arm_R_Group", layer_type="groupLayer", parent=root_name)

        # 5. Props & Background Parallax
        await _create("Props_Layer", layer_type="groupLayer")
        await _create("BG_Parallax", layer_type="groupLayer")

        logger.info("Modular rig scaffolding complete: %d groups created.", groups_created)
        return {
            "success": True,
            "char_id": metadata.character_id,
            "groups_created": groups_created,
            "doc_id": doc_id,
        }

    def export_manifest(
        self,
        metadata: CharacterRigMetadata,
        output_dir: Optional[str] = None,
    ) -> str:
        """Serialize rig metadata to disk as rig_manifest.json."""
        char_dir = output_dir or os.path.join(self.library_root, metadata.character_id)
        os.makedirs(char_dir, exist_ok=True)
        manifest_path = os.path.join(char_dir, "rig_manifest.json")

        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        logger.info("Exported rig manifest to: %s", manifest_path)
        return manifest_path

    async def import_rig(
        self,
        doc_id: str,
        character_id: str,
        x: int = 0,
        y: int = 0,
        scale: float = 1.0,
    ) -> Dict[str, Any]:
        """Read saved rig manifest and scaffold rig into target document."""
        manifest_path = os.path.join(self.library_root, character_id, "rig_manifest.json")
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Rig manifest not found at: {manifest_path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = CharacterRigMetadata(**data)
        scaffold_res = await self.scaffold_rig_tree(doc_id, meta)
        scaffold_res["placement"] = {"x": x, "y": y, "scale": scale}
        return scaffold_res
