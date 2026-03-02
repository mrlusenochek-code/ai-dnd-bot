from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from app.web import server


def test_sanitize_gm_output_removes_meta_and_normalizes_question():
    raw = (
        "Анализ:\n"
        "Ответ: Сцена продолжается, если вы хотите.\n"
        "Варианты действий:\n"
        "- шаг 1\n"
        "- шаг 2\n"
        "Что делаете дальше?\n"
        "Что делаете дальше?"
    )
    out = server._sanitize_gm_output(raw)
    assert "Анализ" not in out
    assert "если вы хотите" not in out.lower()
    assert "Варианты действий" not in out
    assert out.endswith("Что делаете дальше?")


def test_sanitize_gm_output_empty_brackets_current_fallback_behavior():
    out = server._sanitize_gm_output("[]")
    assert out == "[]"


def test_sanitize_combat_narration_strips_mechanics_and_enforces_question():
    raw = "Ты наносишь урон 12, бросок d20 = 18, у цели HP 3/10 и AC 13."
    out = server._sanitize_combat_narration(raw)
    low = out.lower()
    assert "урон" not in low
    assert "hp" not in low
    assert "ac" not in low
    assert "d20" not in low
    assert out.endswith("Что делаете дальше?")


def test_extract_checks_from_draft_returns_clean_text_and_checks():
    draft = (
        "Текст сцены.\n"
        "@@CHECK {\"actor_uid\":2,\"kind\":\"skill\",\"name\":\"perception\",\"dc\":14,\"mode\":\"normal\"}\n"
        "Что делаете дальше?"
    )
    text, checks, has_human = server._extract_checks_from_draft(draft, default_actor_uid=None)
    assert "@@CHECK" not in text
    assert text.startswith("Текст сцены")
    assert len(checks) == 1
    assert checks[0]["actor_uid"] == 2
    assert checks[0]["name"] == "perception"
    assert has_human is False


def test_checks_from_human_text_detects_textual_check_lines():
    text = "Проверка: perception DC 15. Потом идем дальше."
    checks = server._checks_from_human_text(text, default_actor_uid=7)
    assert len(checks) == 1
    assert checks[0]["actor_uid"] == 7
    assert checks[0]["name"] == "perception"
    assert checks[0]["dc"] == 15


def test_mandatory_check_category_detects_theft_and_mechanics():
    theft_text = "Я пытаюсь украсть кошелек у торговца."
    assert server._mandatory_check_category(theft_text) == "theft"

    mechanics_text = "Пытаюсь взломать замок, в итоге вскрыл дверь."
    assert server._mandatory_check_category(mechanics_text) == "mechanics"


def test_run_gm_two_pass_normal_flow_preserves_metadata_and_calls_sanitize(monkeypatch: pytest.MonkeyPatch):
    llm_calls: list[dict[str, Any]] = []

    async def fake_generate_from_prompt(*, prompt: str, timeout_seconds: float | None = None, num_predict: int | None = None):
        llm_calls.append({"prompt": prompt, "timeout_seconds": timeout_seconds, "num_predict": num_predict})
        if len(llm_calls) == 1:
            return {"text": "Черновик сцены.\nЧто делаете дальше?", "finish_reason": "stop", "usage": {"eval_count": 11}}
        return {"text": "Финал сцены.\nЧто делаете дальше?", "finish_reason": "stop", "usage": {"eval_count": 22}}

    sanitize_calls: list[dict[str, Any]] = []

    def fake_narration_sanitize(text: Any, *, location_fallback: str | None = None) -> str:
        sanitize_calls.append({"text": str(text), "location_fallback": location_fallback})
        return str(text).strip()

    monkeypatch.setattr(server, "generate_from_prompt", fake_generate_from_prompt)
    monkeypatch.setattr(server.narration, "sanitize_gm_output", fake_narration_sanitize)
    monkeypatch.setattr(server.narration, "build_location_block", lambda settings, session_id: "ЛОКАЦИЯ")
    monkeypatch.setattr(server, "_ensure_settings", lambda sess: {})
    monkeypatch.setattr(server, "get_combat", lambda _sid: None)

    async def fake_load_actor_context(_db, _sess):
        return {}, {}, {}

    monkeypatch.setattr(server, "_load_actor_context", fake_load_actor_context)

    fake_db = SimpleNamespace(commit=None)
    fake_sess = SimpleNamespace(settings={})

    final_text, draft_meta, final_meta, checks, check_results = asyncio.run(
        server._run_gm_two_pass(
            fake_db,
            fake_sess,
            session_id="sess_test",
            draft_prompt="Контекст (последние события):\n- Игрок: иду вперед",
            default_actor_uid=1,
            previous_gm_text="",
        )
    )

    assert len(llm_calls) == 2
    assert final_text == "Финал сцены.\nЧто делаете дальше?"
    assert draft_meta.get("usage", {}).get("eval_count") == 11
    assert final_meta.get("usage", {}).get("eval_count") == 22
    assert draft_meta.get("finish_reason") == "stop"
    assert final_meta.get("finish_reason") == "stop"
    assert checks == []
    assert check_results == []
    assert sanitize_calls
    assert sanitize_calls[-1]["location_fallback"] == "ЛОКАЦИЯ"


def test_run_gm_two_pass_empty_final_triggers_fallback_call(monkeypatch: pytest.MonkeyPatch):
    llm_calls: list[dict[str, Any]] = []

    async def fake_generate_from_prompt(*, prompt: str, timeout_seconds: float | None = None, num_predict: int | None = None):
        llm_calls.append({"prompt": prompt, "timeout_seconds": timeout_seconds, "num_predict": num_predict})
        if len(llm_calls) == 1:
            return {"text": "Черновик.\nЧто делаете дальше?", "finish_reason": "stop", "usage": {"eval_count": 1}}
        if len(llm_calls) == 2:
            return {"text": "", "finish_reason": "stop", "usage": {"eval_count": 2}}
        return {"text": "[]", "finish_reason": "stop", "usage": {"eval_count": 3}}

    monkeypatch.setattr(server, "generate_from_prompt", fake_generate_from_prompt)
    monkeypatch.setattr(server.narration, "build_location_block", lambda settings, session_id: "ЛОКАЦИЯ")
    monkeypatch.setattr(server, "_ensure_settings", lambda sess: {})
    monkeypatch.setattr(server, "get_combat", lambda _sid: None)

    async def fake_load_actor_context(_db, _sess):
        return {}, {}, {}

    monkeypatch.setattr(server, "_load_actor_context", fake_load_actor_context)

    fake_db = SimpleNamespace(commit=None)
    fake_sess = SimpleNamespace(settings={})

    final_text, draft_meta, final_meta, checks, check_results = asyncio.run(
        server._run_gm_two_pass(
            fake_db,
            fake_sess,
            session_id="sess_test",
            draft_prompt="Контекст (последние события):\n- Игрок: жду",
            default_actor_uid=1,
            previous_gm_text="",
        )
    )

    assert len(llm_calls) == 3
    assert final_text
    assert "Что делаете дальше" in final_text
    assert draft_meta.get("usage", {}).get("eval_count") == 1
    assert final_meta.get("usage", {}).get("eval_count") == 2
    assert checks == []
    assert check_results == []
