"""Tests for CLI entrypoint helpers (bind safety, port/transport parsing)."""

from __future__ import annotations

import pytest

from isms_mcp.__main__ import _http_port, _is_loopback, _transport_mode


class TestIsLoopback:
    @pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost", "  LocalHost "])
    def test_loopback_hosts(self, host: str) -> None:
        assert _is_loopback(host) is True

    @pytest.mark.parametrize(
        "host",
        ["0.0.0.0", "::", "10.0.0.5", "192.168.1.2", "example.com", "", "   "],
    )
    def test_non_loopback_hosts(self, host: str) -> None:
        # "" / whitespace must NOT be loopback: many servers treat an empty
        # bind host as all-interfaces, so it must require the opt-in.
        assert _is_loopback(host) is False


class TestHttpPort:
    def test_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ISMS_MCP_HTTP_PORT", raising=False)
        assert _http_port() == 8765

    def test_explicit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ISMS_MCP_HTTP_PORT", "9001")
        assert _http_port() == 9001

    def test_invalid_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ISMS_MCP_HTTP_PORT", "not-a-port")
        with pytest.raises(SystemExit):
            _http_port()

    @pytest.mark.parametrize("bad", ["0", "-1", "99999", "65536"])
    def test_out_of_range_exits(self, monkeypatch: pytest.MonkeyPatch, bad: str) -> None:
        monkeypatch.setenv("ISMS_MCP_HTTP_PORT", bad)
        with pytest.raises(SystemExit):
            _http_port()


class TestTransportMode:
    def test_default_stdio(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("ISMS_MCP_TRANSPORT", raising=False)
        assert _transport_mode() == "stdio"

    def test_invalid_exits(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("ISMS_MCP_TRANSPORT", "carrier-pigeon")
        with pytest.raises(SystemExit):
            _transport_mode()
