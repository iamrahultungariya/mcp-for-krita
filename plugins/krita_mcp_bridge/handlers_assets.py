"""Krita native API handlers for prop assets and material shading layers."""

import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def register_asset_handlers(dispatcher: Any) -> None:
    """Register prop asset and material shading handlers with the dispatcher."""

    def handle_create_prop(params: dict) -> dict:
        doc_id = params.get("doc_id")
        prop_name = params.get("prop_name", "Prop")
        material = params.get("material", "wood")
        category = params.get("category", "General")
        bounding_box = params.get("bounding_box")
        shading_layers: List[str] = params.get("shading_layers", [])
        layers_created: List[str] = params.get("layers_created", [f"{prop_name}_Lines"] + shading_layers)

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
                    prop_grp = doc.createGroupLayer(f"{prop_name}_Asset")
                    root.addChildNode(prop_grp, None)

                    # Create line art
                    line_node = doc.createNode(f"{prop_name}_Lines", "paintLayer")
                    prop_grp.addChildNode(line_node, None)

                    # Create material layers
                    for sl in shading_layers:
                        node = doc.createNode(sl, "paintLayer")
                        prop_grp.addChildNode(node, None)

                    doc.refreshProjection()
                    return {
                        "prop_name": prop_name,
                        "prop_group_id": f"{prop_name}_Asset",
                        "material": material,
                        "layers_created": layers_created,
                        "doc_id": doc_id,
                    }
        except ImportError:
            pass

        # Headless mock mode
        return {
            "prop_name": prop_name,
            "prop_group_id": f"{prop_name}_Asset",
            "material": material,
            "layers_created": layers_created,
            "doc_id": doc_id,
        }

    def handle_setup_material(params: dict) -> dict:
        doc_id = params.get("doc_id")
        prop_group_id = params.get("prop_group_id", "grp_prop")
        material = params.get("material", "wood")
        shading_layers: List[str] = params.get("shading_layers", [])

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
                    target_group = doc.nodeByName(prop_group_id)
                    if not target_group:
                        # Search root
                        def _find(n):
                            if n.name() == prop_group_id or getattr(n, "_lazy_id", None) == prop_group_id:
                                return n
                            for c in n.childNodes():
                                found = _find(c)
                                if found:
                                    return found
                            return None
                        target_group = _find(doc.rootNode())

                    if target_group:
                        for sl in shading_layers:
                            node = doc.createNode(sl, "paintLayer")
                            target_group.addChildNode(node, None)
                        doc.refreshProjection()
                        return {
                            "material": material,
                            "prop_group_id": prop_group_id,
                            "shading_layers": shading_layers,
                            "doc_id": doc_id,
                        }
        except ImportError:
            pass

        # Headless mock mode
        return {
            "material": material,
            "prop_group_id": prop_group_id,
            "shading_layers": shading_layers,
            "doc_id": doc_id,
        }

    dispatcher.register_handler("assets.create_prop", handle_create_prop)
    dispatcher.register_handler("assets.setup_material", handle_setup_material)
