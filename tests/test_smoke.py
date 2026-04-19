from pathlib import Path

from isms_mcp.context import ServerContext
from isms_mcp.tools import register_all
from isms_mcp.workspace import WorkspaceRoot


class DummyMcp:
    def __init__(self) -> None:
        self.tool_names: list[str] = []

    def tool(self):
        def decorator(fn):
            self.tool_names.append(fn.__name__)
            return fn

        return decorator


def test_register_all_registers_expected_tools() -> None:
    mcp = DummyMcp()
    ctx = ServerContext(
        workspace=WorkspaceRoot(root=Path("/"), allowed_prefixes=(Path("/"),)),
        transport_mode="stdio",
        allow_restricted=True,
    )
    register_all(mcp, ctx)
    assert set(mcp.tool_names) == {
        "isms_info",
        "soa_query",
        "control_status",
        "register_query",
        "risk_query",
        "evidence_age",
        "control_coverage",
        "regulatory_calendar",
    }
