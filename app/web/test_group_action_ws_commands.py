from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.web import session_state, ws_handlers


def test_parse_group_command_supports_wait_camp_move_enter_stop_arrive_interrupt_pause_resume_resolution_split_and_merge() -> None:
    scout_id = str(uuid.uuid4())
    action_wait, payload_wait = ws_handlers._parse_group_command("group wait: держим позицию")
    action_camp, payload_camp = ws_handlers._parse_group_command("group camp ночлег у костра")
    action_move, payload_move = ws_handlers._parse_group_command("group move к воротам")
    action_enter, payload_enter = ws_handlers._parse_group_command("group enter замок")
    action_mode, payload_mode = ws_handlers._parse_group_command("group mode cautious")
    action_activity, payload_activity = ws_handlers._parse_group_command("group activity navigate")
    action_clear_activity, payload_clear_activity = ws_handlers._parse_group_command("group clear activity")
    action_arrive, payload_arrive = ws_handlers._parse_group_command("group arrive")
    action_interrupt, payload_interrupt = ws_handlers._parse_group_command("group interrupt")
    action_pause, payload_pause = ws_handlers._parse_group_command("group pause")
    action_resume, payload_resume = ws_handlers._parse_group_command("group resume")
    action_confirm_enter, payload_confirm_enter = ws_handlers._parse_group_command("group confirm enter")
    action_inspect, payload_inspect = ws_handlers._parse_group_command("group inspect")
    action_bypass, payload_bypass = ws_handlers._parse_group_command("group bypass")
    action_resolve, payload_resolve = ws_handlers._parse_group_command("group resolve")
    action_stop, payload_stop = ws_handlers._parse_group_command("group stop")
    action_split, payload_split = ws_handlers._parse_group_command(f"group split {scout_id} as scout")
    action_merge, payload_merge = ws_handlers._parse_group_command("group merge scout into main")

    assert (action_wait, payload_wait) == ("group_wait", {"reason": "держим позицию"})
    assert (action_camp, payload_camp) == ("group_camp", {"reason": "ночлег у костра"})
    assert (action_move, payload_move) == ("group_move", {"target_hint": "к воротам"})
    assert (action_enter, payload_enter) == ("group_enter", {"target_hint": "замок"})
    assert (action_mode, payload_mode) == ("group_set_mode", {"movement_mode": "cautious"})
    assert (action_activity, payload_activity) == ("group_set_activity", {"activity": "navigate"})
    assert (action_clear_activity, payload_clear_activity) == ("group_clear_activity", {})
    assert (action_arrive, payload_arrive) == ("group_arrive", {})
    assert (action_interrupt, payload_interrupt) == ("group_interrupt", {})
    assert (action_pause, payload_pause) == ("group_pause", {})
    assert (action_resume, payload_resume) == ("group_resume", {})
    assert (action_confirm_enter, payload_confirm_enter) == ("group_confirm_enter", {})
    assert (action_inspect, payload_inspect) == ("group_inspect_target", {})
    assert (action_bypass, payload_bypass) == ("group_bypass", {})
    assert (action_resolve, payload_resolve) == ("group_resolve_pause", {})
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


