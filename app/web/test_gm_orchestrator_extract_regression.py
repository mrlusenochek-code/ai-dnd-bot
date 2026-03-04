from pathlib import Path
import re


def _read_source(name: str) -> str:
    return Path(__file__).with_name(name).read_text(encoding="utf-8")


def _async_function_block(source: str, name: str) -> str | None:
    pattern = re.compile(rf"^async def {re.escape(name)}\(.*", re.MULTILINE)
    m = pattern.search(source)
    if not m:
        return None
    start = m.start()
    tail = source[m.end():]
    m_next = re.search(r"\n\n(?:async def |def |# -------------------------)", tail)
    end = len(source) if not m_next else m.end() + m_next.start()
    return source[start:end]


def test_server_old_auto_tasks_are_extracted_or_wrapped():
    src = _read_source("server.py")

    gm_block = _async_function_block(src, "_auto_gm_reply_task")
    if gm_block is not None:
        assert "gm_orchestrator.run_turn_gm(" in gm_block

    round_block = _async_function_block(src, "_auto_round_task")
    if round_block is not None:
        assert "gm_orchestrator.run_round_gm(" in round_block


def test_gm_orchestrator_has_extracted_functions():
    src = _read_source("gm_orchestrator.py")

    assert "async def run_two_pass(" in src
    assert "async def run_turn_gm(" in src
    assert "async def run_round_gm(" in src
    assert "async def run_lore_generation(" in src
