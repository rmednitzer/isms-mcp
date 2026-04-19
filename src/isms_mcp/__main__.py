"""CLI entry point for ``isms-mcp``.

Reads configuration from environment variables and starts the MCP server in
the configured transport mode (stdio or HTTP).
"""

from __future__ import annotations

import os
import sys

from mcp.server.fastmcp import FastMCP

from isms_mcp.context import ServerContext, TransportMode
from isms_mcp.tools import register_all
from isms_mcp.workspace import WorkspaceRoot


def _transport_mode() -> TransportMode:
    raw = os.environ.get("ISMS_MCP_TRANSPORT", "stdio").lower()
    if raw in ("stdio", "http"):
        return raw  # type: ignore[return-value]
    print(
        f"isms-mcp: invalid ISMS_MCP_TRANSPORT={raw!r}; expected 'stdio' or 'http'",
        file=sys.stderr,
    )
    sys.exit(1)


def main() -> None:
    """Start the isms-mcp server."""
    transport = _transport_mode()

    workspace = WorkspaceRoot.from_env()

    # Restricted entries default to allowed on stdio, denied on HTTP.
    allow_restricted_env = os.environ.get("ISMS_MCP_ALLOW_RESTRICTED")
    if allow_restricted_env is not None:
        allow_restricted = allow_restricted_env.lower() in ("true", "1", "yes")
    else:
        allow_restricted = transport == "stdio"

    ctx = ServerContext(
        workspace=workspace,
        transport_mode=transport,
        allow_restricted=allow_restricted,
    )

    if transport == "http":
        token = os.environ.get("ISMS_MCP_HTTP_TOKEN")
        if not token:
            print("isms-mcp: ISMS_MCP_HTTP_TOKEN is required for HTTP transport", file=sys.stderr)
            sys.exit(1)
        host = os.environ.get("ISMS_MCP_HTTP_HOST", "127.0.0.1")
        port = int(os.environ.get("ISMS_MCP_HTTP_PORT", "8765"))
        allow_any = os.environ.get("ISMS_MCP_HTTP_ALLOW_ANY")
        if host == "0.0.0.0" and allow_any != "yes-i-understand-the-risk":  # noqa: S104
            print(
                "isms-mcp: binding 0.0.0.0 requires "
                "ISMS_MCP_HTTP_ALLOW_ANY=yes-i-understand-the-risk",
                file=sys.stderr,
            )
            sys.exit(1)

        mcp = FastMCP("isms-mcp", host=host, port=port)
        register_all(mcp, ctx)
        mcp.run(transport="sse")
    else:
        mcp = FastMCP("isms-mcp")
        register_all(mcp, ctx)
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
