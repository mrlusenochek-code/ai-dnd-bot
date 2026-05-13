from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.combat.state import Combatant, consume_last_ended_pc_hp, end_combat, start_combat
from app.rules.character_catalog import CLASS_CATALOG
from app.web import state_builder, ws_handlers
from app.web.gameplay_helpers import _char_to_payload


def _fighter_second_wind_mechanics() -> dict:
    fighter = next((item for item in CLASS_CATALOG if str(item.get("key") or "") == "fighter"), None)
    assert fighter is not None
    features = (fighter.get("features_by_level") or {}).get(1) or []
    second_wind = next((item for item in features if str((item or {}).get("key") or "") == "second_wind"), None)
    assert isinstance(second_wind, dict)
    mechanics = second_wind.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _fighter_character(*, hp: int, hp_max: int, sta: int = 12, sta_max: int = 12) -> SimpleNamespace:
    return SimpleNamespace(
        name="фы",
        class_kit="fighter",
        class_skin="Fighter",
        race_kit="aarakocra",
        race_skin="Aarakocra",
        level=3,
        hp=hp,
        hp_max=hp_max,
        sta=sta,
        sta_max=sta_max,
        hit_die=10,
        hit_dice_remaining=1,
        hit_dice_max=3,
        stats={},
        xp_total=0,
        class_features={
            "features": [
                {
                    "key": "second_wind",
                    "name_ru": "Второе дыхание",
                    "mechanics": _fighter_second_wind_mechanics(),
                }
            ],
            "runtime": {"second_wind_used": True},
        },
        race_features={"runtime": {}},
    )


def test_end_combat_keeps_latest_pc_hp_snapshot_before_cleanup() -> None:
    session_id = "test_end_combat_keeps_latest_pc_hp_snapshot_before_cleanup"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="фы",
        side="pc",
        hp_current=10,
        hp_max=24,
        ac=15,
        initiative=10,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Разбойник",
        side="enemy",
        hp_current=0,
        hp_max=12,
        ac=12,
        initiative=8,
    )

    end_combat(session_id)

    assert consume_last_ended_pc_hp(session_id) == {1: 10}
    assert consume_last_ended_pc_hp(session_id) == {}


def test_victory_side_effects_persist_wounded_pc_hp_without_healing(monkeypatch) -> None:
    session_id = "test_victory_side_effects_persist_wounded_pc_hp_without_healing"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="фы",
        side="pc",
        hp_current=10,
        hp_max=24,
        ac=15,
        initiative=10,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Разбойник",
        side="enemy",
        hp_current=0,
        hp_max=12,
        ac=12,
        initiative=8,
    )
    end_combat(session_id)

    ch = _fighter_character(hp=24, hp_max=24)
    sess = SimpleNamespace(id=session_id, settings={})
    patch = {"status": "Бой завершён", "lines": [{"text": "Победа: противники повержены."}]}

    async def _fake_load_actor_context(_db, _sess):
        return ({}, {1: ch}, {})

    async def _false_reward(*_args, **_kwargs):
        return False

    monkeypatch.setattr(state_builder, "_load_actor_context", _fake_load_actor_context)
    monkeypatch.setattr(state_builder, "_grant_combat_rewards_once", _false_reward)
    monkeypatch.setattr(state_builder, "_grant_defeat_outcome_once", _false_reward)
    monkeypatch.setattr(state_builder, "_apply_defeat_effects_once", _false_reward)

    changed = asyncio.run(state_builder._apply_combat_outcome_side_effects(None, sess, session_id, patch))

    assert changed is True
    assert ch.hp == 10
    payload = _char_to_payload(ch)
    assert payload is not None
    assert payload["hp"] == 10
    assert payload["hp_max"] == 24


def test_short_and_long_rest_after_victory_use_persisted_wounded_hp() -> None:
    ch = _fighter_character(hp=10, hp_max=24)

    short_result = ws_handlers._apply_personal_rest(ch, long_rest=False)
    assert short_result["class_reset"] is True
    assert ch.hp == 10
    assert ch.sta == 12

    long_result = ws_handlers._apply_personal_rest(ch, long_rest=True)
    assert long_result["old_hp"] == 10
    assert ch.hp == 24
    assert ch.sta == 12
