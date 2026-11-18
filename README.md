# krita-MCP-lazy (ToonFlow Art Engine)

> Professional AI Art Production Engine and Model Context Protocol (MCP) server for Krita.

## Overview
`krita-MCP-lazy` operates Krita as a professional digital art studio. It bridges AI orchestrators (ToonFlow) with Krita's native brush engine, non-destructive layer trees, color management, visual QA inspection loops, raster animation frames, and Tahoma2D handoff.

## Architecture
- **MCP Server (`src/krita_mcp_lazy/`)**: FastMCP server with typed tools, job queues, input validation, and wall-clock telemetry.
- **Krita Extension (`plugins/krita_mcp_bridge/`)**: Native Python extension running inside Krita, dispatching tasks thread-safely into Krita's main Qt event loop.
- **IPC Protocol**: Authenticated loopback transport (127.0.0.1) with cryptographically random session tokens and zero arbitrary eval.

## Project Tracking & Roadmap
- Master Plan: [docs/superpowers/plans/2026-11-18-krita-mcp-lazy.md](docs/superpowers/plans/2026-11-18-krita-mcp-lazy.md)
- Formal Spec: [docs/superpowers/specs/2026-11-18-krita-mcp-lazy-spec.md](docs/superpowers/specs/2026-11-18-krita-mcp-lazy-spec.md)
- Status & Cross-Session Tracker: [PROJECT_STATUS.md](PROJECT_STATUS.md)

## Quick Start for Developers & AI Agents
Read `PROJECT_STATUS.md` to see the current active phase and immediately resume the next pending task.