def test_handle_group_move_pause_resume_enter_arrive_interrupt_and_stop_requests_update_group_state() -> None:
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
    assert moved_group["status"] == "moving"
    assert moved_group["current_map_position"] == {
        "v": 1,
        "map_level": "region",
        "node_type": "zone",
        "node_id": "центр города",
        "label": "центр города",
    }
    assert moved_group["movement_intent"]["target_node_type"] == "landmark"
    assert moved_group["movement_intent"]["route_kind"] == "landmark_move"
    assert moved_group["movement_intent"]["action_kind"] == "move"
    assert moved_group["movement_intent"]["allowed"] is True
    assert moved_group["travel_state"]["active"] is True
    assert moved_group["travel_state"]["route_summary"]["next_map_position"] == {
        "v": 1,
        "map_level": "landmark",
        "node_type": "landmark",
        "node_id": "ворота",
        "label": "ворота",
        "area_label": "центр города",
    }
    assert moved_group["travel_state"]["paused"] is False
    assert moved_group["travel_state"]["resume_allowed"] is True

    handled_pause, err_pause, msg_pause = ws_handlers._handle_group_action_request(
        sess,
        action="group_pause",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_pause is True
    assert err_pause is None
    assert msg_pause == "Путешествие группы main приостановлено."
    paused_group = session_state._get_group_states(sess)["main"]
    assert paused_group["status"] == "paused_travel"
    assert paused_group["travel_state"]["paused"] is True
    assert paused_group["travel_state"]["pause_reason"] == "manual"
    assert paused_group["travel_state"]["pause_details"] == {"source": "test"}

    handled_resume, err_resume, msg_resume = ws_handlers._handle_group_action_request(
        sess,
        action="group_resume",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_resume is True
    assert err_resume is None
    assert msg_resume == "Группа main продолжает путь."
    resumed_group = session_state._get_group_states(sess)["main"]
    assert resumed_group["status"] == "moving"
    assert resumed_group["travel_state"]["paused"] is False
    assert "pause_reason" not in resumed_group["travel_state"]

    handled_arrive, err_arrive, msg_arrive = ws_handlers._handle_group_action_request(
        sess,
        action="group_arrive",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_arrive is True
    assert err_arrive is None
    assert msg_arrive == "Группа main прибыла в ворота."
    arrived_group = session_state._get_group_states(sess)["main"]
    assert arrived_group["status"] == "idle"
    assert "movement_intent" not in arrived_group
    assert "travel_state" not in arrived_group
    assert arrived_group["current_map_position"] == {
        "v": 1,
        "map_level": "landmark",
        "node_type": "landmark",
        "node_id": "ворота",
        "label": "ворота",
        "area_label": "центр города",
    }

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
    assert entered_group["status"] == "paused_travel"
    assert entered_group["current_map_position"] == {
        "v": 1,
        "map_level": "landmark",
        "node_type": "landmark",
        "node_id": "ворота",
        "label": "ворота",
        "area_label": "центр города",
    }
    assert entered_group["movement_intent"]["target_node_id"] == "замок"
    assert entered_group["movement_intent"]["route_kind"] == "enter_location"
    assert entered_group["movement_intent"]["action_kind"] == "enter"
    assert entered_group["movement_intent"]["allowed"] is True
    assert entered_group["travel_state"]["target_node"]["node_id"] == "замок"
    assert entered_group["travel_state"]["paused"] is True
    assert entered_group["travel_state"]["pause_reason"] == "target_requires_enter"

    blocked_arrive, blocked_arrive_err, blocked_arrive_msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_arrive",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert blocked_arrive is True
    assert blocked_arrive_err == "Путешествие приостановлено: цель требует явного входа. Сначала возобновите движение группы."
    assert blocked_arrive_msg is None

    handled_resume_enter, err_resume_enter, msg_resume_enter = ws_handlers._handle_group_action_request(
        sess,
        action="group_resume",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_resume_enter is True
    assert err_resume_enter is None
    assert msg_resume_enter == "Группа main продолжает путь."

    handled_arrive_enter, err_arrive_enter, msg_arrive_enter = ws_handlers._handle_group_action_request(
        sess,
        action="group_arrive",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_arrive_enter is True
    assert err_arrive_enter is None
    assert msg_arrive_enter == "Группа main прибыла в замок."
    arrived_enter_group = session_state._get_group_states(sess)["main"]
    assert arrived_enter_group["status"] == "idle"
    assert arrived_enter_group["current_map_position"]["node_id"] == "замок"

    session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "zone_move",
            "action_kind": "move",
            "target_label": "площадь",
            "target_node": {
                "map_level": "region",
                "node_type": "zone",
                "node_id": "площадь",
                "label": "площадь",
                "zone_label": "площадь",
                "area_label": "площадь",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "region",
                "node_type": "zone",
                "node_id": "площадь",
                "label": "площадь",
            },
            "next_zone_label": "площадь",
        },
        source="test",
    )

    handled_interrupt, err_interrupt, msg_interrupt = ws_handlers._handle_group_action_request(
        sess,
        action="group_interrupt",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_interrupt is True
    assert err_interrupt is None
    assert msg_interrupt == "Группа main прервала движение."
    interrupted_group = session_state._get_group_states(sess)["main"]
    assert interrupted_group["status"] == "idle"
    assert "movement_intent" not in interrupted_group
    assert "travel_state" not in interrupted_group
    assert interrupted_group["current_map_position"] == {
        "v": 1,
        "map_level": "interior",
        "node_type": "interior_entry",
        "node_id": "замок",
        "label": "замок",
        "area_label": "центр города",
    }

    session_state.set_group_movement_intent(sess, "main", target_node="площадь", source="test")

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


def test_handle_group_mode_and_activity_requests_update_group_state() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "центр города")

    handled_mode, err_mode, msg_mode = ws_handlers._handle_group_action_request(
        sess,
        action="group_set_mode",
        actor_player_id=player_id,
        payload={"movement_mode": "fast"},
        source="test",
    )

    assert handled_mode is True
    assert err_mode is None
    assert msg_mode == "Режим движения группы main: fast."
    assert session_state.get_group_movement_mode(sess, "main") == "fast"

    handled_activity, err_activity, msg_activity = ws_handlers._handle_group_action_request(
        sess,
        action="group_set_activity",
        actor_player_id=player_id,
        payload={"activity": "observe"},
        source="test",
    )

    assert handled_activity is True
    assert err_activity is None
    assert msg_activity == "Походная активность группы main: observe."
    assert session_state.get_group_travel_activity(sess, "main") == {
        "activity": "observe",
        "assigned_actor_id": str(player_id),
        "source": "test",
    }

    handled_clear, err_clear, msg_clear = ws_handlers._handle_group_action_request(
        sess,
        action="group_clear_activity",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_clear is True
    assert err_clear is None
    assert msg_clear == "Походная активность группы main очищена."
    assert session_state.get_group_travel_activity(sess, "main") is None


def test_handle_group_move_uses_route_helper_and_stores_route_summary(monkeypatch) -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "центр города")
    calls: list[tuple[str, str]] = []

    def fake_resolve(**kwargs):
        calls.append(("resolve", str(kwargs.get("action_kind") or "")))
        return {
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "ворота",
            "label": "ворота",
            "zone_label": "центр города",
            "area_label": "центр города",
        }

    def fake_route(**kwargs):
        calls.append(("route", str(kwargs.get("action_kind") or "")))
        return {
            "allowed": True,
            "route_kind": "landmark_move",
            "action_kind": "move",
            "target_node": {
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "ворота",
                "label": "ворота",
                "zone_label": "центр города",
                "area_label": "центр города",
            },
            "target_node_type": "landmark",
            "target_node_id": "ворота",
            "target_label": "ворота",
            "next_map_position": {
                "v": 1,
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "ворота",
                "label": "ворота",
                "area_label": "центр города",
            },
            "next_zone_label": "центр города",
            "error": None,
        }

    monkeypatch.setattr(ws_handlers, "resolve_action_target_node", fake_resolve)
    monkeypatch.setattr(ws_handlers, "resolve_group_target_route", fake_route)

    handled, err, msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_move",
        actor_player_id=player_id,
        payload={"target_hint": "к воротам"},
        source="test",
    )

    assert handled is True
    assert err is None
    assert msg == "Группа main движется к ворота."
    assert calls == [("resolve", "move"), ("route", "move")]
    assert session_state._get_group_states(sess)["main"]["movement_intent"]["route_kind"] == "landmark_move"
    assert session_state._get_group_states(sess)["main"]["current_map_position"]["node_id"] == "центр города"


def test_handle_group_resume_without_paused_travel_returns_clear_error() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "центр города")

    handled, err, msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_resume",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled is True
    assert err == "У группы нет приостановленного путешествия для возобновления."
    assert msg is None


def test_handle_group_confirm_enter_inspect_bypass_and_resolve_pause_commands() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "центр города")

    session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "enter_location",
            "action_kind": "enter",
            "target_label": "замок",
            "target_node": {
                "map_level": "interior",
                "node_type": "interior_entry",
                "node_id": "замок",
                "label": "замок",
                "zone_label": "центр города",
                "area_label": "центр города",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "interior",
                "node_type": "interior_entry",
                "node_id": "замок",
                "label": "замок",
                "area_label": "центр города",
            },
            "next_zone_label": "центр города",
        },
        source="test",
    )

    handled_confirm, err_confirm, msg_confirm = ws_handlers._handle_group_action_request(
        sess,
        action="group_confirm_enter",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_confirm is True
    assert err_confirm is None
    assert msg_confirm == "Группа main подтверждает вход в замок."
    confirmed_group = session_state._get_group_states(sess)["main"]
    assert confirmed_group["status"] == "idle"
    assert confirmed_group["current_map_position"]["node_id"] == "замок"
    assert confirmed_group["last_travel_resolution"]["resolution_kind"] == "confirm_enter"

    session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "landmark_move",
            "action_kind": "move",
            "target_label": "ворота",
            "target_node": {
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "ворота",
                "label": "ворота",
                "zone_label": "центр города",
                "area_label": "центр города",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "ворота",
                "label": "ворота",
                "area_label": "центр города",
            },
            "next_zone_label": "центр города",
            "pause_hint": "inspection_required",
        },
        source="test",
    )

    handled_inspect, err_inspect, msg_inspect = ws_handlers._handle_group_action_request(
        sess,
        action="group_inspect_target",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_inspect is True
    assert err_inspect is None
    assert msg_inspect == "Группа main осматривает ворота."
    inspected_group = session_state._get_group_states(sess)["main"]
    assert inspected_group["status"] == "idle"
    assert inspected_group["current_map_position"]["node_id"] == "замок"
    assert inspected_group["last_travel_resolution"]["resolution_kind"] == "inspect_target"

    session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "zone_move",
            "action_kind": "move",
            "target_label": "лесная тропа",
            "target_node": {
                "map_level": "region",
                "node_type": "zone",
                "node_id": "лесная тропа",
                "label": "лесная тропа",
                "zone_label": "лесная тропа",
                "area_label": "лесная тропа",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "region",
                "node_type": "zone",
                "node_id": "лесная тропа",
                "label": "лесная тропа",
            },
            "next_zone_label": "лесная тропа",
        },
        source="test",
    )
    session_state.pause_group_travel(
        sess,
        "main",
        reason="route_blocked",
        pause_details={"blocker": "оползень"},
        resume_allowed=True,
    )

    handled_bypass, err_bypass, msg_bypass = ws_handlers._handle_group_action_request(
        sess,
        action="group_bypass",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_bypass is True
    assert err_bypass is None
    assert msg_bypass == "Группа main обходит препятствие на пути к лесная тропа."
    bypassed_group = session_state._get_group_states(sess)["main"]
    assert bypassed_group["status"] == "idle"
    assert bypassed_group["last_travel_resolution"]["resolution_kind"] == "bypass"

    session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "zone_move",
            "action_kind": "move",
            "target_label": "старая башня",
            "target_node": {
                "map_level": "region",
                "node_type": "zone",
                "node_id": "старая башня",
                "label": "старая башня",
                "zone_label": "старая башня",
                "area_label": "старая башня",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "region",
                "node_type": "zone",
                "node_id": "старая башня",
                "label": "старая башня",
            },
            "next_zone_label": "старая башня",
        },
        source="test",
    )
    session_state.pause_group_travel(
        sess,
        "main",
        reason="event_pending",
        pause_details={"event_id": "poi-1"},
        resume_allowed=True,
    )

    handled_resolve, err_resolve, msg_resolve = ws_handlers._handle_group_action_request(
        sess,
        action="group_resolve_pause",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_resolve is True
    assert err_resolve is None
    assert msg_resolve == "Paused travel группы main разрешён."
    resolved_group = session_state._get_group_states(sess)["main"]
    assert resolved_group["status"] == "moving"
    assert resolved_group["travel_state"]["paused"] is False
    assert resolved_group["last_travel_resolution"]["resolution_kind"] == "resolve_pause"


def test_handle_invalid_pause_resolution_returns_clear_error_without_corrupting_state() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "центр города")
    session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "landmark_move",
            "action_kind": "move",
            "target_label": "ворота",
            "target_node": {
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "ворота",
                "label": "ворота",
                "zone_label": "центр города",
                "area_label": "центр города",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "ворота",
                "label": "ворота",
                "area_label": "центр города",
            },
            "next_zone_label": "центр города",
            "pause_hint": "inspection_required",
        },
        source="test",
    )
    before = session_state._get_group_states(sess)

    handled, err, msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_bypass",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled is True
    assert err == "Нечего обходить: группе нужен paused travel с blocked route."
    assert msg is None
    assert session_state._get_group_states(sess) == before


def test_handle_group_enter_invalid_target_returns_error_without_corrupting_state() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "центр города")
    before = session_state._get_group_states(sess)

    handled, err, msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_enter",
        actor_player_id=player_id,
        payload={
            "target_node": {
                "map_level": "region",
                "node_type": "zone",
                "node_id": "центр города",
                "label": "центр города",
                "zone_label": "центр города",
                "area_label": "центр города",
            }
        },
        source="test",
    )

    assert handled is True
    assert err == "Для `group enter` нужна interior/building цель, а не обычная zone."
    assert msg is None
    assert session_state._get_group_states(sess) == before


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
            "movement_mode": "normal",
        }
    }
