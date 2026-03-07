from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.resolution import AttackResolution
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.combat.turns import advance_turn_in_state


def _patch_line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    out: list[str] = []
    for item in lines:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if isinstance(text, str):
            out.append(text)
    return out


def test_aasimar_bonus_damage_once_per_turn(monkeypatch) -> None:
    session_id = "test_aasimar_bonus_damage_once_per_turn"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Aasimar",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=20,
        level=3,
        race_features={
            "runtime": {
                "aasimar_transformation": {
                    "active": True,
                    "kind": "protector",
                    "rounds_left": 10,
                }
            }
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=100,
        hp_max=100,
        ac=10,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    def _always_hit(**kwargs):
        return AttackResolution(
            d20_roll=15,
            attack_bonus=int(kwargs.get("attack_bonus") or 0),
            target_ac=int(kwargs.get("target_ac") or 10),
            total_to_hit=99,
            is_hit=True,
            is_crit=False,
            damage_roll=4,
            damage_bonus=0,
            total_damage=4,
        )

    monkeypatch.setattr("app.combat.live_actions.resolve_attack_roll", _always_hit)

    try:
        patch_1, err_1 = handle_live_combat_action("combat_attack", session_id)
        assert err_1 is None
        assert patch_1 is not None
        texts_1 = _patch_line_texts(patch_1)
        assert any("Доп. урон трансформации: +3 radiant (1/ход)." in t for t in texts_1)
        assert any("Урон: 4 + 0 = 7" in t for t in texts_1)

        state_now = get_combat(session_id)
        assert state_now is not None
        state_now.turn_index = 0
        state_now.combatants["pc_1"].action_available = True

        patch_2, err_2 = handle_live_combat_action("combat_attack", session_id)
        assert err_2 is None
        assert patch_2 is not None
        texts_2 = _patch_line_texts(patch_2)
        assert not any("Доп. урон трансформации" in t for t in texts_2)
        assert any("Урон: 4 + 0 = 4" in t for t in texts_2)

        state_now = get_combat(session_id)
        assert state_now is not None
        advance_turn_in_state(state_now)

        patch_3, err_3 = handle_live_combat_action("combat_attack", session_id)
        assert err_3 is None
        assert patch_3 is not None
        texts_3 = _patch_line_texts(patch_3)
        assert any("Доп. урон трансформации: +3 radiant (1/ход)." in t for t in texts_3)
        assert any("Урон: 4 + 0 = 7" in t for t in texts_3)
    finally:
        end_combat(session_id)
