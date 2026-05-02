from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

from app.gm import service as gm_service
from app.web import server_impl, ws_handlers
from app.web.check_engine import build_check_result


def _rogue_reliable_talent_features() -> dict:
    return {
        "features": [
            {
                "key": "reliable_talent",
                "mechanics": {
                    "type": "reliable_talent",
                    "min_d20": 10,
                    "requires_proficiency": True,
                    "applies_to": ["ability_check"],
                },
            }
        ],
        "runtime": {},
    }


def _skillful_rogue(*, level: int = 11) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid.uuid4(),
        name="Плут",
        level=level,
        xp_total=0,
        stats={"dex": 70, "wis": 70, "int": 50},
        class_features=_rogue_reliable_talent_features() if level >= 11 else {"features": [], "runtime": {}},
        race_features={"proficiencies": {"tools": ["thieves_tools"]}},
    )


def test_manual_like_skill_check_uses_reliable_talent_for_proficient_skill() -> None:
    rogue = _skillful_rogue(level=11)
    skill_mods_by_char = {rogue.id: {"stealth": 2}}
    mod = server_impl._compute_check_mod({"kind": "skill", "name": "stealth"}, rogue, skill_mods_by_char)
    adjusted_roll, applied = server_impl._apply_reliable_talent_for_check(
        {"kind": "skill", "name": "stealth"},
        rogue,
        skill_mods_by_char,
        roll=3,
    )
    result = build_check_result({"kind": "skill", "name": "stealth", "dc": 0, "mode": "normal"}, mod=mod, roll_a=3, roll_b=None, roll=adjusted_roll)

    assert applied is True
    assert adjusted_roll == 10
    assert result["total"] == 14


def test_skill_without_proficiency_keeps_original_roll() -> None:
    rogue = _skillful_rogue(level=11)
    skill_mods_by_char = {rogue.id: {"athletics": 0}}
    mod = server_impl._compute_check_mod({"kind": "skill", "name": "athletics"}, rogue, skill_mods_by_char)
    adjusted_roll, applied = server_impl._apply_reliable_talent_for_check(
        {"kind": "skill", "name": "athletics"},
        rogue,
        skill_mods_by_char,
        roll=3,
    )
    result = build_check_result({"kind": "skill", "name": "athletics", "dc": 0, "mode": "normal"}, mod=mod, roll_a=3, roll_b=None, roll=adjusted_roll)

    assert applied is False
    assert adjusted_roll == 3
    assert result["total"] == 3


def test_toolcheck_with_proficiency_uses_reliable_talent() -> None:
    rogue = _skillful_rogue(level=11)
    mod = ws_handlers._effective_toolcheck_mod(rogue, "thieves_tools")
    adjusted_roll, applied = ws_handlers._reliable_talent_adjusted_roll(
        rogue,
        kind="tool",
        roll=4,
        proficient=True,
    )
    result = build_check_result({"kind": "tool", "name": "thieves_tools", "dc": 0, "mode": "normal"}, mod=mod, roll_a=4, roll_b=None, roll=adjusted_roll)

    assert applied is True
    assert adjusted_roll == 10
    assert result["total"] == 14


def test_non_rogue_or_low_level_does_not_get_reliable_talent() -> None:
    low_level_rogue = _skillful_rogue(level=10)
    adjusted_roll, applied = ws_handlers._reliable_talent_adjusted_roll(
        low_level_rogue,
        kind="skill",
        roll=4,
        proficient=True,
    )
    assert applied is False
    assert adjusted_roll == 4


def test_composite_check_applies_only_when_best_candidate_is_proficient() -> None:
    rogue = _skillful_rogue(level=11)
    skill_mods_by_char = {
        rogue.id: {
            "perception": 2,
            "athletics": 0,
        }
    }
    adjusted_roll, applied = server_impl._apply_reliable_talent_for_check(
        {"kind": "skill", "name": "athletics|perception"},
        rogue,
        skill_mods_by_char,
        roll=2,
    )
    assert applied is True
    assert adjusted_roll == 10

    skill_mods_by_char[rogue.id] = {"perception": 0}
    adjusted_roll_2, applied_2 = server_impl._apply_reliable_talent_for_check(
        {"kind": "skill", "name": "athletics|perception"},
        rogue,
        skill_mods_by_char,
        roll=2,
    )
    assert applied_2 is False
    assert adjusted_roll_2 == 2


def test_gm_two_pass_skill_check_applies_reliable_talent() -> None:
    rogue = _skillful_rogue(level=11)
    call_count = {"n": 0}

    class _FakeExecuteResult:
        def scalar_one_or_none(self):
            return None

    class _FakeDb:
        async def execute(self, _query):
            return _FakeExecuteResult()

        def add(self, _obj) -> None:
            return None

        async def commit(self) -> None:
            return None

    async def fake_load_actor_context(_db, _sess):
        return {}, {1: rogue}, {rogue.id: {"stealth": 2}}

    async def fake_generate(*, prompt: str, timeout_seconds: float | None = None, num_predict: int | None = None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return {
                "text": (
                    "Сцена продолжается.\n"
                    "@@CHECK {\"actor_uid\":1,\"kind\":\"skill\",\"name\":\"stealth\",\"dc\":14,\"mode\":\"normal\"}\n"
                    "Что делаете дальше?"
                ),
                "finish_reason": "stop",
                "usage": {"eval_count": 11},
            }
        return {"text": "Финал сцены.\nЧто делаете дальше?", "finish_reason": "stop", "usage": {"eval_count": 22}}

    gm_text, _draft_meta, _final_meta, _checks, check_results = asyncio.run(
        gm_service.run_two_pass(
            _FakeDb(),
            SimpleNamespace(),
            session_id="sess_test",
            draft_prompt="Контекст",
            default_actor_uid=1,
            previous_gm_text="",
            location_fallback="ЛОКАЦИЯ",
            timeout_seconds=1.0,
            draft_num_predict=1000,
            final_num_predict=1000,
            combat_active=False,
            load_actor_context=fake_load_actor_context,
            compute_check_mod=server_impl._compute_check_mod,
            roll_check=lambda _mode: (3, None, 3),
            build_check_result=server_impl._build_check_result,
            character_xp_gain_from_check=lambda _result: 0,
            level_from_xp_total=lambda level, _xp: level,
            skill_xp_gain=lambda _result: 0,
            xp_to_next_skill_rank=lambda _rank: 999,
                apply_reliable_talent_for_check=server_impl._apply_reliable_talent_for_check,
                clamp_fn=server_impl._clamp,
                as_int_fn=server_impl.as_int,
                get_phase_fn=lambda _sess: "explore",
                trim_for_log_fn=lambda text, _limit=0: text,
                looks_like_combat_drift_fn=lambda _text: False,
                llm_generate=fake_generate,
                logger=server_impl.logger,
        )
    )

    assert "Что делаете дальше?" in gm_text
    assert len(check_results) == 1
    assert check_results[0]["roll"] == 10
    assert check_results[0]["total"] == 14
    assert "Надёжный талант: d20 ниже 10 считается как 10." in (check_results[0].get("extra_bonus_texts") or [])
