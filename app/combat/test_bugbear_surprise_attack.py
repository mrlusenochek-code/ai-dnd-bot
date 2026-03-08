from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def _line_texts(patch) -> list[str]:
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


def _build_state(session_id: str) -> None:
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Bugbear",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=1,
        stats={"str": 50, "dex": 50, "con": 50},
        race_features={
            "features": {
                "surprise_attack": {
                    "extra_damage": "2d6",
                    "limit": "once_per_combat",
                    "trigger": "hit_on_first_turn_vs_surprised",
                }
            }
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Target",
        side="enemy",
        hp_current=40,
        hp_max=40,
        ac=10,
        initiative=10,
        stats={"dex": 50},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0


def test_bugbear_surprise_attack_triggers_once_per_combat(monkeypatch) -> None:
    session_id = "test_bugbear_surprise_attack_triggers_once_per_combat"
    _build_state(session_id)
    rolls = iter([15, 3, 5, 6, 15, 3])  # attack d20, weapon d6, surprise 2d6, then attack d20, weapon d6
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch_1, err_1 = handle_live_combat_action("combat_attack", session_id)
        assert err_1 is None
        assert patch_1 is not None
        texts_1 = _line_texts(patch_1)
        assert any("Внезапное нападение: +" in t for t in texts_1)
        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].surprise_attack_used is True

        state_now.turn_index = 0
        state_now.combatants["pc_1"].action_available = True
        patch_2, err_2 = handle_live_combat_action("combat_attack", session_id)
        assert err_2 is None
        assert patch_2 is not None
        texts_2 = _line_texts(patch_2)
        assert not any("Внезапное нападение: +" in t for t in texts_2)
    finally:
        end_combat(session_id)


def test_bugbear_surprise_attack_does_not_trigger_if_target_already_acted(monkeypatch) -> None:
    session_id = "test_bugbear_surprise_attack_does_not_trigger_if_target_already_acted"
    _build_state(session_id)
    state = get_combat(session_id)
    assert state is not None
    state.combatants["enemy_1"].turns_taken = 1
    rolls = iter([15, 3])  # attack d20, weapon d6
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert not any("Внезапное нападение: +" in t for t in texts)
        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].surprise_attack_used is False
    finally:
        end_combat(session_id)
