from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from app.gm import service as gm_service
from app.web import server


def _make_fake_generate() -> tuple[Any, list[dict[str, Any]]]:
    calls: list[dict[str, Any]] = []

    async def fake_generate_from_prompt(*, prompt: str, timeout_seconds: float | None = None, num_predict: int | None = None):
        calls.append({"prompt": prompt, "timeout_seconds": timeout_seconds, "num_predict": num_predict})
        if len(calls) == 1:
            return {"text": "Черновик сцены.\nЧто делаете дальше?", "finish_reason": "stop", "usage": {"eval_count": 11}}
        return {"text": "Финал сцены.\nЧто делаете дальше?", "finish_reason": "stop", "usage": {"eval_count": 22}}

    return fake_generate_from_prompt, calls


def test_run_two_pass_wrapper_equals_service(monkeypatch):
    async def fake_load_actor_context(_db, _sess):
        return {}, {}, {}

    def fake_narration_sanitize(text: Any, *, location_fallback: str | None = None) -> str:
        return str(text).strip()

    monkeypatch.setattr(server, "_load_actor_context", fake_load_actor_context)
    monkeypatch.setattr(server.narration, "sanitize_gm_output", fake_narration_sanitize)
    monkeypatch.setattr(server.narration, "build_location_block", lambda settings, session_id: "ЛОКАЦИЯ")
    monkeypatch.setattr(server, "_ensure_settings", lambda sess: {})
    monkeypatch.setattr(server, "get_combat", lambda _sid: None)

    fake_db = SimpleNamespace(commit=None)
    fake_sess = SimpleNamespace(settings={})

    fake_generate_wrapper, _calls_wrapper = _make_fake_generate()
    monkeypatch.setattr(server, "generate_from_prompt", fake_generate_wrapper)
    wrapper_result = asyncio.run(
        server._run_gm_two_pass(
            fake_db,
            fake_sess,
            session_id="sess_test",
            draft_prompt="Контекст (последние события):\n- Игрок: иду вперед",
            default_actor_uid=1,
            previous_gm_text="",
        )
    )

    fake_generate_service, _calls_service = _make_fake_generate()
    service_result = asyncio.run(
        gm_service.run_two_pass(
            fake_db,
            fake_sess,
            session_id="sess_test",
            draft_prompt="Контекст (последние события):\n- Игрок: иду вперед",
            default_actor_uid=1,
            previous_gm_text="",
            location_fallback="ЛОКАЦИЯ",
            timeout_seconds=server.GM_OLLAMA_TIMEOUT_SECONDS,
            draft_num_predict=server.GM_DRAFT_NUM_PREDICT,
            final_num_predict=server.GM_FINAL_NUM_PREDICT,
            combat_active=False,
            load_actor_context=server._load_actor_context,
            compute_check_mod=server._compute_check_mod,
            roll_check=server._roll_check,
            build_check_result=server._build_check_result,
            character_xp_gain_from_check=server._character_xp_gain_from_check,
            level_from_xp_total=server._level_from_xp_total,
            skill_xp_gain=server._skill_xp_gain,
            xp_to_next_skill_rank=server._xp_to_next_skill_rank,
            clamp_fn=server._clamp,
            as_int_fn=server.as_int,
            get_phase_fn=server._get_phase,
            trim_for_log_fn=server._trim_for_log,
            looks_like_combat_drift_fn=server._looks_like_combat_drift,
            llm_generate=fake_generate_service,
            logger=server.logger,
        )
    )

    assert wrapper_result == service_result
