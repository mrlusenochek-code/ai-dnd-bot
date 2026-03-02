from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from app.gm import service as gm_service


def _run_two_pass_with_llm(
    *,
    draft_prompt: str,
    final_text: str,
    repair_text: str,
    location_fallback: str,
    previous_gm_text: str = "",
) -> tuple[str, list[dict[str, Any]]]:
    calls: list[dict[str, Any]] = []

    async def fake_generate_from_prompt(*, prompt: str, timeout_seconds: float | None = None, num_predict: int | None = None):
        calls.append({"prompt": prompt, "timeout_seconds": timeout_seconds, "num_predict": num_predict})
        if len(calls) == 1:
            return {"text": "Черновик сцены.\nЧто делаете дальше?", "finish_reason": "stop", "usage": {"eval_count": 1}}
        if len(calls) == 2:
            return {"text": final_text, "finish_reason": "stop", "usage": {"eval_count": 2}}
        return {"text": repair_text, "finish_reason": "stop", "usage": {"eval_count": 3}}

    async def fake_load_actor_context(_db, _sess):
        return {}, {}, {}

    out = asyncio.run(
        gm_service.run_two_pass(
            SimpleNamespace(commit=None),
            SimpleNamespace(settings={}),
            session_id="sess_test",
            draft_prompt=draft_prompt,
            default_actor_uid=1,
            previous_gm_text=previous_gm_text,
            location_fallback=location_fallback,
            timeout_seconds=30.0,
            draft_num_predict=256,
            final_num_predict=256,
            combat_active=False,
            load_actor_context=fake_load_actor_context,
            compute_check_mod=lambda _check, _ch, _mods: 0,
            roll_check=lambda _mode: (10, None, 10),
            build_check_result=lambda check, mod, roll_a, roll_b, roll: {
                "actor_uid": check.get("actor_uid"),
                "name": check.get("name"),
                "mod": mod,
                "roll_a": roll_a,
                "roll_b": roll_b,
                "roll": roll,
            },
            character_xp_gain_from_check=lambda _res: 0,
            level_from_xp_total=lambda xp, lvl: lvl,
            skill_xp_gain=lambda _res: 0,
            xp_to_next_skill_rank=lambda _rank: 100,
            llm_generate=fake_generate_from_prompt,
            logger=None,
        )
    )
    return out[0], calls


def test_prison_hallucination_regression_repairs_two_pass_output() -> None:
    draft_prompt = (
        "MOVED: false\n"
        "Контекст (последние события):\n"
        "- Игрок: остаюсь на площади и смотрю на толпу"
    )
    final_text = (
        "Николай говорит, что Крылов уже арестован по суду.\n"
        "Рядом стоит заключенный, а тюремные заключенные ждут конвой у камеры.\n"
        "Что делаете дальше?"
    )
    repair_text = "На площади ветер гонит пыль, и ты замечаешь настороженные взгляды прохожих.\nЧто делаете дальше?"
    final_out, calls = _run_two_pass_with_llm(
        draft_prompt=draft_prompt,
        final_text=final_text,
        repair_text=repair_text,
        location_fallback="Городская площадь у фонтана",
    )
    assert len(calls) == 3
    assert final_out == repair_text


def test_sentence_start_names_and_prison_shift_are_detected() -> None:
    final_text = (
        "Николай говорит, что Крылов уже арестован по суду.\n"
        "Рядом стоит заключенный, а тюремные заключенные ждут конвой у камеры."
    )
    tokens = gm_service._extract_capitalized_tokens(final_text)
    assert "Николай" in tokens
    assert "Крылов" in tokens

    hits = gm_service._find_scene_lock_violations(
        final_text,
        "Контекст: площадь и стража",
        "Городская площадь",
    )
    assert "заключенный вне контекста" in hits
    assert "по суду вне контекста" in hits
