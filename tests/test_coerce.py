"""Unit tests for defensive int coercion."""

from __future__ import annotations

from isms_mcp._coerce import coerce_int


class TestCoerceInt:
    def test_int_passthrough(self) -> None:
        assert coerce_int(90) == 90

    def test_numeric_string(self) -> None:
        assert coerce_int("90") == 90
        assert coerce_int("  90 ") == 90

    def test_float_truncates(self) -> None:
        assert coerce_int(90.7) == 90

    def test_junk_string_is_none(self) -> None:
        assert coerce_int("ninety") is None

    def test_bool_is_none(self) -> None:
        assert coerce_int(True) is None
        assert coerce_int(False) is None

    def test_list_is_none(self) -> None:
        assert coerce_int([90]) is None

    def test_none_is_none(self) -> None:
        assert coerce_int(None) is None
