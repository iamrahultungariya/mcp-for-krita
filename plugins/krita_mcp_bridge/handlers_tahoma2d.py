"""Krita native API handlers for Tahoma2D multi-layer asset export and manifests."""

import json
import logging
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def register_tahoma2d_handlers(dispatcher: Any) -> None:
    """Register Tahoma2D cutout packaging handlers with the dispatcher."""

    def handle_package_cutout(params: dict) -> dict:
        doc_id = params.get("doc_id")
        char_group_name = params.get("character_group", "Character")
        output_dir = params.get("output_dir", "")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = None
                for d in app.documents():
                    if getattr(d, "_lazy_id", None) == doc_id or d.fileName() == doc_id:
                        doc = d
                        break
                if not doc:
                    doc = app.activeDocument()

                if doc:
                    root = doc.rootNode()
                    char_node = doc.nodeByName(char_group_name)
                    if not char_node:
                        # Search tree
                        def _find(n):
                            if n.name() == char_group_name or getattr(n, "_lazy_id", None) == char_group_name:
                                return n
                            for c in n.childNodes():
                                found = _find(c)
                                if found:
                                    return found
                            return None
                        char_node = _find(root)

                    parts: List[Dict[str, Any]] = []
                    if char_node and output_dir:
                        os.makedirs(output_dir, exist_ok=True)
                        children = char_node.childNodes()
                        for idx, child in enumerate(children):
                            p_name = child.name()
                            filename = f"{p_name}.png"
                            out_path = os.path.join(output_dir, filename)
                            # Export child node if possible
                            if hasattr(child, "save"):
                                child.save(out_path, doc.xRes(), doc.yRes())
                            parts.append({
                                "name": p_name,
                                "file": filename,
                                "pivot_x": 0.5,
                                "pivot_y": 0.5,
                                "z_order": idx,
                            })

                        manifest_data = {
                            "character": char_group_name,
                            "parts": parts,
                            "canvas_width": doc.width(),
                            "canvas_height": doc.height(),
                        }
                        # Write manifest file
                        m_file = os.path.join(output_dir, "manifest.json")
                        with open(m_file, "w", encoding="utf-8") as f:
                            json.dump(manifest_data, f, indent=2)

                        return {
                            "manifest": manifest_data,
                            "output_directory": output_dir,
                            "manifest_file": m_file,
                            "doc_id": doc_id,
                        }
        except ImportError:
            pass

        # Headless mock mode
        mock_parts = [
            {"name": "Head", "file": "Head.png", "pivot_x": 0.5, "pivot_y": 0.9, "z_order": 5},
            {"name": "Torso", "file": "Torso.png", "pivot_x": 0.5, "pivot_y": 0.5, "z_order": 4},
        ]
        manifest_data = {
            "character": "Hero",
            "parts": mock_parts,
            "canvas_width": 1920,
            "canvas_height": 1080,
        }
        return {
            "manifest": manifest_data,
            "output_directory": output_dir,
            "doc_id": doc_id,
        }

    dispatcher.register_handler("tahoma2d.package_cutout", handle_package_cutout)
