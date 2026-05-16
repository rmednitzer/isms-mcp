# CLAUDE.md

Guidance for Claude Code (and other agents) working in this repository.

## What this is

`isms-mcp` is a **read-only** Model Context Protocol overlay over the
[ISMS](https://github.com/rmednitzer/isms) workspace. It exposes eight tools
that wrap YAML/JSON loaders so AI clients can query the workspace by concept
(control ID, register entry, regulatory milestone) rather than by file path.

The overlay is **out-of-tree**: it never imports from the ISMS repository, and
per `DEC-2026-008` of the ISMS repository it is non-normative for evidence
reproducibility.

## Hard constraints — do not violate

These are load-bearing security and architectural invariants. Any change that
relaxes one needs an explicit user decision.

1. **Read-only.** No tool, loader, or helper writes to the filesystem,
   shells out (`git`, `make`, subprocess), mutates env, or modifies state.
   The audit log under `$XDG_STATE_HOME/isms-mcp/` is the *only* permitted
   write, and it is best-effort and structural-metadata-only.
2. **Workspace allow-list.** Path discovery and one-shot text reads go
   through `WorkspaceRoot.safe_read_text` / `safe_iterdir` / `safe_rglob`.
   Paths are canonicalised with `Path.resolve(strict=True)` and rejected if
   they fall outside `docs`, `template`, `instance`, or `framework-refs`.
   Symlinks are followed, then the resolved target is re-checked. NUL bytes
   and absolute paths are rejected up front. Once `safe_rglob`/`safe_iterdir`
   has yielded a path, it has already been validated, so a bare `open(path)`
   on the yielded value is safe — `loaders/evidence.py` (JSON attestations)
   and `loaders/decisions.py` (DEC frontmatter) do exactly this. Don't
   construct workspace paths any other way.
3. **No non-loopback bind without auth.** stdio is the default transport. HTTP
   requires `ISMS_MCP_HTTP_TOKEN`. Binding any non-loopback host (`0.0.0.0`,
   `::`, or a specific routable IP; loopback set is `127.0.0.1`/`::1`/
   `localhost`) requires the literal opt-in
   `ISMS_MCP_HTTP_ALLOW_ANY=yes-i-understand-the-risk`.
4. **No `mcp-remote` dependency.**
5. **Classification filter on HTTP.** `classification: restricted` entries
   are dropped over HTTP unless `ISMS_MCP_ALLOW_RESTRICTED=true`. Apply
   `ServerContext.filter_classification` to any list output that may carry
   classified rows. `register_query` filters both `classification` and
   `classification_handled`; mirror that pattern when adding sources.

## Layout

```
src/isms_mcp/
  __main__.py        # CLI entry: env -> WorkspaceRoot -> ServerContext -> FastMCP
  __init__.py        # __version__, MCP_SPEC_REVISION
  workspace.py       # WorkspaceRoot — the security boundary
  context.py         # ServerContext (transport, allow_restricted, classification filter)
  exceptions.py      # IsmsMcpError, PathEscape, WorkspaceNotConfigured, ClassificationDenied
  models.py          # Pydantic v2 models for every tool input/output
  audit.py           # JSON-lines audit log (best-effort, structural metadata only)
  _pagination.py     # paginate(items, page, page_size) -> (slice, Pagination)
  loaders/           # YAML/JSON readers; instance/ preferred, template/ fallback
    _yaml.py         # ruamel.yaml safe loader — use this, never raw yaml
    soa.py registers.py risk.py calendar.py evidence.py
    controls.py sources.py decisions.py
  tools/             # One file per MCP tool, each defines register(mcp, ctx)
    overview.py      # isms_info
    soa.py           # soa_query, control_status (the only 2-tool file)
    registers.py     # register_query
    risk.py          # risk_query
    evidence.py      # evidence_age
    coverage.py      # control_coverage
    calendar.py      # regulatory_calendar
    __init__.py      # register_all(mcp, ctx)
tests/               # pytest, mirrors src/ layout
```

The full set of registered tool names is asserted in
`tests/test_smoke.py::test_register_all_registers_expected_tools` — keep it in
sync when you add or rename a tool.

## Architectural rules

- **Layering.** `__main__` → `tools/` → `loaders/` → `workspace`. Tools
  delegate file reads to loaders; loaders never know about MCP. The lone
  exception is `tools/overview.py`, which reads `instance/config.yaml`
  directly via `parse_yaml(workspace.safe_read_text(...))` because no
  loader exists for it — preserve that pattern (or extract a loader) but
  don't add new direct reads to other tools.
- **Loader fallback.** Every loader probes `instance/...` first, then
  `template/...`, returning `None`/`[]` if neither exists. Empty workspace is
  a normal v1 state — never raise on absence.
- **Tolerant parsing — partial.** Loaders narrow YAML output with
  `isinstance(data, dict)` so non-dict YAML degrades to an empty result.
  `loaders/evidence.py` and `loaders/decisions.py` additionally swallow
  `OSError` (and `JSONDecodeError` for evidence) on a per-file basis when
  scanning trees. **YAML parse errors are *not* caught**: `_yaml.parse_yaml`
  delegates straight to `ruamel.yaml`, so malformed `soa.yaml`,
  `evidence-plan.yaml`, etc. will raise out of the loader and surface as a
  tool error. If you need true tolerance for a new YAML loader, add explicit
  `try/except YAMLError` at the call site.
- **Pydantic for I/O.** Every tool input/output is a Pydantic model in
  `models.py`. FastMCP derives JSON Schemas from these and the agent receives
  structured output (MCP spec revision `2025-11-25`, see `__init__.py`).
- **Audit every tool.** Each tool calls `audit.record(...)` with the
  invocation payload (no PII or restricted contents — only structural
  metadata) and `len(result.model_dump_json())`. Failures don't propagate.
- **Pagination.** List-returning tools use `_pagination.paginate`. Default
  `page_size=50`, max `200` (enforced by Pydantic `Field`).

## Adding a new tool

1. Add input/output models to `src/isms_mcp/models.py`.
2. If a new data source is needed, add a loader under `src/isms_mcp/loaders/`
   following the instance/template fallback pattern and using
   `WorkspaceRoot` methods only.
3. Create `src/isms_mcp/tools/<name>.py` with a `register(mcp, ctx)` function
   that defines an inner `@mcp.tool()`-decorated callable.
4. Wire it in `src/isms_mcp/tools/__init__.py::register_all`.
5. Add the tool name to the assertion in `tests/test_smoke.py`.
6. Add tests under `tests/test_tools.py`.
7. Update the tool table in `README.md`.
8. Inside the tool: filter classification, paginate, audit, return the model.

## Conventions

- **Python 3.12+.** Use modern syntax: PEP 695 generics (`def f[T](...)`),
  `X | None`, `from __future__ import annotations` (already standard here),
  `dict[str, T]` not `Dict`.
- **Strict typing.** mypy runs in strict mode against `src/`. Don't introduce
  `Any` without reason; prefer narrow `Literal` types (see
  `RegisterName`, `ControlStatusName`, `RiskStatus`, etc.).
- **Defensive coercion.** When parsing YAML, validate the shape with
  `isinstance(...)` before indexing, then map to the Pydantic model.
  See `tools/soa.py::_to_soa_entry` for the canonical pattern.
- **Date handling.** `datetime.fromisoformat(value.replace("Z", "+00:00"))`
  for ISO-with-Z. Use `date.today()` and integer day deltas for ages.
- **Comments.** Project-wide preference: minimal. Only annotate non-obvious
  invariants (e.g. why `audit.record` swallows OSError). No "why I did this"
  history in code.
- **Imports.** Ruff's `I` is enforced. Don't hand-format imports.

## Development

```bash
uv sync --extra dev --extra http
uv run pytest -v
uv run ruff check
uv run ruff format --check
uv run mypy src/
```

CI runs all four against Python 3.12 and 3.13. All four must pass before a PR
is mergeable.

A handy one-liner for local pre-push:

```bash
uv run ruff check && uv run ruff format --check && uv run mypy src/ && uv run pytest -v
```

Run the server against a real workspace:

```bash
ISMS_MCP_WORKSPACE=/abs/path/to/isms uv run isms-mcp
```

## Configuration surface

All via environment variables; there is no config file.

| Var | Required | Default | Notes |
|---|---|---|---|
| `ISMS_MCP_WORKSPACE` | yes | — | Absolute path to ISMS repo root. |
| `ISMS_MCP_TRANSPORT` | no | `stdio` | `stdio` or `http`. |
| `ISMS_MCP_HTTP_HOST` | no | `127.0.0.1` | |
| `ISMS_MCP_HTTP_PORT` | no | `8765` | |
| `ISMS_MCP_HTTP_TOKEN` | iff `http` | — | Bearer token. |
| `ISMS_MCP_HTTP_ALLOW_ANY` | no | unset | Set to `yes-i-understand-the-risk` to bind `0.0.0.0`. |
| `ISMS_MCP_ALLOW_RESTRICTED` | no | `true` on stdio, `false` on http | |
| `XDG_STATE_HOME` | no | `~/.local/state` | Audit log lives at `<XDG_STATE_HOME>/isms-mcp/audit.log`. |

## Things that look like footguns and aren't

- **Empty workspaces are valid.** Loaders return `[]` / `None`; tools return
  empty results. Don't add "missing data" errors.
- **Theme/status fields can be junk.** Coerce to known `Literal` values or
  to a safe default; don't propagate raw strings up.
- **`_RATING_ORDER` lookup with `-1`.** In `tools/risk.py`, unknown ratings
  sort below `low`, so `min_residual` filters them out. Intentional.
- **`__path` injection on attestations.** `loaders/evidence.py` stamps
  `__path` onto each parsed dict for traceability. Don't strip it; the
  `control_status` tool surfaces it as `latest_attestation.path`.

## What to never do

- Add a write path. Anywhere. (Audit log is the sole exception, and it's
  already there.)
- Shell out, invoke `git`, run `make`, or import anything that does.
- Read a workspace path with bare `open()` / `Path.read_text()` on a path
  you constructed yourself. Discover paths with `WorkspaceRoot` methods
  first; reading a path that `safe_rglob` already yielded is fine (see
  `loaders/evidence.py`).
- Introduce a config file or a global mutable singleton.
- Add a dependency without justifying it; the runtime deps are deliberately
  minimal (`mcp`, `pydantic`, `ruamel.yaml`, `jsonschema`, `python-dateutil`).
- Bypass classification filtering on a list-returning tool.
- Loosen mypy strict or ruff rules to make a change pass.

## Useful pointers

- `README.md` — user-facing install/usage and tool table.
- `CONTRIBUTING.md` — PR process and required checks.
- `SECURITY.md` — security model and disclosure.
- `src/isms_mcp/workspace.py` — re-read whenever touching path handling.
- `tests/test_workspace.py` — the security regression suite.
- `tests/test_tools.py` — fixture `populated_workspace` shows the expected
  on-disk YAML shapes for every loader.
