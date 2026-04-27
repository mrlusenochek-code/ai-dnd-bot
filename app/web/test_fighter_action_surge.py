from __future__ import annotations

from types import SimpleNamespace

from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.rules.character_catalog import CLASS_CATALOG
from app.web.ws_class_features import apply_combat_class_feature_action
from app.web.ws_gameplay import _detect_chat_combat_action


def _fighter_action_surge_mechanics() -> dict:
    fighter = next((item for item in CLASS_CATALOG if str(item.get("key") or "") == "fighter"), None)
    assert fighter is not None
    features = (fighter.get("features_by_level") or {}).get(2) or []
    action_surge = next((item for item in features if str((item or {}).get("key") or "") == "action_surge"), None)
    assert isinstance(action_surge, dict)
    mechanics = action_surge.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _fighter_character() -> SimpleNamespace:
    return SimpleNamespace(
        name="Fighter",
        class_features={
            "features": [
                {
                    "key": "action_surge",
                    "name_ru": "Всплеск действий",
                    "mechanics": _fighter_action_surge_mechanics(),
                }
            ],
            "runtime": {},
        },
    )


def test_detect_action_surge_phrases_as_combat_action() -> None:
    assert _detect_chat_combat_action("всплеск действий") == "combat_action_surge"
    assert _detect_chat_combat_action("использую всплеск действий") == "combat_action_surge"
    assert _detect_chat_combat_action("action surge") == "combat_action_surge"


def test_action_surge_router_requires_active_combat() -> None:
    ch = _fighter_character()
    patch, err, changed = apply_combat_class_feature_action("combat_action_surge", "missing_session", "pc_1", ch)
    assert patch is None
    assert err == "Combat is not active"
    assert changed is False


def test_action_surge_router_requires_own_turn_and_grants_action_once() -> None:
    session_id = "test_action_surge_router_requires_own_turn_and_grants_action_once"
    ch = _fighter_character()
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Fighter",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=16,
        initiative=15,
        action_available=False,
        bonus_action_available=False,
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=12,
        hp_max=12,
        ac=12,
        initiative=10,
    )

    try:
        state.order = ["enemy_1", "pc_1"]
        state.turn_index = 0
        patch_wrong, err_wrong, changed_wrong = apply_combat_class_feature_action(
            "combat_action_surge",
            session_id,
            "pc_1",
            ch,
        )
        assert patch_wrong is None
        assert err_wrong is not None
        assert "Дождись своего хода" in err_wrong
        assert changed_wrong is False

        state.order = ["pc_1", "enemy_1"]
        state.turn_index = 0
        patch_ok, err_ok, changed_ok = apply_combat_class_feature_action(
            "combat_action_surge",
            session_id,
            "pc_1",
            ch,
        )
        assert err_ok is None
        assert patch_ok is not None
        assert changed_ok is True

        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        assert actor.action_available is True
        assert actor.bonus_action_available is False
        lines = patch_ok.get("lines") if isinstance(patch_ok, dict) else []
        first_text = ""
        if isinstance(lines, list) and lines and isinstance(lines[0], dict):
            first_text = str(lines[0].get("text") or "")
        assert "Всплеск действий" in first_text

        patch_repeat, err_repeat, changed_repeat = apply_combat_class_feature_action(
            "combat_action_surge",
            session_id,
            "pc_1",
            ch,
        )
        assert patch_repeat is None
        assert err_repeat is not None
        assert "короткого или долгого отдыха" in err_repeat
        assert changed_repeat is False
    finally:
        end_combat(session_id)
