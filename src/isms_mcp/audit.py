"""Audit logging for tool invocations.

Writes JSON-lines to ``$XDG_STATE_HOME/isms-mcp/audit.log`` (or
``~/.local/state/isms-mcp/audit.log`` if XDG_STATE_HOME is unset). Logs only
structural metadata: timestamp, tool name, input hash, workspace path,
transport, result length. Never logs the contents of restricted records.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _log_dir() -> Path:
    base = os.environ.get("XDG_STATE_HOME") or os.path.expanduser("~/.local/state")
    return Path(base) / "isms-mcp"


def _hash_input(payload: Any) -> str:
    serialised = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(serialised).hexdigest()[:16]


def record(
    *,
    tool: str,
    workspace: str,
    transport: str,
    payload: Any,
    result_length: int,
) -> None:
    """Append a single audit-log line. Best effort: failures do not raise."""
    try:
        directory = _log_dir()
        directory.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(UTC).isoformat(),
            "tool": tool,
            "workspace": workspace,
            "transport": transport,
            "input_hash": _hash_input(payload),
            "result_length": int(result_length),
        }
        with open(directory / "audit.log", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError:
        # Audit logging is best effort; never break a tool over it.
        return
