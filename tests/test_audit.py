"""Tests for audit logging."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from isms_mcp.audit import _hash_input, _log_dir, record


class TestHashInput:
    def test_deterministic(self) -> None:
        h1 = _hash_input({"a": 1, "b": 2})
        h2 = _hash_input({"b": 2, "a": 1})
        assert h1 == h2

    def test_returns_16_hex_chars(self) -> None:
        result = _hash_input("test")
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)

    def test_different_inputs_differ(self) -> None:
        assert _hash_input("alpha") != _hash_input("beta")


class TestLogDir:
    def test_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("XDG_STATE_HOME", raising=False)
        result = _log_dir()
        assert result.name == "isms-mcp"
        assert "state" in str(result)

    def test_xdg_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("XDG_STATE_HOME", "/tmp/xdg-state")
        result = _log_dir()
        assert result == Path("/tmp/xdg-state/isms-mcp")


class TestRecord:
    def test_writes_json_line(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("isms_mcp.audit._log_dir", return_value=Path(tmpdir)):
                record(
                    tool="isms_info",
                    workspace="/ws",
                    transport="stdio",
                    payload={"key": "value"},
                    result_length=42,
                )
            log_file = Path(tmpdir) / "audit.log"
            assert log_file.exists()
            line = log_file.read_text().strip()
            entry = json.loads(line)
            assert entry["tool"] == "isms_info"
            assert entry["workspace"] == "/ws"
            assert entry["transport"] == "stdio"
            assert entry["result_length"] == 42
            assert "ts" in entry
            assert "input_hash" in entry

    def test_appends_multiple_entries(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("isms_mcp.audit._log_dir", return_value=Path(tmpdir)):
                record(tool="a", workspace="/", transport="stdio", payload={}, result_length=1)
                record(tool="b", workspace="/", transport="http", payload={}, result_length=2)
            log_file = Path(tmpdir) / "audit.log"
            lines = log_file.read_text().strip().split("\n")
            assert len(lines) == 2
            assert json.loads(lines[0])["tool"] == "a"
            assert json.loads(lines[1])["tool"] == "b"

    def test_silent_on_error(self) -> None:
        with patch("isms_mcp.audit._log_dir", return_value=Path("/nonexistent/readonly")):
            # Audit logging is best effort; should not raise
            record(tool="x", workspace="/", transport="stdio", payload={}, result_length=0)
