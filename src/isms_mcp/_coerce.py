"""Defensive scalar coercion for tolerant YAML parsing.

Loaders do not schema-validate, so a junk ``cadence_days`` (e.g. the string
``"ninety"`` or a list) must degrade to "no cadence" rather than crash a tool
with an unhandled ``ValueError``/``TypeError``. This mirrors the project-wide
rule that malformed workspace data degrades gracefully.
"""

from __future__ import annotations

import math


def coerce_int(value: object) -> int | None:
    """Best-effort int. Returns None when ``value`` is not a sane integer.

    ``bool`` is rejected: YAML ``true`` is not a meaningful cadence/day count.
    Non-finite floats (YAML ``.nan`` / ``.inf``) degrade to None rather than
    raising ``ValueError``/``OverflowError`` out of ``int()``.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if math.isfinite(value) else None
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None
