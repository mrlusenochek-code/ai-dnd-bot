from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.web import session_state


def test_set_player_map_position_stores_structured_and_legacy_label() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})

    session_state._set_player_map_position(
        sess,
        player_id,
        {
            "map_level": "district",
            "node_type": "landmark",
            "node_id": "old-tavern-cellar",
            "label": "Старый подвал",
        },
    )

    assert sess.settings["map_positions"][str(player_id)] == {
        "v": 1,
        "map_level": "district",
        "node_type": "landmark",
        "node_id": "old-tavern-cellar",
        "label": "Старый подвал",
    }
    assert sess.settings["pc_positions"][str(player_id)] == "Старый подвал"


def test_get_pc_positions_prefers_structured_map_positions() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(
        settings={
            "pc_positions": {str(player_id): "Устаревшая зона"},
            "map_positions": {
                str(player_id): {
                    "map_level": "region",
                    "node_type": "zone",
                    "node_id": "north-gate",
                    "label": "Северные ворота",
                }
            },
        }
    )

    assert session_state._get_pc_positions(sess) == {str(player_id): "Северные ворота"}


def test_map_position_identity_equals_ignores_label_mismatch() -> None:
    left = {
        "map_level": "district",
        "node_type": "landmark",
        "node_id": "old-tavern-cellar",
        "label": "Старый подвал",
    }
    right = {
        "map_level": "district",
        "node_type": "landmark",
        "node_id": "old-tavern-cellar",
        "label": "Подвал таверны",
    }

    assert session_state._map_position_identity_equals(left, right) is True


def test_map_position_identity_equals_detects_different_node() -> None:
    left = {
        "map_level": "district",
        "node_type": "landmark",
        "node_id": "old-tavern-cellar",
        "label": "Старый подвал",
    }
    right = {
        "map_level": "district",
        "node_type": "landmark",
        "node_id": "north-gate",
        "label": "Северные ворота",
    }

    assert session_state._map_position_identity_equals(left, right) is False


def test_same_player_map_position_falls_back_to_legacy_when_structured_absent() -> None:
    left_id = uuid.uuid4()
    right_id = uuid.uuid4()
    sess = SimpleNamespace(
        settings={
            "pc_positions": {
                str(left_id): "Таверна",
                str(right_id): "Таверна",
            }
        }
    )

    assert session_state._same_player_map_position(sess, left_id, right_id) is True


def test_same_player_map_position_legacy_fallback_does_not_read_pc_positions_helper(monkeypatch) -> None:
    left_id = uuid.uuid4()
    right_id = uuid.uuid4()
    sess = SimpleNamespace(
        settings={
            "pc_positions": {
                str(left_id): "Таверна",
                str(right_id): "Таверна",
            }
        }
    )

    def _unexpected_read(_sess) -> dict[str, str]:
        raise AssertionError("_get_pc_positions should not be used by same-position fallback")

    monkeypatch.setattr(session_state, "_get_pc_positions", _unexpected_read)

    assert session_state._same_player_map_position(sess, left_id, right_id) is True


def test_get_player_position_context_prefers_structured_and_exposes_zone_label() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(
        settings={
            "pc_positions": {str(player_id): "Устаревшая зона"},
            "map_positions": {
                str(player_id): {
                    "map_level": "district",
                    "node_type": "landmark",
                    "node_id": "old-tavern-cellar",
                    "label": "Старый подвал",
                }
            },
        }
    )

    assert session_state._get_player_position_context(sess, player_id) == {
        "zone_label": "Старый подвал",
        "map_position": {
            "v": 1,
            "map_level": "district",
            "node_type": "landmark",
            "node_id": "old-tavern-cellar",
            "label": "Старый подвал",
        },
    }


def test_get_player_position_context_falls_back_to_legacy_zone() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={"pc_positions": {str(player_id): "Таверна"}})

    assert session_state._get_player_position_context(sess, player_id) == {
        "zone_label": "Таверна",
        "map_position": None,
    }


def test_clear_player_map_position_removes_structured_and_legacy_entries() -> None:
    player_id = uuid.uuid4()
    other_id = uuid.uuid4()
    sess = SimpleNamespace(
        settings={
            "pc_positions": {
                str(player_id): "Старый подвал",
                str(other_id): "Рынок",
            },
            "map_positions": {
                str(player_id): {
                    "map_level": "district",
                    "node_type": "landmark",
                    "node_id": "old-tavern-cellar",
                    "label": "Старый подвал",
                },
                str(other_id): {
                    "map_level": "region",
                    "node_type": "zone",
                    "node_id": "market",
                    "label": "Рынок",
                },
            },
        }
    )

    session_state._clear_player_map_position(sess, player_id)

    assert str(player_id) not in sess.settings["pc_positions"]
    assert str(player_id) not in sess.settings["map_positions"]
    assert str(other_id) in sess.settings["pc_positions"]
    assert str(other_id) in sess.settings["map_positions"]
