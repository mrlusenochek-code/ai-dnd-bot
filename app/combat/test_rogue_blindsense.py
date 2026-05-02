from __future__ import annotations

from app.combat.live_actions import (
    _blindsense_detected_opponents,
    _blindsense_distance_ft,
    _is_hidden_or_invisible_for_blindsense,
    handle_live_combat_action,
)
from app.combat.state import Combatant, end_combat, start_combat
from app.combat.state import get_combat


def _rogue_blindsense_features() -> dict:
    return {
        "features": [
            {
                "key": "blindsense",
                "mechanics": {
                    "type": "blindsense",
                    "range_ft": 10,
                    "detects": ["hidden", "invisible"],
                    "requires_hearing": True,
                },
            }
        ],
        "runtime": {},
    }


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


def _build_state(session_id: str) -> tuple[Combatant, Combatant]:
    state = start_combat(session_id)
    rogue = Combatant(
        key="pc_1",
        name="Плут",
        side="pc",
        hp_current=30,
        hp_max=30,
        ac=15,
        initiative=20,
        level=14,
        class_features=_rogue_blindsense_features(),
    )
    enemy = Combatant(
        key="enemy_1",
        name="Скрытый враг",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
        race_features={"runtime": {}},
    )
    rogue.combat_position = {"node_id": "room_a", "x_ft": 0, "y_ft": 0}
    enemy.combat_position = {"node_id": "room_a", "x_ft": 5, "y_ft": 0}
    state.combatants["pc_1"] = rogue
    state.combatants["enemy_1"] = enemy
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0
    state.round_no = 1
    return rogue, enemy


def test_blindsense_detects_hidden_step_enemy_within_10ft_same_node() -> None:
    session_id = "test_blindsense_detects_hidden_step_enemy_within_10ft_same_node"
    rogue, enemy = _build_state(session_id)
    enemy.race_features = {"runtime": {"hidden_step": {"active": True}}}

    try:
        assert _is_hidden_or_invisible_for_blindsense(enemy) is True
        detected = _blindsense_detected_opponents(get_combat(session_id), rogue)
        assert [actor.key for actor in detected] == ["enemy_1"]
    finally:
        end_combat(session_id)


def test_blindsense_detects_nimble_escape_hide_enemy_within_10ft() -> None:
    session_id = "test_blindsense_detects_nimble_escape_hide_enemy_within_10ft"
    rogue, enemy = _build_state(session_id)
    enemy.race_features = {"runtime": {"nimble_escape_hide": {"active": True}}}

    try:
        detected = _blindsense_detected_opponents(get_combat(session_id), rogue)
        assert [actor.key for actor in detected] == ["enemy_1"]
    finally:
        end_combat(session_id)


def test_blindsense_does_not_detect_beyond_10ft() -> None:
    session_id = "test_blindsense_does_not_detect_beyond_10ft"
    rogue, enemy = _build_state(session_id)
    enemy.race_features = {"runtime": {"hidden_step": {"active": True}}}
    enemy.combat_position = {"node_id": "room_a", "x_ft": 11, "y_ft": 0}

    try:
        assert _blindsense_distance_ft(rogue, enemy) == 11.0
        assert _blindsense_detected_opponents(get_combat(session_id), rogue) == []
    finally:
        end_combat(session_id)


def test_blindsense_does_not_detect_on_different_node() -> None:
    session_id = "test_blindsense_does_not_detect_on_different_node"
    rogue, enemy = _build_state(session_id)
    enemy.race_features = {"runtime": {"hidden_step": {"active": True}}}
    enemy.combat_position = {"node_id": "room_b", "x_ft": 5, "y_ft": 0}

    try:
        assert _blindsense_distance_ft(rogue, enemy) is None
        assert _blindsense_detected_opponents(get_combat(session_id), rogue) == []
    finally:
        end_combat(session_id)


def test_blindsense_does_not_detect_without_coordinates() -> None:
    session_id = "test_blindsense_does_not_detect_without_coordinates"
    rogue, enemy = _build_state(session_id)
    enemy.race_features = {"runtime": {"hidden_step": {"active": True}}}
    enemy.combat_position = {"node_id": "room_a"}

    try:
        assert _blindsense_distance_ft(rogue, enemy) is None
        assert _blindsense_detected_opponents(get_combat(session_id), rogue) == []
    finally:
        end_combat(session_id)


def test_blindsense_does_not_detect_non_hidden_enemy() -> None:
    session_id = "test_blindsense_does_not_detect_non_hidden_enemy"
    rogue, _enemy = _build_state(session_id)

    try:
        assert _blindsense_detected_opponents(get_combat(session_id), rogue) == []
    finally:
        end_combat(session_id)


def test_blindsense_notice_appears_once_per_turn_without_spam() -> None:
    session_id = "test_blindsense_notice_appears_once_per_turn_without_spam"
    _rogue, enemy = _build_state(session_id)
    enemy.race_features = {"runtime": {"hidden_step": {"active": True}}}

    try:
        patch_1, err_1 = handle_live_combat_action("combat_move", session_id, distance_ft=5)
        assert err_1 is None
        assert patch_1 is not None
        texts_1 = _line_texts(patch_1)
        assert sum(1 for text in texts_1 if "Слепое чутьё:" in text) == 1

        patch_2, err_2 = handle_live_combat_action("combat_move", session_id, distance_ft=5)
        assert err_2 is None
        assert patch_2 is not None
        texts_2 = _line_texts(patch_2)
        assert sum(1 for text in texts_2 if "Слепое чутьё:" in text) == 0
    finally:
        end_combat(session_id)
