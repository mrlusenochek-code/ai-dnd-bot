from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.resolution import AttackResolution
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    out: list[str] = []
    if not isinstance(lines, list):
        return out
    for line in lines:
        if isinstance(line, dict) and isinstance(line.get("text"), str):
            out.append(line["text"])
    return out


def _build_state(session_id: str, *, hp_current: int, hp_max: int = 20) -> None:
    state = start_combat(session_id)
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Орк-налётчик",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=20,
        action_available=True,
    )
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Полуорк",
        side="pc",
        hp_current=hp_current,
        hp_max=hp_max,
        ac=10,
        initiative=10,
        race_features={
            "features": {
                "relentless_endurance": {
                    "type": "relentless_endurance",
                    "uses": "per_long_rest",
                    "set_hp_to": 1,
                }
            }
        },
    )
    state.combatants["pc_2"] = Combatant(
        key="pc_2",
        name="Союзник",
        side="pc",
        hp_current=10,
        hp_max=10,
        ac=11,
        initiative=5,
    )
    state.order = ["enemy_1", "pc_1", "pc_2"]
    state.turn_index = 0


def test_relentless_endurance_triggers_once_before_long_rest(monkeypatch) -> None:
    session_id = "test_half_orc_relentless_endurance_once"
    _build_state(session_id, hp_current=5, hp_max=20)

    def _always_hit(**kwargs):
        return AttackResolution(
            d20_roll=15,
            attack_bonus=int(kwargs.get("attack_bonus") or 0),
            target_ac=int(kwargs.get("target_ac") or 10),
            total_to_hit=99,
            is_hit=True,
            is_crit=False,
            damage_roll=6,
            damage_bonus=0,
            total_damage=6,
        )

    monkeypatch.setattr("app.combat.live_actions.resolve_attack_roll", _always_hit)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 10)

    try:
        patch_1, err_1 = handle_live_combat_action("combat_attack", session_id)
        assert err_1 is None
        assert patch_1 is not None
        texts_1 = _line_texts(patch_1)
        assert any("Неукротимая стойкость" in t for t in texts_1)

        state = get_combat(session_id)
        assert state is not None
        target = state.combatants["pc_1"]
        assert target.hp_current == 1
        runtime = ((target.race_features or {}).get("runtime") or {})
        assert runtime.get("relentless_endurance_used") is True

        state.turn_index = 0
        state.combatants["enemy_1"].action_available = True

        patch_2, err_2 = handle_live_combat_action("combat_attack", session_id)
        assert err_2 is None
        assert patch_2 is not None

        state = get_combat(session_id)
        assert state is not None
        target = state.combatants["pc_1"]
        assert target.hp_current == 0
        assert target.is_dead is False
    finally:
        end_combat(session_id)


def test_relentless_endurance_does_not_prevent_instant_death(monkeypatch) -> None:
    session_id = "test_half_orc_relentless_endurance_instant_death"
    _build_state(session_id, hp_current=5, hp_max=20)

    def _massive_hit(**kwargs):
        return AttackResolution(
            d20_roll=15,
            attack_bonus=int(kwargs.get("attack_bonus") or 0),
            target_ac=int(kwargs.get("target_ac") or 10),
            total_to_hit=99,
            is_hit=True,
            is_crit=False,
            damage_roll=25,
            damage_bonus=0,
            total_damage=25,
        )

    monkeypatch.setattr("app.combat.live_actions.resolve_attack_roll", _massive_hit)
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: 10)

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None

        state = get_combat(session_id)
        assert state is not None
        target = state.combatants["pc_1"]
        assert target.hp_current == 0
        assert target.is_dead is True
        texts = _line_texts(patch)
        assert any("Мгновенная смерть" in t for t in texts)
        assert not any("Неукротимая стойкость" in t for t in texts)
    finally:
        end_combat(session_id)
