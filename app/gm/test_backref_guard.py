from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from app.gm import service as gm_service


def _run_two_pass_with_llm(
    *,
    draft_text: str,
    final_text: str,
    repair_text: str | None = None,
    previous_gm_text: str = "",
) -> tuple[str, list[dict[str, Any]]]:
    calls: list[dict[str, Any]] = []

    async def fake_generate_from_prompt(*, prompt: str, timeout_seconds: float | None = None, num_predict: int | None = None):
        calls.append({"prompt": prompt, "timeout_seconds": timeout_seconds, "num_predict": num_predict})
        if len(calls) == 1:
            return {"text": draft_text, "finish_reason": "stop", "usage": {"eval_count": 1}}
        if len(calls) == 2:
            return {"text": final_text, "finish_reason": "stop", "usage": {"eval_count": 2}}
        return {"text": repair_text or "", "finish_reason": "stop", "usage": {"eval_count": 3}}

    async def fake_load_actor_context(_db, _sess):
        return {}, {}, {}

    out = asyncio.run(
        gm_service.run_two_pass(
            SimpleNamespace(commit=None),
            SimpleNamespace(settings={}),
            session_id="sess_test",
            draft_prompt="Контекст (последние события):\n- Игрок: жду",
            default_actor_uid=1,
            previous_gm_text=previous_gm_text,
            location_fallback="ЛОКАЦИЯ",
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


def test_backref_guard_triggers_for_unsupported_warning_reference() -> None:
    final_out, calls = _run_two_pass_with_llm(
        draft_text="Черновик сцены.\nЧто делаете дальше?",
        final_text="После его предупреждения о потенциальной опасности ты идешь медленнее.\nЧто делаете дальше?",
        repair_text="Ты замечаешь напряжение в воздухе и невольно замедляешь шаг.\nЧто делаете дальше?",
    )
    assert len(calls) == 3
    assert final_out == "Ты замечаешь напряжение в воздухе и невольно замедляешь шаг.\nЧто делаете дальше?"


def test_backref_guard_skips_when_warning_anchor_exists_in_context() -> None:
    final_out, calls = _run_two_pass_with_llm(
        draft_text="Черновик сцены.\nЧто делаете дальше?",
        final_text="После его предупреждения о потенциальной опасности ты идешь медленнее.\nЧто делаете дальше?",
        previous_gm_text="Старик дал предупреждение о том, что впереди возможна опасность.",
    )
    assert len(calls) == 2
    assert final_out == "После его предупреждения о потенциальной опасности ты идешь медленнее.\nЧто делаете дальше?"


def test_backref_guard_triggers_for_as_we_discussed_without_anchor() -> None:
    final_out, calls = _run_two_pass_with_llm(
        draft_text="Черновик сцены.\nЧто делаете дальше?",
        final_text="Как мы уже обсуждали, эта дверь ведет в подвал.\nЧто делаете дальше?",
        repair_text="Старая дверь скрипит и ведет вниз, в темный подвал.\nЧто делаете дальше?",
    )
    assert len(calls) == 3
    assert final_out == "Старая дверь скрипит и ведет вниз, в темный подвал.\nЧто делаете дальше?"
