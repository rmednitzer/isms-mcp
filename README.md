# isms-mcp

Read-only Model Context Protocol (MCP) overlay for the
[ISMS](https://github.com/rmednitzer/isms) workspace.

The overlay wraps the ISMS validators and YAML loaders so that AI clients
(Claude Code, Claude Desktop) can query the workspace by concept (control
identifier, register entry, regulatory milestone) rather than by file path.
It is independent of, and not required by, the ISMS itself; per DEC-2026-008
of the ISMS repository, the overlay is non-normative for evidence
reproducibility.

## Hard constraints

- **Out of tree.** The overlay lives in this separate repository and is never
  imported from the ISMS repository.
- **Read only.** No tool writes to the filesystem, invokes `git`, runs `make`,
  or mutates any state.
- **Workspace-scoped filesystem access.** The server receives one workspace
  root via `ISMS_MCP_WORKSPACE`, canonicalises it with
  `Path.resolve(strict=True)`, and rejects every path outside the four
  allow-listed subtrees (`docs`, `template`, `instance`, `framework-refs`).
- **No `0.0.0.0` bind without auth.** stdio transport is the default; HTTP is
  optional and requires a bearer token.
- **No dependency on `mcp-remote`.**

See [docs/security.md](docs/security.md) for the CVE-informed defences.

## Installation

```bash
uv tool install isms-mcp
```

or for ad-hoc execution:

```bash
uvx isms-mcp
```

## Usage with Claude Desktop

```json
{
  "mcpServers": {
    "isms": {
      "command": "uvx",
      "args": ["isms-mcp"],
      "env": {
        "ISMS_MCP_WORKSPACE": "/absolute/path/to/isms"
      }
    }
  }
}
```

See [docs/claude-desktop.md](docs/claude-desktop.md) for the full registration
guide.

## Tools

| Tool | Purpose |
|---|---|
| `isms_info` | One-shot orientation: entity, jurisdiction, classification, workspace state. |
| `soa_query` | Query the Statement of Applicability with filters. |
| `control_status` | Drill into one control across SoA, implementation, evidence, crosswalk. |
| `register_query` | Unified query across assets, facilities, networks, suppliers, data. |
| `risk_query` | Query the risk register. |
| `evidence_age` | Evidence task ages, staleness against cadence, never-collected list. |
| `control_coverage` | SoA-wide coverage report (implementation, evidence, recency). |
| `regulatory_calendar` | Upcoming milestones with obligations and readiness artefacts. |

## Configuration

All configuration via environment variables. No config file.

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `ISMS_MCP_WORKSPACE` | yes | none | Absolute path to ISMS repo root. |
| `ISMS_MCP_TRANSPORT` | no | `stdio` | One of `stdio`, `http`. |
| `ISMS_MCP_HTTP_HOST` | no | `127.0.0.1` | Bind host for HTTP transport. |
| `ISMS_MCP_HTTP_PORT` | no | `8765` | Bind port. |
| `ISMS_MCP_HTTP_TOKEN` | conditional | none | Required when `ISMS_MCP_TRANSPORT=http`. |
| `ISMS_MCP_HTTP_ALLOW_ANY` | no | unset | Set to `yes-i-understand-the-risk` to bind `0.0.0.0`. |
| `ISMS_MCP_ALLOW_RESTRICTED` | no | `true` (stdio) / `false` (HTTP) | Surface `classification: restricted` entries. |

## Development

```bash
uv sync --extra dev --extra http
uv run pytest -v
uv run ruff check
uv run mypy src/
```

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
