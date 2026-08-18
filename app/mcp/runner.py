"""
Tanvelo MCP Server CLI Runner
Runs the MCP server over standard I/O (default for Cursor / Claude Code / Codex CLI) or SSE.
"""

import argparse
import asyncio
import sys
from app.mcp.server import mcp_server


def main():
    parser = argparse.ArgumentParser(description="Tanvelo MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable_http"],
        default="stdio",
        help="MCP transport protocol (default: stdio)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8001,
        help="Port for SSE/HTTP transport (default: 8001)"
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        asyncio.run(mcp_server.run_stdio_async())
    elif args.transport == "sse":
        asyncio.run(mcp_server.run_sse_async())
    elif args.transport == "streamable_http":
        asyncio.run(mcp_server.run_streamable_http_async())


if __name__ == "__main__":
    main()
