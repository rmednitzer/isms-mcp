"""Tool registration. ``register_all`` wires every tool into a FastMCP app."""

from __future__ import annotations

from typing import TYPE_CHECKING

from isms_mcp.tools import calendar, coverage, evidence, overview, registers, risk, soa

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from isms_mcp.context import ServerContext


def register_all(mcp: FastMCP, ctx: ServerContext) -> None:
    """Register every tool against the given FastMCP app."""
    overview.register(mcp, ctx)
    soa.register(mcp, ctx)
    registers.register(mcp, ctx)
    risk.register(mcp, ctx)
    evidence.register(mcp, ctx)
    coverage.register(mcp, ctx)
    calendar.register(mcp, ctx)
