# krita-MCP-lazy (ToonFlow Art Engine)

> Professional AI Art Production Engine and Model Context Protocol (MCP) server for Krita.

## Overview
`krita-MCP-lazy` operates Krita as a professional digital art studio. It bridges AI orchestrators (ToonFlow) with Krita's native brush engine, non-destructive layer trees, color management, visual QA inspection loops, raster animation frames, and Tahoma2D handoff.

---

## 🚀 Quick Setup & Usage

### 1. Krita Plugin Activation
The plugin has already been linked to your Krita configuration directory (`%APPDATA%\krita\pykrita\krita_mcp_bridge`).
1. Launch **Krita**.
2. Open **Settings > Configure Krita... > Python Plugin Manager**.
3. Locate **Krita MCP Bridge** and ensure the checkbox is **Enabled** (checked).
4. Restart Krita (or apply settings).
5. Open the docker via **Settings > Dockers > Krita MCP Bridge** (it shows the bridge status and loopback port `18812`).

---

### 2. MCP Client Configuration

The CLI tool `krita-mcp` is installed globally in your Python environment.

#### For Claude Desktop (`claude_desktop_config.json`):
```json
{
  "mcpServers": {
    "krita": {
      "command": "krita-mcp",
      "args": []
    }
  }
}
```

#### For Cursor / VS Code / Other Clients:
```json
{
  "mcpServers": {
    "krita": {
      "command": "python",
      "args": ["-m", "krita_mcp_lazy.main"]
    }
  }
}
```

---

## 🛠 Features & Registered Tools (55 Production Tools)

- **Document & Canvas Intelligence**: `krita_create_document`, `krita_resize_canvas`, `krita_crop_canvas`, `krita_rotate_canvas`, `krita_sample_pixel`
- **Non-Destructive Layer Trees**: `krita_create_layer`, `krita_delete_layer`, `krita_reorder_layer`, `krita_inspect_layer_tree`, `krita_set_layer_properties`
- **Masking & Alpha**: `krita_add_mask`, `krita_remove_mask`, `krita_set_alpha_inheritance`, `krita_list_masks`
- **Semantic Organization**: `krita_scaffold_semantic_structure` (Character, Background, UI, Props)
- **Brush & Stroke Engine**: `krita_list_brush_presets`, `krita_select_brush_preset`, `krita_configure_brush`, `krita_paint_stroke`, `krita_paint_bezier_curve`
- **Art Direction & Grids**: `krita_generate_production_spec`, `krita_calculate_composition_grid`, `krita_create_perspective_grid`, `krita_setup_environment_depth_planes`
- **Character & Expressions**: `krita_create_character_turnaround`, `krita_verify_character_consistency`, `krita_create_expression_sheet`, `krita_generate_viseme_set`
- **Props & Materials**: `krita_create_prop_asset`, `krita_apply_material_shading`
- **Visual QA & Scorecard**: `krita_capture_preview`, `krita_extract_region`, `krita_evaluate_visual_quality`, `krita_create_checkpoint`, `krita_rollback_checkpoint`
- **Animation & Sequence Exporter**: `krita_create_keyframe`, `krita_configure_onion_skin`, `krita_set_frame_timing`, `krita_export_frame_sequence`, `krita_validate_frame_sequence`
- **Tahoma2D Pipeline Interop**: `krita_package_tahoma2d_assets`, `krita_build_tahoma2d_scene`, `krita_verify_tahoma2d_roundtrip`
- **Telemetry & Diagnostics**: `krita_get_version`, `krita_health_check`, `krita_get_telemetry_report`, `krita_reset_telemetry`

---

## 🧪 Testing & Verification
All 113 unit and dogfooding benchmark tests pass with 100% coverage across headless environments:
```bash
pytest -v
```
