from pathlib import Path


def _read_server_source() -> str:
    return Path(__file__).with_name("server.py").read_text(encoding="utf-8")


def _async_function_block(source: str, name: str) -> str:
    marker = f"async def {name}():"
    start = source.find(marker)
    assert start >= 0, f"Function not found: {name}"

    next_def = source.find("\n\nasync def ", start + len(marker))
    if next_def < 0:
        next_def = len(source)
    return source[start:next_def]


def test_timer_watcher_uses_unlocked_broadcast_only():
    src = _read_server_source()
    block = _async_function_block(src, "timer_watcher")

    assert "_broadcast_state_unlocked(" in block
    assert "broadcast_state(" not in block


def test_inactive_watcher_uses_unlocked_broadcast_only():
    src = _read_server_source()
    block = _async_function_block(src, "inactive_watcher")

    assert "_broadcast_state_unlocked(" in block
    assert "broadcast_state(" not in block
