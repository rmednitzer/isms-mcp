"""Pagination helper."""

from isms_mcp.models import Pagination


def paginate[T](items: list[T], page: int, page_size: int) -> tuple[list[T], Pagination]:
    total = len(items)
    pages = (total + page_size - 1) // page_size if total else 0
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], Pagination(page=page, page_size=page_size, total=total, pages=pages)
