"""Pagination helper."""

from __future__ import annotations

from typing import TypeVar

from isms_mcp.models import Pagination

T = TypeVar("T")


def paginate(items: list[T], page: int, page_size: int) -> tuple[list[T], Pagination]:
    total = len(items)
    pages = (total + page_size - 1) // page_size if total else 0
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], Pagination(page=page, page_size=page_size, total=total, pages=pages)
