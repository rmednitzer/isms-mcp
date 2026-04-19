"""Tests for ServerContext classification filtering."""

from pathlib import Path

from isms_mcp.context import ServerContext
from isms_mcp.workspace import WorkspaceRoot


def _make_ctx(allow_restricted: bool) -> ServerContext:
    return ServerContext(
        workspace=WorkspaceRoot(root=Path("/"), allowed_prefixes=(Path("/"),)),
        transport_mode="stdio",
        allow_restricted=allow_restricted,
    )


class TestFilterClassification:
    def test_restricted_allowed(self) -> None:
        ctx = _make_ctx(allow_restricted=True)
        items = [
            {"id": "1", "classification": "restricted"},
            {"id": "2", "classification": "internal"},
        ]
        result = ctx.filter_classification(items)
        assert len(result) == 2

    def test_restricted_denied(self) -> None:
        ctx = _make_ctx(allow_restricted=False)
        items = [
            {"id": "1", "classification": "restricted"},
            {"id": "2", "classification": "internal"},
            {"id": "3", "classification": "public"},
        ]
        result = ctx.filter_classification(items)
        assert len(result) == 2
        assert all(item["classification"] != "restricted" for item in result)

    def test_custom_field_name(self) -> None:
        ctx = _make_ctx(allow_restricted=False)
        items = [
            {"id": "1", "sensitivity": "restricted"},
            {"id": "2", "sensitivity": "normal"},
        ]
        result = ctx.filter_classification(items, field="sensitivity")
        assert len(result) == 1
        assert result[0]["id"] == "2"

    def test_missing_field_kept(self) -> None:
        ctx = _make_ctx(allow_restricted=False)
        items = [
            {"id": "1"},  # no classification field
            {"id": "2", "classification": "public"},
        ]
        result = ctx.filter_classification(items)
        assert len(result) == 2

    def test_empty_list(self) -> None:
        ctx = _make_ctx(allow_restricted=False)
        assert ctx.filter_classification([]) == []
