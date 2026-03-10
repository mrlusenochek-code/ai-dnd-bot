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


def _build_bugbear_state(session_id: str) -> None:
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


def test_bugbear_surprise_attack_resets_after_end_combat_and_next_battle(monkeypatch) -> None:
    session_id = "test_bugbear_surprise_attack_resets_after_end_combat_and_next_battle"
    _build_bugbear_state(session_id)
    battle_one_rolls = iter([15, 3, 5, 6])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(battle_one_rolls))

    first_state = get_combat(session_id)
    assert first_state is not None

    patch_1, err_1 = handle_live_combat_action("combat_attack", session_id)
    assert err_1 is None
    assert patch_1 is not None
    assert any("Внезапное нападение: +" in text for text in _line_texts(patch_1))
    assert first_state.combatants["pc_1"].surprise_attack_used is True

    end_combat(session_id)

    assert get_combat(session_id) is None
    assert first_state.combatants["pc_1"].surprise_attack_used is False
    assert first_state.combatants["pc_1"].turns_taken == 0
    assert first_state.combatants["enemy_1"].turns_taken == 0

    _build_bugbear_state(session_id)
    battle_two_rolls = iter([15, 4, 2, 6])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(battle_two_rolls))

    try:
        patch_2, err_2 = handle_live_combat_action("combat_attack", session_id)
        assert err_2 is None
        assert patch_2 is not None
        assert any("Внезапное нападение: +" in text for text in _line_texts(patch_2))
        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_1"].surprise_attack_used is True
    finally:
        end_combat(session_id)


def test_start_combat_cleans_stale_bugbear_surprise_attack_flags() -> None:
    session_id = "test_start_combat_cleans_stale_bugbear_surprise_attack_flags"
    _build_bugbear_state(session_id)
    stale_state = get_combat(session_id)
    assert stale_state is not None
    stale_state.combatants["pc_1"].surprise_attack_used = True
    stale_state.combatants["pc_1"].turns_taken = 2
    stale_state.combatants["enemy_1"].turns_taken = 1

    new_state = start_combat(session_id, reason="fresh_battle")

    try:
        assert new_state is not stale_state
        assert stale_state.combatants["pc_1"].surprise_attack_used is False
        assert stale_state.combatants["pc_1"].turns_taken == 0
        assert stale_state.combatants["enemy_1"].turns_taken == 0
        assert new_state.round_no == 1
        assert new_state.turn_index == 0
        assert new_state.combatants == {}
    finally:
        end_combat(session_id)
