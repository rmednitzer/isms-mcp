"""Workspace data loaders.

Each loader prefers ``instance/`` content and falls back to ``template/`` for
workspaces where the template has not been rendered yet. All file reads go
through ``WorkspaceRoot.safe_read_text`` for path-traversal safety.
"""
