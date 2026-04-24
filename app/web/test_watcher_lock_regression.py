from pathlib import Path


def _read_watchers_source() -> str:
    return Path(__file__).with_name("watchers.py").read_text(encoding="utf-8")


def _read_server_source() -> str:
    return Path(__file__).with_name("server.py").read_text(encoding="utf-8")


def _read_ws_turns_source() -> str:
    return Path(__file__).with_name("ws_turns.py").read_text(encoding="utf-8")


def _async_function_block(source: str, name: str) -> str:
    marker = f"async def {name}():"
    start = source.find(marker)
    assert start >= 0, f"Function not found: {name}"

    next_def = source.find("\n\nasync def ", start + len(marker))
    if next_def < 0:
        next_def = len(source)
    return source[start:next_def]


def test_timer_watcher_uses_unlocked_broadcast_only():
    src = _read_watchers_source()
    block = _async_function_block(src, "timer_watcher")

    assert "_broadcast_state_unlocked(" in block
    assert "broadcast_state(" not in block


def test_inactive_watcher_uses_unlocked_broadcast_only():
    src = _read_watchers_source()
    block = _async_function_block(src, "inactive_watcher")

    assert "_broadcast_state_unlocked(" in block
    assert "broadcast_state(" not in block


def test_timer_watcher_short_circuits_when_timeout_disabled():
    src = _read_watchers_source()
    block = _async_function_block(src, "timer_watcher")

    assert "if TURN_TIMEOUT_SECONDS <= 0:" in block
    assert "await asyncio.sleep(1)" in block
    assert "continue" in block


def test_inactive_watcher_short_circuits_when_inactive_timeout_disabled():
    src = _read_watchers_source()
    block = _async_function_block(src, "inactive_watcher")

    assert "if INACTIVE_TIMEOUT_SECONDS <= 0:" in block
    assert "await asyncio.sleep(INACTIVE_SCAN_PERIOD_SECONDS)" in block
    assert "continue" in block


def test_ws_turns_default_timeout_is_disabled():
    src = _read_ws_turns_source()

    assert 'TURN_TIMEOUT_SECONDS = int(os.getenv("TURN_TIMEOUT_SECONDS", "0"))' in src


def test_compute_remaining_returns_none_when_timeout_disabled():
    src = _read_ws_turns_source()

    assert "if TURN_TIMEOUT_SECONDS <= 0:" in src
    assert "return None" in src


def test_server_does_not_define_watchers():
    src = _read_server_source()
    assert "async def timer_watcher" not in src
    assert "async def inactive_watcher" not in src
