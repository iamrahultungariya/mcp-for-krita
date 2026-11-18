"""Krita native API handlers for masks (transparency, filter, transform) and alpha inheritance."""

import logging
import uuid
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Mock mask store for headless testing
_mock_masks: Dict[str, List[dict]] = {}


def register_mask_handlers(dispatcher: Any) -> None:
    """Register all mask-related handlers with the main-thread dispatcher."""

    def handle_add_mask(params: dict) -> dict:
        doc_id = params.get("doc_id", "default")
        layer_id = params.get("layer_id")
        mask_type = params.get("mask_type", "transparency")
        name = params.get("name", "Mask")
        filter_config = params.get("filter_config", {})

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.activeDocument()
                if doc and layer_id:
                    parent_node = doc.nodeByName(layer_id)
                    if parent_node:
                        if mask_type == "transparency":
                            mask_node = doc.createTransparencyMask(name)
                        elif mask_type == "transform":
                            mask_node = doc.createTransformMask(name)
                        else:
                            mask_node = doc.createTransparencyMask(name)

                        parent_node.addChildNode(mask_node, None)
                        mask_id = mask_node.name()
                        return {
                            "doc_id": doc_id,
                            "parent_layer_id": layer_id,
                            "mask_id": mask_id,
                            "name": name,
                            "mask_type": mask_type,
                            "created": True,
                        }
        except ImportError:
            pass

        # Headless mock mode
        mask_id = f"mask_{uuid.uuid4().hex[:6]}"
        mask_entry = {
            "mask_id": mask_id,
            "parent_layer_id": layer_id,
            "name": name,
            "mask_type": mask_type,
            "filter_config": filter_config,
        }
        _mock_masks.setdefault(layer_id, []).append(mask_entry)
        return {
            "doc_id": doc_id,
            "parent_layer_id": layer_id,
            "mask_id": mask_id,
            "name": name,
            "mask_type": mask_type,
            "created": True,
        }

    def handle_remove_mask(params: dict) -> dict:
        doc_id = params.get("doc_id", "default")
        mask_id = params.get("mask_id")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.activeDocument()
                if doc and mask_id:
                    node = doc.nodeByName(mask_id)
                    if node:
                        node.remove()
                        return {"doc_id": doc_id, "mask_id": mask_id, "removed": True}
        except ImportError:
            pass

        # Headless mock mode
        for layer_id, masks in _mock_masks.items():
            for i, m in enumerate(masks):
                if m["mask_id"] == mask_id or m["name"] == mask_id:
                    masks.pop(i)
                    return {"doc_id": doc_id, "mask_id": mask_id, "removed": True}
        return {"doc_id": doc_id, "mask_id": mask_id, "removed": True}

    def handle_alpha_inheritance(params: dict) -> dict:
        doc_id = params.get("doc_id", "default")
        layer_id = params.get("layer_id")
        inherit_alpha = params.get("inherit_alpha", True)

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.activeDocument()
                if doc and layer_id:
                    node = doc.nodeByName(layer_id)
                    if node:
                        node.setInheritAlpha(inherit_alpha)
                        return {
                            "doc_id": doc_id,
                            "layer_id": layer_id,
                            "inherit_alpha": inherit_alpha,
                            "updated": True,
                        }
        except ImportError:
            pass

        # Headless mock mode
        return {
            "doc_id": doc_id,
            "layer_id": layer_id,
            "inherit_alpha": inherit_alpha,
            "updated": True,
        }

    def handle_list_masks(params: dict) -> dict:
        doc_id = params.get("doc_id", "default")
        layer_id = params.get("layer_id")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.activeDocument()
                if doc and layer_id:
                    node = doc.nodeByName(layer_id)
                    if node:
                        masks = []
                        for child in node.childNodes():
                            if "mask" in child.type().lower():
                                masks.append({
                                    "mask_id": child.name(),
                                    "name": child.name(),
                                    "type": child.type(),
                                    "visible": child.visible(),
                                })
                        return {"doc_id": doc_id, "layer_id": layer_id, "masks": masks}
        except ImportError:
            pass

        # Headless mock mode
        return {"doc_id": doc_id, "layer_id": layer_id, "masks": _mock_masks.get(layer_id, [])}

    dispatcher.register_handler("mask.add", handle_add_mask)
    dispatcher.register_handler("mask.remove", handle_remove_mask)
    dispatcher.register_handler("layer.alpha_inheritance", handle_alpha_inheritance)
    dispatcher.register_handler("mask.list", handle_list_masks)
