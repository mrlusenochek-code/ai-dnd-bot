from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
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


def test_halfling_lucky_rerolls_one_on_attack_into_hit(monkeypatch) -> None:
    session_id = "test_halfling_lucky_rerolls_one_on_attack_into_hit"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Полурослик",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=20,
        stats={"str": 50, "dex": 50},
        inventory=[{"id": "w1", "def": "dagger"}],
        equip={"main_hand": "w1"},
        race_features={
            "features": {
                "reroll_ones": {
                    "scope": ["attack", "check", "save"],
                }
            }
        },
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Цель",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=10,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    rolls = iter((1, 20, 5))
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("критическое попадание" in t.lower() or "попадание" in t.lower() for t in texts)

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["enemy_1"].hp_current < 20
    finally:
        end_combat(session_id)
