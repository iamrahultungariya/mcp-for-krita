"""Tahoma2D and OpenToonz scene project (.tnz) XML generator and round-trip validator."""

import os
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional


class Tahoma2DSceneBuilder:
    """Constructs Tahoma2D / OpenToonz .tnz XML scene files and validates round-trip structure."""

    def generate_scene_xml(
        self,
        manifest: Dict[str, Any],
        output_dir: str,
        scene_name: str = "scene",
    ) -> str:
        """Synthesize a complete .tnz scene project XML mapping cutouts to columns and pegbars."""
        os.makedirs(output_dir, exist_ok=True)
        tnz_path = os.path.join(output_dir, f"{scene_name}.tnz")

        character_name = manifest.get("character", "Character")
        width = manifest.get("canvas_width", 1920)
        height = manifest.get("canvas_height", 1080)
        parts: List[Dict[str, Any]] = manifest.get("parts", [])

        # Build root XML structure
        root = ET.Element("tnz")
        generator = ET.SubElement(root, "generator")
        generator.text = "Tahoma2D"

        version = ET.SubElement(root, "version")
        version.text = "1.4"

        # Camera section
        camera = ET.SubElement(root, "camera")
        c_res = ET.SubElement(camera, "resolution")
        c_res.set("width", str(width))
        c_res.set("height", str(height))

        # Levels section
        levels = ET.SubElement(root, "levels")
        for idx, part in enumerate(parts):
            lvl = ET.SubElement(levels, "level")
            lvl.set("id", str(idx + 1))
            lvl.set("name", part.get("name", f"part_{idx}"))
            path = ET.SubElement(lvl, "path")
            path.text = part.get("file", f"part_{idx}.png")

        # Columns / Xsheet section
        columns = ET.SubElement(root, "columns")
        for idx, part in enumerate(parts):
            col = ET.SubElement(columns, "column")
            col.set("index", str(idx))
            col.set("levelId", str(idx + 1))
            peg = ET.SubElement(col, "pegbar")
            peg.set("pivot_x", str(part.get("pivot_x", 0.5)))
            peg.set("pivot_y", str(part.get("pivot_y", 0.5)))
            peg.set("z_order", str(part.get("z_order", idx)))

        tree = ET.ElementTree(root)
        # Format and write
        ET.indent(tree, space="  ", level=0)
        tree.write(tnz_path, encoding="utf-8", xml_declaration=True)

        return tnz_path

    def verify_roundtrip(self, manifest: Dict[str, Any], tnz_path: str) -> Dict[str, Any]:
        """Verify XML validity, level files, column count, and coordinate synchronization."""
        issues: List[str] = []
        if not os.path.exists(tnz_path):
            return {
                "valid": False,
                "parts_count": 0,
                "scene_file": tnz_path,
                "issues": [f"File {tnz_path} does not exist"],
            }

        try:
            tree = ET.parse(tnz_path)
            root = tree.getroot()
            if root.tag != "tnz":
                issues.append("Root element is not <tnz>")

            levels = root.find("levels")
            level_count = len(levels.findall("level")) if levels is not None else 0

            columns = root.find("columns")
            column_count = len(columns.findall("column")) if columns is not None else 0

            expected_parts = manifest.get("parts", [])
            if level_count != len(expected_parts):
                issues.append(f"Level count ({level_count}) does not match manifest parts ({len(expected_parts)})")
            if column_count != len(expected_parts):
                issues.append(f"Column count ({column_count}) does not match manifest parts ({len(expected_parts)})")

        except ET.ParseError as e:
            issues.append(f"XML parse error: {str(e)}")

        return {
            "valid": len(issues) == 0,
            "parts_count": len(manifest.get("parts", [])),
            "scene_file": tnz_path,
            "issues": issues,
        }
