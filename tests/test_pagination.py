"""Tests for the pagination helper."""

from isms_mcp._pagination import paginate


def test_basic_pagination() -> None:
    items = list(range(10))
    page_items, meta = paginate(items, page=1, page_size=3)
    assert page_items == [0, 1, 2]
    assert meta.page == 1
    assert meta.page_size == 3
    assert meta.total == 10
    assert meta.pages == 4  # ceil(10/3)


def test_last_page() -> None:
    items = list(range(10))
    page_items, meta = paginate(items, page=4, page_size=3)
    assert page_items == [9]
    assert meta.pages == 4


def test_empty_list() -> None:
    page_items, meta = paginate([], page=1, page_size=10)
    assert page_items == []
    assert meta.total == 0
    assert meta.pages == 0


def test_beyond_last_page() -> None:
    items = [1, 2, 3]
    page_items, meta = paginate(items, page=5, page_size=10)
    assert page_items == []
    assert meta.total == 3
    assert meta.pages == 1


def test_exact_page_boundary() -> None:
    items = list(range(6))
    page_items, meta = paginate(items, page=2, page_size=3)
    assert page_items == [3, 4, 5]
    assert meta.pages == 2


def test_single_item() -> None:
    page_items, meta = paginate(["only"], page=1, page_size=50)
    assert page_items == ["only"]
    assert meta.total == 1
    assert meta.pages == 1
