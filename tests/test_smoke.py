from isms_mcp.tools import register_all


def test_register_all_is_callable() -> None:
    assert callable(register_all)
