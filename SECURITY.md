# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.1.x   | :white_check_mark: |

## Reporting a Vulnerability

If you discover a security vulnerability in isms-mcp, please report it
responsibly:

1. **Do not** open a public issue.
2. Email the maintainers or use
   [GitHub Security Advisories](https://github.com/rmednitzer/isms-mcp/security/advisories/new)
   to report the issue privately.
3. Include a description of the vulnerability, steps to reproduce, and any
   potential impact.

We aim to acknowledge reports within 48 hours and will work with you to
understand and address the issue before any public disclosure.

## Security Model

isms-mcp is designed as a **read-only** MCP overlay with the following
security properties:

- **Workspace-scoped filesystem access.** All reads are restricted to four
  allow-listed subtrees (`docs`, `template`, `instance`, `framework-refs`)
  via `WorkspaceRoot`. Symlink targets are resolved and verified.
- **No mutations.** The server never writes to the filesystem, invokes
  `git`, runs `make`, or modifies state.
- **No `0.0.0.0` bind without explicit opt-in.** HTTP transport binds to
  `127.0.0.1` by default; binding all interfaces requires setting
  `ISMS_MCP_HTTP_ALLOW_ANY=yes-i-understand-the-risk`.
- **Bearer token required for HTTP.** The `ISMS_MCP_HTTP_TOKEN` environment
  variable is mandatory when using HTTP transport.
- **Classification filtering.** Entries marked `classification: restricted`
  are dropped over HTTP transport unless explicitly allowed.
