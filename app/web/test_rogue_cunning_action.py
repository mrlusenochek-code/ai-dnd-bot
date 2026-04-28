from __future__ import annotations

from types import SimpleNamespace

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
from app.rules.character_catalog import CLASS_CATALOG
from app.web.ws_class_features import apply_combat_class_feature_action
from app.web.ws_gameplay import _detect_chat_combat_action


def _rogue_cunning_action_mechanics() -> dict:
    rogue = next((item for item in CLASS_CATALOG if str(item.get("key") or "") == "rogue"), None)
    assert rogue is not None
    features = (rogue.get("features_by_level") or {}).get(2) or []
    cunning_action = next((item for item in features if str((item or {}).get("key") or "") == "cunning_action"), None)
    assert isinstance(cunning_action, dict)
    mechanics = cunning_action.get("mechanics") or {}
    assert isinstance(mechanics, dict)
    return mechanics


def _rogue_character() -> SimpleNamespace:
    return SimpleNamespace(
        name="Rogue",
        class_features={
            "features": [
                {
                    "key": "cunning_action",
                    "name_ru": "Хитрое действие",
                    "mechanics": _rogue_cunning_action_mechanics(),
                }
            ],
            "runtime": {},
        },
    )


def _fighter_like_character() -> SimpleNamespace:
    return SimpleNamespace(
        name="Fighter",
        class_features={
            "features": [],
            "runtime": {},
        },
    )


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    return [str(item.get("text") or "") for item in lines if isinstance(item, dict)]


def _start_basic_combat(session_id: str, *, action_available: bool = True, bonus_action_available: bool = True):
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Rogue",
        side="pc",
        hp_current=18,
        hp_max=18,
        ac=15,
        initiative=18,
        action_available=action_available,
        bonus_action_available=bonus_action_available,
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
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0
    return state


def test_detect_cunning_action_phrases_as_combat_actions() -> None:
    assert _detect_chat_combat_action("хитрым действием рывок") == "combat_cunning_dash"
    assert _detect_chat_combat_action("бонусным действием прячусь") == "combat_cunning_hide"
    assert _detect_chat_combat_action("рывок") == "combat_dash"


def test_rogue_cunning_dash_spends_bonus_action_but_not_action() -> None:
    session_id = "test_rogue_cunning_dash_spends_bonus_action_but_not_action"
    ch = _rogue_character()
    _start_basic_combat(session_id)
    try:
        patch, err, changed = apply_combat_class_feature_action("combat_cunning_dash", session_id, "pc_1", ch)
        assert err is None
        assert patch is not None
        assert changed is False

        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        assert actor.action_available is True
        assert actor.bonus_action_available is False
        assert actor.dash_active is True
        assert any("Хитрое действие" in text for text in _line_texts(patch))
    finally:
        end_combat(session_id)


def test_regular_combat_dash_still_spends_action() -> None:
    session_id = "test_regular_combat_dash_still_spends_action"
    _start_basic_combat(session_id)
    try:
        patch, err = handle_live_combat_action("combat_dash", session_id)
        assert err is None
        assert patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        assert actor.action_available is False
        assert actor.bonus_action_available is True
        assert actor.dash_active is True
    finally:
        end_combat(session_id)


def test_cunning_action_blocks_when_bonus_action_is_spent() -> None:
    session_id = "test_cunning_action_blocks_when_bonus_action_is_spent"
    ch = _rogue_character()
    _start_basic_combat(session_id, bonus_action_available=False)
    try:
        patch, err, changed = apply_combat_class_feature_action("combat_cunning_dash", session_id, "pc_1", ch)
        assert patch is None
        assert err == "Бонусное действие недоступно: бонусное действие уже потрачено."
        assert changed is False
    finally:
        end_combat(session_id)


def test_cunning_action_requires_rogue_feature() -> None:
    session_id = "test_cunning_action_requires_rogue_feature"
    ch = _fighter_like_character()
    _start_basic_combat(session_id)
    try:
        patch, err, changed = apply_combat_class_feature_action("combat_cunning_dash", session_id, "pc_1", ch)
        assert patch is None
        assert err == "Хитрое действие недоступно вашему классу."
        assert changed is False
    finally:
        end_combat(session_id)


def test_cunning_hide_and_disengage_route_through_class_feature_router() -> None:
    hide_session = "test_cunning_hide_routes_through_class_feature_router"
    disengage_session = "test_cunning_disengage_routes_through_class_feature_router"
    ch_hide = _rogue_character()
    ch_disengage = _rogue_character()

    _start_basic_combat(hide_session)
    _start_basic_combat(disengage_session)
    try:
        hide_patch, hide_err, hide_changed = apply_combat_class_feature_action("combat_cunning_hide", hide_session, "pc_1", ch_hide)
        assert hide_err is None
        assert hide_patch is not None
        assert hide_changed is False
        hide_lines = _line_texts(hide_patch)
        assert any("прячется" in text.lower() for text in hide_lines)
        hide_state = get_combat(hide_session)
        assert hide_state is not None
        hide_actor = hide_state.combatants["pc_1"]
        assert hide_actor.action_available is True
        assert hide_actor.bonus_action_available is False

        disengage_patch, disengage_err, disengage_changed = apply_combat_class_feature_action(
            "combat_cunning_disengage",
            disengage_session,
            "pc_1",
            ch_disengage,
        )
        assert disengage_err is None
        assert disengage_patch is not None
        assert disengage_changed is False
        disengage_lines = _line_texts(disengage_patch)
        assert any("Отход" in text for text in disengage_lines)
        disengage_state = get_combat(disengage_session)
        assert disengage_state is not None
        disengage_actor = disengage_state.combatants["pc_1"]
        assert disengage_actor.action_available is True
        assert disengage_actor.bonus_action_available is False
        assert disengage_state.turn_index == 1
    finally:
        end_combat(hide_session)
        end_combat(disengage_session)
