# Contributing to isms-mcp

Thank you for your interest in contributing!

## Development Setup

```bash
# Clone the repository
git clone https://github.com/rmednitzer/isms-mcp.git
cd isms-mcp

# Install dependencies (requires uv)
uv sync --extra dev --extra http

# Run the full check suite
uv run ruff check
uv run ruff format --check
uv run mypy src/
uv run pytest -v
```

## Code Quality

All contributions must pass:

- **Ruff** linting and formatting (`ruff check`, `ruff format --check`)
- **Mypy** strict type checking (`mypy src/`)
- **Pytest** tests (`pytest -v`)

The CI pipeline runs these checks on every pull request against Python 3.12
and 3.13.

## Pull Request Guidelines

1. Fork the repository and create a feature branch from `main`.
2. Make focused, minimal changes that address a single concern.
3. Add or update tests for any changed behaviour.
4. Ensure all checks pass locally before opening a PR.
5. Write a clear PR description explaining the *what* and *why*.

## Hard Constraints

These constraints are non-negotiable:

- **Read only.** No tool may write to the filesystem, invoke `git`, run
  `make`, or mutate any state.
- **Workspace-scoped access.** All filesystem reads must go through
  `WorkspaceRoot` methods that enforce the allow-list.
- **No `0.0.0.0` bind without auth.** HTTP transport requires a bearer
  token and explicit opt-in for non-loopback binding.

## License

By contributing, you agree that your contributions will be licensed under
the Apache License 2.0.
