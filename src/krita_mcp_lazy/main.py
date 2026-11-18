"""CLI entry point for launching the krita-MCP-lazy MCP server."""

import argparse
import logging
import sys
from typing import Optional

from krita_mcp_lazy.core.config import KritaConfig
from krita_mcp_lazy.server.app import create_mcp_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("krita-mcp-lazy")


def main(argv: Optional[list[str]] = None) -> None:
    """Parse command-line arguments and run the MCP server."""
    parser = argparse.ArgumentParser(
        prog="krita-mcp",
        description="krita-MCP-lazy (ToonFlow Art Engine) - Professional Krita MCP Server",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Loopback address for Krita IPC bridge (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=18812,
        help="TCP port for Krita IPC bridge (default: 18812)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Pre-shared authentication session token for Krita bridge",
    )
    parser.add_argument(
        "--transport",
        default="stdio",
        choices=["stdio", "sse"],
        help="MCP server transport mechanism (default: stdio)",
    )

    args = parser.parse_args(argv)
    
    config = KritaConfig(
        host=args.host,
        port=args.port,
        token=args.token,
    )
    
    logger.info("Initializing krita-MCP-lazy server...")
    server = create_mcp_server(config)
    logger.info("Starting MCP server over %s transport...", args.transport)
    server.run(transport=args.transport)


if __name__ == "__main__":
    main()
