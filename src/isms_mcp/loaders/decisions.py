"""Load DEC-* records from docs/decisions/.

Each DEC file is a markdown document with YAML front-matter. We extract the
front-matter and the body for substring search.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from isms_mcp.loaders._yaml import parse_yaml
from isms_mcp.workspace import WorkspaceRoot

DECISIONS_DIR = "docs/decisions"
FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def load_decisions(workspace: WorkspaceRoot) -> list[dict[str, Any]]:
    """Return ``[{\"frontmatter\": {...}, \"body\": str, \"path\": str}, ...]``."""
    if not workspace.exists(DECISIONS_DIR):
        return []
    out: list[dict[str, Any]] = []
    for path in workspace.safe_rglob(DECISIONS_DIR, "DEC-*.md"):
        try:
            text = open(path, "r", encoding="utf-8").read()
        except OSError:
            continue
        rel = str(Path(path).relative_to(workspace.root)) if Path(path).is_absolute() else str(path)
        match = FRONTMATTER_RE.match(text)
        if match is None:
            out.append({"frontmatter": {}, "body": text, "path": rel})
            continue
        fm_raw, body = match.group(1), match.group(2)
        fm = parse_yaml(fm_raw) or {}
        if not isinstance(fm, dict):
            fm = {}
        out.append({"frontmatter": fm, "body": body, "path": rel})
    return out
