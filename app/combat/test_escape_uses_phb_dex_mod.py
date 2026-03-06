from __future__ import annotations

from app.combat import live_actions
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def test_combat_escape_uses_phb_dex_mod_and_fails(monkeypatch) -> None:
    session_id = "test_combat_escape_uses_phb_dex_mod_and_fails"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Беглец",
        side="pc",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=20,
        stats={"dex": 70},
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Гоблин",
        side="enemy",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    monkeypatch.setattr("app.combat.live_actions.roll_check", lambda _mode: (10, None, 10))

    original_handle = live_actions.handle_live_combat_action

    def _patched_handle(action: str, sid: str):
        if action == "combat_attack":
            return (
                {
                    "status": "⚔ Бой",
                    "open": True,
                    "lines": [{"text": "Реакция врага"}],
                },
                None,
            )
        return original_handle(action, sid)

    monkeypatch.setattr("app.combat.live_actions.handle_live_combat_action", _patched_handle)

    try:
        patch, err = live_actions.handle_live_combat_action("combat_escape", session_id)
        assert err is None
        assert patch is not None
        assert patch["open"] is True

        texts = [line.get("text") for line in patch["lines"] if isinstance(line, dict)]
        assert any("+2" in text and "= 12" in text and "DC 13" in text for text in texts if isinstance(text, str))
        assert any("побег не удался" in text for text in texts if isinstance(text, str))

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.active is True
    finally:
        end_combat(session_id)


def test_combat_stabilize_uses_phb_wis_mod_success(monkeypatch) -> None:
    session_id = "test_combat_stabilize_uses_phb_wis_mod_success"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Лекарь",
        side="pc",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=20,
        stats={"wis": 70},
    )
    state.combatants["pc_2"] = Combatant(
        key="pc_2",
        name="Раненый",
        side="pc",
        hp_current=0,
        hp_max=12,
        ac=12,
        initiative=10,
        is_stable=False,
        is_dead=False,
    )
    state.order = ["pc_1", "pc_2"]
    state.turn_index = 0

    monkeypatch.setattr("app.combat.live_actions.roll_check", lambda _mode: (8, None, 8))

    try:
        patch, err = live_actions.handle_live_combat_action("combat_stabilize", session_id)
        assert err is None
        assert patch is not None

        texts = [line.get("text") for line in patch["lines"] if isinstance(line, dict)]
        assert any("+2" in text and "= 10" in text and "DC 10" in text for text in texts if isinstance(text, str))

        state_now = get_combat(session_id)
        assert state_now is not None
        assert state_now.combatants["pc_2"].is_stable is True
    finally:
        end_combat(session_id)
