"""Shared safe YAML loader."""

from __future__ import annotations

from io import StringIO
from typing import Any

from ruamel.yaml import YAML

_YAML = YAML(typ="safe")


def parse_yaml(text: str) -> Any:
    """Parse a YAML string with the safe loader. Returns None on empty input."""
    return _YAML.load(StringIO(text))
