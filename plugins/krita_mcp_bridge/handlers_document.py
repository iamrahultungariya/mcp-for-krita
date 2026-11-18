"""Krita native API handlers for document operations executed on the main GUI thread."""

import logging
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# In-memory document registry for headless/mock environments
_mock_documents: Dict[str, dict] = {}


def register_document_handlers(dispatcher: Any) -> None:
    """Register all document-related handlers with the main-thread dispatcher."""

    def handle_create_document(params: dict) -> dict:
        width = params.get("width", 1920)
        height = params.get("height", 1080)
        name = params.get("name", "Artwork")
        resolution_dpi = params.get("resolution_dpi", 300.0)
        color_model = params.get("color_model", "RGBA")
        bit_depth = params.get("bit_depth", "U8")
        color_profile = params.get("color_profile", "sRGB-elle-V2-srgbtrc.icc")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                # Map color model & bit depth to Krita channel strings
                # e.g., "RGBA", "U8" -> "RGBA", "U8"
                doc = app.createDocument(
                    width,
                    height,
                    name,
                    color_model.lower(),
                    bit_depth.lower(),
                    color_profile,
                    resolution_dpi,
                )
                if not doc:
                    raise RuntimeError("Krita app.createDocument returned None")
                active_win = app.activeWindow()
                if active_win:
                    active_win.addView(doc)
                doc_id = str(uuid.uuid4())[:8]
                return {
                    "doc_id": doc_id,
                    "name": doc.name(),
                    "width": doc.width(),
                    "height": doc.height(),
                    "resolution_dpi": doc.resolution(),
                    "color_model": doc.colorModel(),
                    "bit_depth": doc.colorDepth(),
                    "color_profile": doc.colorProfile(),
                    "modified": doc.modified(),
                }
        except ImportError:
            pass

        # Headless mock mode
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        doc_info = {
            "doc_id": doc_id,
            "name": name,
            "width": width,
            "height": height,
            "resolution_dpi": resolution_dpi,
            "color_model": color_model,
            "bit_depth": bit_depth,
            "color_profile": color_profile,
            "modified": False,
            "file_path": None,
            "layer_count": 1,
        }
        _mock_documents[doc_id] = doc_info
        return doc_info

    def handle_open_document(params: dict) -> dict:
        file_path = params.get("file_path")
        if not file_path:
            raise ValueError("Parameter 'file_path' is required")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.openDocument(file_path)
                if not doc:
                    raise RuntimeError(f"Krita failed to open document at '{file_path}'")
                active_win = app.activeWindow()
                if active_win:
                    active_win.addView(doc)
                doc_id = str(uuid.uuid4())[:8]
                return {
                    "doc_id": doc_id,
                    "name": doc.name(),
                    "width": doc.width(),
                    "height": doc.height(),
                    "file_path": file_path,
                }
        except ImportError:
            pass

        # Headless mock mode
        doc_id = f"doc_{uuid.uuid4().hex[:8]}"
        doc_info = {
            "doc_id": doc_id,
            "name": file_path.split("/")[-1].split("\\")[-1],
            "width": 1920,
            "height": 1080,
            "resolution_dpi": 300.0,
            "color_model": "RGBA",
            "bit_depth": "U8",
            "color_profile": "sRGB-elle-V2-srgbtrc.icc",
            "file_path": file_path,
            "modified": False,
            "layer_count": 1,
        }
        _mock_documents[doc_id] = doc_info
        return doc_info

    def handle_save_document(params: dict) -> dict:
        doc_id = params.get("doc_id")
        file_path = params.get("file_path")
        export_format = params.get("export_format", "kra")

        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.activeDocument()
                if doc:
                    if file_path:
                        success = doc.saveAs(file_path)
                    else:
                        success = doc.save()
                    return {"doc_id": doc_id or "active", "saved": success, "file_path": doc.fileName()}
        except ImportError:
            pass

        # Headless mock mode
        if doc_id and doc_id in _mock_documents:
            _mock_documents[doc_id]["saved"] = True
            if file_path:
                _mock_documents[doc_id]["file_path"] = file_path
        return {"doc_id": doc_id, "saved": True, "file_path": file_path, "export_format": export_format}

    def handle_close_document(params: dict) -> dict:
        doc_id = params.get("doc_id")
        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.activeDocument()
                if doc:
                    closed = doc.close()
                    return {"doc_id": doc_id or "active", "closed": closed}
        except ImportError:
            pass

        # Headless mock mode
        if doc_id in _mock_documents:
            del _mock_documents[doc_id]
        return {"doc_id": doc_id, "closed": True}

    def handle_inspect_document(params: dict) -> dict:
        doc_id = params.get("doc_id")
        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                doc = app.activeDocument()
                if doc:
                    return {
                        "doc_id": doc_id or "active",
                        "name": doc.name(),
                        "width": doc.width(),
                        "height": doc.height(),
                        "resolution_dpi": doc.resolution(),
                        "color_model": doc.colorModel(),
                        "bit_depth": doc.colorDepth(),
                        "color_profile": doc.colorProfile(),
                        "modified": doc.modified(),
                    }
        except ImportError:
            pass

        # Headless mock mode
        if doc_id and doc_id in _mock_documents:
            return _mock_documents[doc_id]
        if _mock_documents:
            return next(iter(_mock_documents.values()))
        return {
            "doc_id": doc_id or "none",
            "name": "Untitled",
            "width": 1920,
            "height": 1080,
            "resolution_dpi": 300.0,
            "color_model": "RGBA",
            "bit_depth": "U8",
            "color_profile": "sRGB",
            "modified": False,
        }

    def handle_list_documents(params: dict) -> dict:
        try:
            from krita import Krita
            app = Krita.instance()
            if app:
                docs = app.documents()
                doc_list = []
                for idx, d in enumerate(docs):
                    doc_list.append({
                        "doc_id": f"doc_{idx}",
                        "name": d.name(),
                        "width": d.width(),
                        "height": d.height(),
                        "modified": d.modified(),
                    })
                return {"documents": doc_list}
        except ImportError:
            pass

        # Headless mock mode
        return {"documents": list(_mock_documents.values())}

    dispatcher.register_handler("document.create", handle_create_document)
    dispatcher.register_handler("document.open", handle_open_document)
    dispatcher.register_handler("document.save", handle_save_document)
    dispatcher.register_handler("document.close", handle_close_document)
    dispatcher.register_handler("document.inspect", handle_inspect_document)
    dispatcher.register_handler("document.list", handle_list_documents)
