from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.web import session_state, ws_handlers


def test_parse_group_command_supports_wait_camp_move_enter_stop_split_and_merge() -> None:
    scout_id = str(uuid.uuid4())
    action_wait, payload_wait = ws_handlers._parse_group_command("group wait: держим позицию")
    action_camp, payload_camp = ws_handlers._parse_group_command("group camp ночлег у костра")
    action_move, payload_move = ws_handlers._parse_group_command("group move к воротам")
    action_enter, payload_enter = ws_handlers._parse_group_command("group enter замок")
    action_stop, payload_stop = ws_handlers._parse_group_command("group stop")
    action_split, payload_split = ws_handlers._parse_group_command(f"group split {scout_id} as scout")
    action_merge, payload_merge = ws_handlers._parse_group_command("group merge scout into main")

    assert (action_wait, payload_wait) == ("group_wait", {"reason": "держим позицию"})
    assert (action_camp, payload_camp) == ("group_camp", {"reason": "ночлег у костра"})
    assert (action_move, payload_move) == ("group_move", {"target_hint": "к воротам"})
    assert (action_enter, payload_enter) == ("group_enter", {"target_hint": "замок"})
    assert (action_stop, payload_stop) == ("group_stop", {})
    assert (action_split, payload_split) == (
        "group_split",
        {"member_player_ids": [scout_id], "new_group_id": "scout"},
    )
    assert (action_merge, payload_merge) == (
        "group_merge",
        {"source_group_id": "scout", "target_group_id": "main"},
    )


def test_handle_group_wait_request_sets_waiting_state() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "Таверна")

    handled, err, msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_wait",
        actor_player_id=player_id,
        payload={"reason": "ждём отстающих"},
        source="test",
    )

    assert handled is True
    assert err is None
    assert msg == "Группа main ждёт: ждём отстающих."
    assert session_state._get_group_states(sess)["main"]["wait_state"] == {
        "reason": "ждём отстающих",
        "source": "test",
        "requested_by": str(player_id),
    }


def test_handle_group_move_enter_and_stop_requests_update_group_state() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "центр города")

    handled_move, err_move, msg_move = ws_handlers._handle_group_action_request(
        sess,
        action="group_move",
        actor_player_id=player_id,
        payload={"target_hint": "к воротам"},
        source="test",
    )

    assert handled_move is True
    assert err_move is None
    assert msg_move == "Группа main движется к ворота."
    moved_group = session_state._get_group_states(sess)["main"]
    assert moved_group["status"] == "moving_intent"
    assert moved_group["current_map_position"] == {
        "v": 1,
        "map_level": "landmark",
        "node_type": "landmark",
        "node_id": "ворота",
        "label": "ворота",
        "area_label": "центр города",
    }
    assert moved_group["movement_intent"]["target_node_type"] == "landmark"

    handled_enter, err_enter, msg_enter = ws_handlers._handle_group_action_request(
        sess,
        action="group_enter",
        actor_player_id=player_id,
        payload={"target_hint": "замок"},
        source="test",
    )

    assert handled_enter is True
    assert err_enter is None
    assert msg_enter == "Группа main входит в замок."
    entered_group = session_state._get_group_states(sess)["main"]
    assert entered_group["current_map_position"] == {
        "v": 1,
        "map_level": "interior",
        "node_type": "interior_entry",
        "node_id": "замок",
        "label": "замок",
        "area_label": "центр города",
    }
    assert entered_group["movement_intent"]["target_node_id"] == "замок"

    handled_stop, err_stop, msg_stop = ws_handlers._handle_group_action_request(
        sess,
        action="group_stop",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_stop is True
    assert err_stop is None
    assert msg_stop == "Группа main остановилась."
    stopped_group = session_state._get_group_states(sess)["main"]
    assert stopped_group["status"] == "idle"
    assert "movement_intent" not in stopped_group


def test_handle_group_split_and_merge_requests_update_group_state() -> None:
    left_id = uuid.uuid4()
    right_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [left_id, right_id], "Таверна")

    handled_split, err_split, msg_split = ws_handlers._handle_group_action_request(
        sess,
        action="group_split",
        actor_player_id=left_id,
        payload={"member_player_ids": [str(right_id)], "new_group_id": "scout"},
        source="test",
    )

    assert handled_split is True
    assert err_split is None
    assert msg_split == "Группа main разделена. Новая группа: scout."
    assert session_state._get_player_group_id(sess, right_id) == "scout"

    handled_merge, err_merge, msg_merge = ws_handlers._handle_group_action_request(
        sess,
        action="group_merge",
        actor_player_id=left_id,
        payload={"source_group_id": "scout", "target_group_id": "main"},
        source="test",
    )

    assert handled_merge is True
    assert err_merge is None
    assert msg_merge == "Группы scout и main объединены."
    assert session_state._get_group_states(sess) == {
        "main": {
            "group_id": "main",
            "player_ids": [str(left_id), str(right_id)],
            "current_map_position": {
                "v": 1,
                "map_level": "region",
                "node_type": "zone",
                "node_id": "Таверна",
                "label": "Таверна",
            },
            "area_label": "Таверна",
            "status": "idle",
        }
    }
