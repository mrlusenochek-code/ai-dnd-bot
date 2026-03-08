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


def test_changeling_reverts_to_true_form_on_death(monkeypatch) -> None:
    session_id = "test_changeling_reverts_to_true_form_on_death"
    state = start_combat(session_id)
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=20,
        stats={"str": 60},
        inventory=[{"id": "w1", "def": "longsword"}],
        equip={"main_hand": "w1"},
    )
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Changeling",
        side="pc",
        hp_current=1,
        hp_max=1,
        ac=10,
        initiative=10,
        race_features={
            "features": {"shapechanger": {"action": True, "revert_on_death": True}},
            "runtime": {
                "shapechanger": {
                    "active": True,
                    "persona": "городской страж",
                    "voice": "",
                    "changed_at_iso": "2026-03-09T00:00:00+00:00",
                }
            },
        },
    )
    state.combatants["pc_2"] = Combatant(
        key="pc_2",
        name="Ally",
        side="pc",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=5,
    )
    state.order = ["enemy_1", "pc_1", "pc_2"]
    state.turn_index = 0

    rolls = iter([15, 8])  # attack d20, longsword d8 => instant death for hp 1/1
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None
        assert patch is not None
        texts = _line_texts(patch)
        assert any("Перевёртыш: смерть — возвращение в истинную форму." in t for t in texts)

        state_now = get_combat(session_id)
        assert state_now is not None
        runtime = ((state_now.combatants["pc_1"].race_features or {}).get("runtime") or {})
        shape = runtime.get("shapechanger") or {}
        assert shape.get("active") is False
    finally:
        end_combat(session_id)
