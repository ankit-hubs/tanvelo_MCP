"""
Tanvelo MCP Server CLI Runner
Runs the MCP server over standard I/O (default for Cursor / Claude Code / Codex CLI / Windsurf) or SSE.
"""

import argparse
import asyncio
import os
import sys
from app.mcp.server import mcp_server


def main():
    parser = argparse.ArgumentParser(description="Tanvelo Enterprise MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable_http"],
        default="stdio",
        help="MCP transport protocol (default: stdio)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host for SSE/HTTP transport (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("MCP_PORT", 8001)),
        help="Port for SSE/HTTP transport (default: 8001)"
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="Tanvelo API Key (tv_live_...)"
    )
    args = parser.parse_args()

    if args.api_key:
        os.environ["TANVELO_API_KEY"] = args.api_key

    if args.transport == "stdio":
        asyncio.run(mcp_server.run_stdio_async())
    elif args.transport == "sse":
        print(f"Tanvelo MCP SSE Server listening on http://{args.host}:{args.port}/sse")
        asyncio.run(mcp_server.run_sse_async(host=args.host, port=args.port))
    elif args.transport == "streamable_http":
        print(f"Tanvelo MCP Streamable HTTP Server listening on http://{args.host}:{args.port}")
        asyncio.run(mcp_server.run_streamable_http_async())


if __name__ == "__main__":
    main()
