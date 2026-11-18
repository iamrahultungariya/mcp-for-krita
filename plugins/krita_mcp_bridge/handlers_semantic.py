"""Krita native API handlers for scaffolding semantic layer trees recursively."""

import logging
import uuid
from typing import Any, Dict, List

from plugins.krita_mcp_bridge.handlers_layers import _get_doc_layers

logger = logging.getLogger(__name__)


def register_semantic_handlers(dispatcher: Any) -> None:
    """Register semantic scaffolding handlers with the main-thread dispatcher."""

    def handle_scaffold_semantic(params: dict) -> dict:
        doc_id = params.get("doc_id", "default")
        schema = params.get("schema", {})
        preset = params.get("preset")

        if not schema:
            raise ValueError("Schema dictionary is empty or not provided")

        created_groups = 0
        created_layers = 0

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.activeDocument()
                if doc:
                    def _build_tree(tree: Any, parent_node: Any) -> None:
                        nonlocal created_groups, created_layers
                        if isinstance(tree, dict):
                            for key, val in tree.items():
                                group = doc.createGroupLayer(key)
                                parent_node.addChildNode(group, None)
                                created_groups += 1
                                _build_tree(val, group)
                        elif isinstance(tree, list):
                            for item in tree:
                                if isinstance(item, str):
                                    layer = doc.createNode(item, "paintLayer")
                                    parent_node.addChildNode(layer, None)
                                    created_layers += 1
                                elif isinstance(item, dict):
                                    _build_tree(item, parent_node)

                    _build_tree(schema, doc.rootNode())
                    return {
                        "doc_id": doc_id,
                        "created_groups": created_groups,
                        "created_layers": created_layers,
                        "preset": preset,
                    }
        except ImportError:
            pass

        # Headless mock mode
        doc_layers = _get_doc_layers(doc_id)

        def _mock_build(tree: Any, target_list: List[dict]) -> None:
            nonlocal created_groups, created_layers
            if isinstance(tree, dict):
                for key, val in tree.items():
                    group_node = {
                        "id": f"grp_{uuid.uuid4().hex[:6]}",
                        "name": key,
                        "type": "group",
                        "opacity": 255,
                        "blending_mode": "normal",
                        "visible": True,
                        "locked": False,
                        "children": [],
                    }
                    target_list.append(group_node)
                    created_groups += 1
                    _mock_build(val, group_node["children"])
            elif isinstance(tree, list):
                for item in tree:
                    if isinstance(item, str):
                        layer_node = {
                            "id": f"lyr_{uuid.uuid4().hex[:6]}",
                            "name": item,
                            "type": "paint",
                            "opacity": 255,
                            "blending_mode": "normal",
                            "visible": True,
                            "locked": False,
                            "children": [],
                        }
                        target_list.append(layer_node)
                        created_layers += 1
                    elif isinstance(item, dict):
                        _mock_build(item, target_list)

        _mock_build(schema, doc_layers)
        return {
            "doc_id": doc_id,
            "created_groups": created_groups,
            "created_layers": created_layers,
            "preset": preset,
        }

    dispatcher.register_handler("layer.scaffold_semantic", handle_scaffold_semantic)
