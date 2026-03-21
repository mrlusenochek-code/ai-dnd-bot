from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.web import session_state, ws_handlers


def test_parse_group_command_supports_wait_camp_rest_scout_move_navigate_context_actions_services_enter_stop_arrive_interrupt_pause_resume_event_resolution_split_and_merge() -> None:
    scout_id = str(uuid.uuid4())
    action_wait, payload_wait = ws_handlers._parse_group_command("group wait: держим позицию")
    action_camp_resolve, payload_camp_resolve = ws_handlers._parse_group_command("group camp resolve")
    action_camp, payload_camp = ws_handlers._parse_group_command("group camp ночлег у костра")
    action_rest, payload_rest = ws_handlers._parse_group_command("group rest")
    action_scout, payload_scout = ws_handlers._parse_group_command("group scout")
    action_search, payload_search = ws_handlers._parse_group_command("group search")
    action_move, payload_move = ws_handlers._parse_group_command("group move к воротам")
    action_navigate, payload_navigate = ws_handlers._parse_group_command("group navigate fortress_gate")
    action_go, payload_go = ws_handlers._parse_group_command("group go mine_entrance")
    action_continue, payload_continue = ws_handlers._parse_group_command("group continue")
    action_journey, payload_journey = ws_handlers._parse_group_command("group journey")
    action_do_inspect, payload_do_inspect = ws_handlers._parse_group_command("group do inspect")
    action_do_navigate, payload_do_navigate = ws_handlers._parse_group_command("group action navigate fortress_gate")
    action_do_camp, payload_do_camp = ws_handlers._parse_group_command("group action camp")
    action_service, payload_service = ws_handlers._parse_group_command("group service craft_town:safe_rest")
    action_use_service, payload_use_service = ws_handlers._parse_group_command("group use chapel_village_shrine_aid")
    action_intel, payload_intel = ws_handlers._parse_group_command("group intel")
    action_journal, payload_journal = ws_handlers._parse_group_command("group journal")
    action_leads, payload_leads = ws_handlers._parse_group_command("group leads")
    action_next, payload_next = ws_handlers._parse_group_command("group next")
    action_routes, payload_routes = ws_handlers._parse_group_command("group routes")
    action_path, payload_path = ws_handlers._parse_group_command("group path fortress_gate")
    action_route, payload_route = ws_handlers._parse_group_command("group route fortress_gate")
    action_trail, payload_trail = ws_handlers._parse_group_command("group trail")
    action_visits, payload_visits = ws_handlers._parse_group_command("group visits")
    action_entry, payload_entry = ws_handlers._parse_group_command("group entry")
    action_arrival, payload_arrival = ws_handlers._parse_group_command("group arrival")
    action_local, payload_local = ws_handlers._parse_group_command("group local")
    action_event_read, payload_event_read = ws_handlers._parse_group_command("group event")
    action_options, payload_options = ws_handlers._parse_group_command("group options")
    action_interact, payload_interact = ws_handlers._parse_group_command("group interact")
    action_progress, payload_progress = ws_handlers._parse_group_command("group progress")
    action_place, payload_place = ws_handlers._parse_group_command("group place")
    action_region, payload_region = ws_handlers._parse_group_command("group region")
    action_frontier, payload_frontier = ws_handlers._parse_group_command("group frontier")
    action_exits, payload_exits = ws_handlers._parse_group_command("group exits")
    action_gateways, payload_gateways = ws_handlers._parse_group_command("group gateways")
    action_here, payload_here = ws_handlers._parse_group_command("group here")
    action_regions, payload_regions = ws_handlers._parse_group_command("group regions")
    action_world, payload_world = ws_handlers._parse_group_command("group world")
    action_links, payload_links = ws_handlers._parse_group_command("group links")
    action_crossings, payload_crossings = ws_handlers._parse_group_command("group crossings")
    action_focus, payload_focus = ws_handlers._parse_group_command("group focus")
    action_focus_route, payload_focus_route = ws_handlers._parse_group_command("group focus-route")
    action_focus_path, payload_focus_path = ws_handlers._parse_group_command("group focus-path")
    action_region_pursuit, payload_region_pursuit = ws_handlers._parse_group_command("group region-pursuit")
    action_region_step, payload_region_step = ws_handlers._parse_group_command("group region-step")
    action_continue_region, payload_continue_region = ws_handlers._parse_group_command("group continue-region")
    action_arrival_region, payload_arrival_region = ws_handlers._parse_group_command("group arrival-region")
    action_region_entry, payload_region_entry = ws_handlers._parse_group_command("group region-entry")
    action_exit, payload_exit = ws_handlers._parse_group_command("group exit forest_settlement_northwatch")
    action_cross, payload_cross = ws_handlers._parse_group_command("group cross fortress_gate_western_road")
    action_transition, payload_transition = ws_handlers._parse_group_command("group transition")
    action_route_region, payload_route_region = ws_handlers._parse_group_command("group route-region northwatch_frontier")
    action_region_path, payload_region_path = ws_handlers._parse_group_command("group region-path northwatch_frontier")
    action_route_known_region, payload_route_known_region = ws_handlers._parse_group_command("group route-known-region northwatch_frontier")
    action_known_path, payload_known_path = ws_handlers._parse_group_command("group known-path northwatch_frontier")
    action_pursue_region, payload_pursue_region = ws_handlers._parse_group_command("group pursue-region northwatch_frontier")
    action_stop_region, payload_stop_region = ws_handlers._parse_group_command("group stop-region")
    action_enter, payload_enter = ws_handlers._parse_group_command("group enter замок")
    action_mode, payload_mode = ws_handlers._parse_group_command("group mode cautious")
    action_activity, payload_activity = ws_handlers._parse_group_command("group activity navigate")
    action_clear_activity, payload_clear_activity = ws_handlers._parse_group_command("group clear activity")
    action_event_resolve, payload_event_resolve = ws_handlers._parse_group_command("group event resolve")
    action_event_ignore, payload_event_ignore = ws_handlers._parse_group_command("group event ignore")
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
    assert (action_camp_resolve, payload_camp_resolve) == ("group_camp_resolve", {})
    assert (action_camp, payload_camp) == ("group_camp", {"reason": "ночлег у костра"})
    assert (action_rest, payload_rest) == ("group_rest", {})
    assert (action_scout, payload_scout) == ("group_scout", {})
    assert (action_search, payload_search) == ("group_scout", {})
    assert (action_move, payload_move) == ("group_move", {"target_hint": "к воротам"})
    assert (action_navigate, payload_navigate) == ("group_navigate", {"target_node_id": "fortress_gate"})
    assert (action_go, payload_go) == ("group_journey_set", {"target_node_id": "mine_entrance"})
    assert (action_continue, payload_continue) == ("group_journey_advance", {})
    assert (action_journey, payload_journey) == ("group_journey_status", {})
    assert (action_do_inspect, payload_do_inspect) == ("group_context_action", {"action_key": "inspect", "action_id": "inspect"})
    assert (action_do_navigate, payload_do_navigate) == (
        "group_context_action",
        {"action_key": "navigate", "action_id": "navigate", "target_node_id": "fortress_gate"},
    )
    assert (action_do_camp, payload_do_camp) == ("group_context_action", {"action_key": "camp", "action_id": "camp"})
    assert (action_service, payload_service) == ("group_service_use", {"service_id": "craft_town:safe_rest", "service_key": "craft_town:safe_rest"})
    assert (action_use_service, payload_use_service) == ("group_service_use", {"service_id": "chapel_village_shrine_aid", "service_key": "chapel_village_shrine_aid"})
    assert (action_intel, payload_intel) == ("group_map_intel", {})
    assert (action_journal, payload_journal) == ("group_map_intel", {})
    assert (action_leads, payload_leads) == ("group_exploration_leads", {})
    assert (action_next, payload_next) == ("group_exploration_leads", {})
    assert (action_routes, payload_routes) == ("group_route_planning", {})
    assert (action_path, payload_path) == ("group_route_plan_to", {"target_node_id": "fortress_gate"})
    assert (action_route, payload_route) == ("group_route_plan_to", {"target_node_id": "fortress_gate"})
    assert (action_trail, payload_trail) == ("group_visit_history", {})
    assert (action_visits, payload_visits) == ("group_visit_history", {})
    assert (action_entry, payload_entry) == ("group_node_entry", {})
    assert (action_arrival, payload_arrival) == ("group_node_entry", {})
    assert (action_local, payload_local) == ("group_destination_event", {})
    assert (action_event_read, payload_event_read) == ("group_destination_event", {})
    assert (action_options, payload_options) == ("group_local_interactions", {})
    assert (action_interact, payload_interact) == ("group_local_interactions", {})
    assert (action_progress, payload_progress) == ("group_node_progress", {})
    assert (action_place, payload_place) == ("group_node_progress", {})
    assert (action_region, payload_region) == ("group_region_progress", {})
    assert (action_frontier, payload_frontier) == ("group_region_progress", {})
    assert (action_exits, payload_exits) == ("group_region_gateways", {})
    assert (action_gateways, payload_gateways) == ("group_region_gateways", {})
    assert (action_here, payload_here) == ("group_region_status", {})
    assert (action_regions, payload_regions) == ("group_discovered_regions", {})
    assert (action_world, payload_world) == ("group_region_world", {})
    assert (action_links, payload_links) == ("group_region_links", {})
    assert (action_crossings, payload_crossings) == ("group_gateway_history", {})
    assert (action_focus, payload_focus) == ("group_region_focus", {})
    assert (action_focus_route, payload_focus_route) == ("group_primary_region_route", {})
    assert (action_focus_path, payload_focus_path) == ("group_primary_region_focus_plan", {})
    assert (action_region_pursuit, payload_region_pursuit) == ("group_region_pursuit_status", {})
    assert (action_region_step, payload_region_step) == ("group_region_pursuit_step_status", {})
    assert (action_continue_region, payload_continue_region) == ("group_region_pursuit_advance", {})
    assert (action_arrival_region, payload_arrival_region) == ("group_region_onboarding", {})
    assert (action_region_entry, payload_region_entry) == ("group_region_onboarding", {})
    assert (action_exit, payload_exit) == ("group_region_transition", {"gateway_id": "forest_settlement_northwatch"})
    assert (action_cross, payload_cross) == ("group_region_transition", {"gateway_id": "fortress_gate_western_road"})
    assert (action_transition, payload_transition) == ("group_region_transition_status", {})
    assert (action_route_region, payload_route_region) == ("group_region_target_plan", {"target_region_id": "northwatch_frontier"})
    assert (action_region_path, payload_region_path) == ("group_region_target_plan", {"target_region_id": "northwatch_frontier"})
    assert (action_route_known_region, payload_route_known_region) == ("group_known_region_route", {"target_region_id": "northwatch_frontier"})
    assert (action_known_path, payload_known_path) == ("group_known_region_route", {"target_region_id": "northwatch_frontier"})
    assert (action_pursue_region, payload_pursue_region) == ("group_region_pursuit_set", {"target_region_id": "northwatch_frontier"})
    assert (action_stop_region, payload_stop_region) == ("group_region_pursuit_clear", {})
    assert (action_enter, payload_enter) == ("group_enter", {"target_hint": "замок"})
    assert (action_mode, payload_mode) == ("group_set_mode", {"movement_mode": "cautious"})
    assert (action_activity, payload_activity) == ("group_set_activity", {"activity": "navigate"})
    assert (action_clear_activity, payload_clear_activity) == ("group_clear_activity", {})
    assert (action_event_resolve, payload_event_resolve) == ("group_event_resolve", {})
    assert (action_event_ignore, payload_event_ignore) == ("group_event_ignore", {})
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


def test_handle_group_camp_resolve_request_stores_canonical_result() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "chapel_village",
            "label": "Деревня у часовни",
        },
    )
    session_state.set_group_camp(sess, "main", reason="ночлег", source="test", requested_by=player_id)

    handled, err, msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_camp_resolve",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled is True
    assert err is None
    assert "спокойный отдых" in str(msg)
    resolved_group = session_state._get_group_states(sess)["main"]
    assert resolved_group["status"] == "idle"
    assert "camp_state" not in resolved_group
    assert resolved_group["last_camp_result"]["result_type"] in {"safe_rest", "sheltered_rest"}


def test_handle_group_rest_request_sets_and_resolves_camp() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    handled, err, msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_rest",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled is True
    assert err is None
    assert "передыш" in str(msg) or "отдых" in str(msg)
    resolved_group = session_state._get_group_states(sess)["main"]
    assert resolved_group["status"] == "idle"
    assert resolved_group["last_camp_result"]["result_type"] in {"safe_rest", "roadside_pause", "sheltered_rest"}


def test_handle_group_camp_resolve_without_active_camp_returns_error() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "Таверна")

    handled, err, msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_camp_resolve",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled is True
    assert err == "У группы нет активного лагеря."
    assert msg is None


def test_handle_group_scout_request_stores_canonical_result() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    handled, err, msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_scout",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled is True
    assert err is None
    assert "маршрут" in str(msg) or "развед" in str(msg)
    resolved_group = session_state._get_group_states(sess)["main"]
    assert resolved_group["last_scout_result"]["result_type"] == "route_revealed"
    assert session_state.is_player_node_revealed(sess, player_id, "craft_town") is True


def test_handle_group_search_alias_uses_same_scout_flow() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    handled, err, msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_scout",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled is True
    assert err is None
    assert "маршрут" in str(msg) or "развед" in str(msg)
    assert session_state._get_group_states(sess)["main"]["last_scout_result"]["result_type"] == "route_revealed"


def test_handle_group_local_interactions_and_locked_local_execution() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "craft_town",
            "label": "Озёрный городок",
        },
    )

    handled_surface, err_surface, msg_surface = ws_handlers._handle_group_action_request(
        sess,
        action="group_local_interactions",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    handled_action, err_action, msg_action = ws_handlers._handle_group_action_request(
        sess,
        action="group_context_action",
        actor_player_id=player_id,
        payload={"action_id": "trace_watchtower_bearing", "action_key": "trace_watchtower_bearing"},
        source="test",
    )
    handled_service, err_service, msg_service = ws_handlers._handle_group_action_request(
        sess,
        action="group_service_use",
        actor_player_id=player_id,
        payload={"service_id": "craft_town_local_guidance", "service_key": "craft_town_local_guidance"},
        source="test",
    )

    assert handled_surface is True
    assert err_surface is None
    assert "действий" in str(msg_surface)
    assert handled_action is True
    assert err_action == "Сначала получить береговую наводку при первом прибытии в городок."
    assert msg_action is None
    assert handled_service is True
    assert err_service == "Сначала получить местную наводку при прибытии в городок."
    assert msg_service is None


def test_handle_group_context_action_wait_camp_inspect_and_navigate() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    handled_wait, err_wait, msg_wait = ws_handlers._handle_group_action_request(
        sess,
        action="group_context_action",
        actor_player_id=player_id,
        payload={"action_id": "wait", "reason": "держим точку"},
        source="test",
    )
    assert handled_wait is True
    assert err_wait is None
    assert msg_wait == "Группа main ждёт."

    session_state._clear_group_activity_state(session_state._get_group_states(sess)["main"], status="idle")

    handled_camp, err_camp, msg_camp = ws_handlers._handle_group_action_request(
        sess,
        action="group_context_action",
        actor_player_id=player_id,
        payload={"action_id": "camp", "reason": "ночлег"},
        source="test",
    )
    assert handled_camp is True
    assert err_camp is None
    assert msg_camp == "Группа main разбила лагерь."

    session_state._clear_group_activity_state(session_state._get_group_states(sess)["main"], status="idle")

    handled_inspect, err_inspect, msg_inspect = ws_handlers._handle_group_action_request(
        sess,
        action="group_context_action",
        actor_player_id=player_id,
        payload={"action_id": "inspect"},
        source="test",
    )
    assert handled_inspect is True
    assert err_inspect is None
    assert msg_inspect == "Группа main осматривает Стартовый тракт."

    handled_navigate, err_navigate, msg_navigate = ws_handlers._handle_group_action_request(
        sess,
        action="group_context_action",
        actor_player_id=player_id,
        payload={"action_id": "navigate", "target_node_id": "fortress_gate"},
        source="test",
    )
    assert handled_navigate is True
    assert err_navigate is None
    assert msg_navigate == "Группа main движется к Ворота крепости."


def test_handle_group_context_action_enter_and_errors_cleanly() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "ruined_settlement",
            "label": "Разрушенный посёлок",
        },
    )
    session_state.maybe_apply_group_enter_target(
        sess,
        "main",
        {
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "mine_entrance",
            "label": "Шахтный вход",
            "zone_label": "Разрушенный посёлок",
            "area_label": "Разрушенный посёлок",
        },
        source="test",
    )

    handled_enter, err_enter, msg_enter = ws_handlers._handle_group_action_request(
        sess,
        action="group_context_action",
        actor_player_id=player_id,
        payload={"action_id": "enter"},
        source="test",
    )
    assert handled_enter is True
    assert err_enter is None
    assert msg_enter == "Группа main подтверждает вход в Шахтный вход."

    hint_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        hint_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "craft_town",
            "label": "Озёрный городок",
        },
    )
    hint_handled, hint_err, hint_msg = ws_handlers._handle_group_action_request(
        hint_sess,
        action="group_context_action",
        actor_player_id=player_id,
        payload={"action_id": "rest_hint"},
        source="test",
    )
    invalid_handled, invalid_err, invalid_msg = ws_handlers._handle_group_action_request(
        hint_sess,
        action="group_context_action",
        actor_player_id=player_id,
        payload={"action_id": "unknown_action"},
        source="test",
    )

    navigate_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        navigate_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )
    session_state.grant_player_map_knowledge(navigate_sess, player_id, "watchtower", knowledge_kind="known", source="test")
    unavailable_handled, unavailable_err, unavailable_msg = ws_handlers._handle_group_action_request(
        navigate_sess,
        action="group_context_action",
        actor_player_id=player_id,
        payload={"action_id": "navigate", "target_node_id": "watchtower"},
        source="test",
    )

    assert hint_handled is True
    assert hint_err == "Это contextual действие доступно только как подсказка."
    assert hint_msg is None
    assert invalid_handled is True
    assert invalid_err == "Это contextual действие сейчас недоступно."
    assert invalid_msg is None
    assert unavailable_handled is True
    assert unavailable_err == "Эта navigation цель сейчас недоступна из текущей точки."
    assert unavailable_msg is None


def test_handle_group_context_action_supports_authored_action_and_alias_payload() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.set_group_route_access_state(
        sess,
        "main",
        "forest_road->ruined_settlement:move",
        access_state="blocked",
        summary="Старая дорога завалена.",
        block_reason="fallen_trees",
        source="test",
    )

    handled, err, msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_context_action",
        actor_player_id=player_id,
        payload={"action_id": "clear_old_road"},
        source="test",
    )

    assert handled is True
    assert err is None
    assert "открывает устойчивый проход" in str(msg)
    assert session_state.get_group_route_access_state(sess, "main", "forest_road->ruined_settlement:move")["access_state"] == "cleared"
    assert session_state.get_group_node_state(sess, "main", "forest_road")["state_flags"] == ["old_road_cleared"]


def test_handle_group_context_action_wrong_node_or_exhausted_action_returns_clean_result() -> None:
    player_id = uuid.uuid4()
    wrong_node_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        wrong_node_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "craft_town",
            "label": "Озёрный городок",
        },
    )

    handled_wrong, err_wrong, msg_wrong = ws_handlers._handle_group_action_request(
        wrong_node_sess,
        action="group_context_action",
        actor_player_id=player_id,
        payload={"action_id": "clear_old_road"},
        source="test",
    )

    assert handled_wrong is True
    assert err_wrong == "Это contextual действие сейчас недоступно."
    assert msg_wrong is None

    exhausted_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        exhausted_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "chapel_village",
            "label": "Часовенное село",
        },
    )
    session_state.record_group_node_visit(
        exhausted_sess,
        "main",
        "chapel_village",
        node_label="Часовенное село",
        result_type="settlement_arrival",
        summary="Первый визит.",
    )
    session_state.record_group_node_visit(
        exhausted_sess,
        "main",
        "chapel_village",
        node_label="Часовенное село",
        result_type="return_arrival",
        summary="Повторный визит.",
    )
    session_state.resolve_group_context_action(
        exhausted_sess,
        "main",
        action_id="listen_chapel_watch",
        player_id=player_id,
        source="test",
    )

    handled_repeat, err_repeat, msg_repeat = ws_handlers._handle_group_action_request(
        exhausted_sess,
        action="group_context_action",
        actor_player_id=player_id,
        payload={"action_id": "listen_chapel_watch"},
        source="test",
    )

    assert handled_repeat is True
    assert err_repeat is None
    assert "уже было выполнено" in str(msg_repeat)


def test_handle_group_node_entry_read_surface_returns_empty_and_current_entry() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        empty_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    handled_empty, err_empty, msg_empty = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_node_entry",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_empty is True
    assert err_empty is None
    assert msg_empty == "У группы main пока нет node-entry результата."

    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )
    session_state.grant_player_map_knowledge(sess, player_id, "craft_town", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(sess, player_id, "craft_town", source="test")

    started, error = session_state.execute_group_navigation_option(
        sess,
        target_node_id="craft_town",
        player_id=player_id,
        group_id="main",
        source="test",
    )

    assert started is not None
    assert error is None
    updated = session_state.complete_group_travel(sess, "main", player_id=player_id, source="test")
    assert updated is not None

    handled, err, msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_node_entry",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled is True
    assert err is None
    assert msg == "Node entry группы main: Озёрный городок принимает путников (settlement_welcome)."


def test_handle_group_destination_event_read_surface_returns_empty_and_current_event() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        empty_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    handled_empty, err_empty, msg_empty = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_destination_event",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_empty is True
    assert err_empty is None
    assert msg_empty == "У группы main пока нет destination event результата."

    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )
    session_state.grant_player_map_knowledge(sess, player_id, "craft_town", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(sess, player_id, "craft_town", source="test")
    started, error = session_state.execute_group_navigation_option(
        sess,
        target_node_id="craft_town",
        player_id=player_id,
        group_id="main",
        source="test",
    )
    assert started is not None
    assert error is None
    session_state.complete_group_travel(sess, "main", player_id=player_id, source="test")

    handled, err, msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_destination_event",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled is True
    assert err is None
    assert msg == "Destination event группы main: У причала быстро находят ориентиры (settlement_notice)."


def test_handle_group_service_executes_and_errors_cleanly() -> None:
    player_id = uuid.uuid4()
    craft_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        craft_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "craft_town",
            "label": "Озёрный городок",
        },
    )

    handled_service, err_service, msg_service = ws_handlers._handle_group_action_request(
        craft_sess,
        action="group_service_use",
        actor_player_id=player_id,
        payload={"service_id": "craft_town:resupply"},
        source="test",
    )

    assert handled_service is True
    assert err_service is None
    assert "привести снаряжение в порядок" in str(msg_service)
    assert session_state.get_current_group_last_service_result(craft_sess, player_id=player_id)["service_id"] == "craft_town:resupply"

    ruined_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        ruined_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "ruined_settlement",
            "label": "Разрушенный посёлок",
        },
    )

    unavailable_handled, unavailable_err, unavailable_msg = ws_handlers._handle_group_action_request(
        ruined_sess,
        action="group_service_use",
        actor_player_id=player_id,
        payload={"service_id": "safe_rest"},
        source="test",
    )

    assert unavailable_handled is True
    assert unavailable_err == "Эта услуга сейчас недоступна в текущем месте."
    assert unavailable_msg is None


def test_handle_group_service_use_supports_authored_result_and_already_used() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "craft_town",
            "label": "Озёрный городок",
        },
    )
    session_state.record_group_node_visit(
        sess,
        "main",
        "craft_town",
        node_label="Озёрный городок",
        result_type="settlement_arrival",
        summary="Группа прибыла в городок.",
    )
    session_state.resolve_group_destination_event(sess, "main", source="test")

    handled_first, err_first, msg_first = ws_handlers._handle_group_action_request(
        sess,
        action="group_service_use",
        actor_player_id=player_id,
        payload={"service_id": "craft_town_local_guidance"},
        source="test",
    )
    handled_repeat, err_repeat, msg_repeat = ws_handlers._handle_group_action_request(
        sess,
        action="group_service_use",
        actor_player_id=player_id,
        payload={"service_id": "craft_town_local_guidance"},
        source="test",
    )

    assert handled_first is True
    assert err_first is None
    assert "сторожевой башни" in str(msg_first)
    assert session_state.is_player_node_revealed(sess, player_id, "watchtower") is True
    assert set(session_state.get_group_node_state(sess, "main", "craft_town")["state_flags"]) == {
        "craft_arrival_notice_taken",
        "craft_guidance_taken",
    }
    assert handled_repeat is True
    assert err_repeat is None
    assert "уже была использована" in str(msg_repeat)


def test_handle_group_map_intel_returns_empty_and_recent_journal_summary() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(empty_sess, [player_id], "Таверна")

    handled_empty, err_empty, msg_empty = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_map_intel",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_empty is True
    assert err_empty is None
    assert "пока нет записей" in str(msg_empty)

    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )
    session_state.resolve_group_scout(sess, "main", player_id=player_id, source="test")

    handled_filled, err_filled, msg_filled = ws_handlers._handle_group_action_request(
        sess,
        action="group_map_intel",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_filled is True
    assert err_filled is None
    assert "Журнал разведки группы main" in str(msg_filled)
    assert "Последняя запись" in str(msg_filled)


def test_handle_group_visit_history_returns_empty_and_recent_summary() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(empty_sess, [player_id], "Таверна")

    handled_empty, err_empty, msg_empty = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_visit_history",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_empty is True
    assert err_empty is None
    assert "пока нет истории посещений" in str(msg_empty)

    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {"map_level": "region", "node_type": "zone", "node_id": "start_trakt", "label": "Стартовый тракт"},
    )
    session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_id": "start_trakt->craft_town:move",
            "route_kind": "zone_move",
            "action_kind": "move",
            "target_label": "Озёрный городок",
            "target_node_id": "craft_town",
            "target_node": {
                "map_level": "region",
                "node_type": "zone",
                "node_id": "craft_town",
                "label": "Озёрный городок",
                "zone_label": "Озёрный городок",
                "area_label": "Озёрный городок",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "region",
                "node_type": "zone",
                "node_id": "craft_town",
                "label": "Озёрный городок",
                "area_label": "Озёрный городок",
            },
            "next_zone_label": "Озёрный городок",
            "source": "registry",
        },
        source="test",
    )
    session_state.complete_group_travel(sess, "main", player_id=player_id, source="test")

    handled_filled, err_filled, msg_filled = ws_handlers._handle_group_action_request(
        sess,
        action="group_visit_history",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_filled is True
    assert err_filled is None
    assert "История пути группы main" in str(msg_filled)
    assert "посещённых точек" in str(msg_filled)


def test_handle_group_route_planning_and_target_lookup_return_clean_summaries() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    for node_id in ("road_hamlet", "mine_entrance"):
        session_state.grant_player_map_knowledge(sess, player_id, node_id, knowledge_kind="known", source="test")
        session_state.reveal_player_map_node(sess, player_id, node_id, source="test")
    session_state.set_group_route_access_state(
        sess,
        "main",
        "forest_road->mine_entrance:enter",
        access_state="blocked",
        summary="Вход завален.",
        block_reason="blocked_path",
        source="test",
    )

    handled_routes, err_routes, msg_routes = ws_handlers._handle_group_action_request(
        sess,
        action="group_route_planning",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    handled_reachable, err_reachable, msg_reachable = ws_handlers._handle_group_action_request(
        sess,
        action="group_route_plan_to",
        actor_player_id=player_id,
        payload={"target_node_id": "road_hamlet"},
        source="test",
    )
    handled_blocked, err_blocked, msg_blocked = ws_handlers._handle_group_action_request(
        sess,
        action="group_route_plan_to",
        actor_player_id=player_id,
        payload={"target_node_id": "mine_entrance"},
        source="test",
    )
    handled_unrevealed, err_unrevealed, msg_unrevealed = ws_handlers._handle_group_action_request(
        sess,
        action="group_route_plan_to",
        actor_player_id=player_id,
        payload={"target_node_id": "watchtower"},
        source="test",
    )

    assert handled_routes is True
    assert err_routes is None
    assert "Маршрутный план группы main" in str(msg_routes)
    assert handled_reachable is True
    assert err_reachable is None
    assert "Путь к Дорожный хутор доступен" in str(msg_reachable)
    assert handled_blocked is True
    assert err_blocked is None
    assert msg_blocked == "Путь к Шахтный вход заблокирован: blocked_path."
    assert handled_unrevealed is True
    assert err_unrevealed is None
    assert msg_unrevealed == "Точка Сторожевая башня ещё не раскрыта для текущей группы."


def test_handle_group_exploration_leads_returns_empty_and_primary_summary() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(empty_sess, [player_id], "Таверна")

    handled_empty, err_empty, msg_empty = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_exploration_leads",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_empty is True
    assert err_empty is None
    assert msg_empty == "У группы main сейчас нет явных exploration leads."

    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )
    for node_id in ("fortress_gate",):
        session_state.grant_player_map_knowledge(sess, player_id, node_id, knowledge_kind="known", source="test")
        session_state.reveal_player_map_node(sess, player_id, node_id, source="test")
    session_state.set_group_journey_target(sess, "main", "fortress_gate", player_id=player_id, source="test")

    handled_filled, err_filled, msg_filled = ws_handlers._handle_group_action_request(
        sess,
        action="group_exploration_leads",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_filled is True
    assert err_filled is None
    assert "Exploration leads группы main: " in str(msg_filled)
    assert "Главная зацепка: Активный путь: Ворота крепости." in str(msg_filled)


def test_handle_group_node_progress_returns_quiet_and_active_summaries() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        empty_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    handled_quiet, err_quiet, msg_quiet = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_node_progress",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_quiet is True
    assert err_quiet is None
    assert "quiet_location" in str(msg_quiet)

    active_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        active_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "craft_town",
            "label": "Озёрный городок",
        },
    )
    session_state.record_group_node_visit(
        active_sess,
        "main",
        "craft_town",
        node_label="Озёрный городок",
        result_type="first_arrival",
        summary="Первый визит.",
    )

    handled_active, err_active, msg_active = ws_handlers._handle_group_action_request(
        active_sess,
        action="group_node_progress",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_active is True
    assert err_active is None
    assert "locally_active" in str(msg_active)
    assert "Озёрный городок" in str(msg_active)


def test_handle_group_region_progress_returns_minimal_and_frontier_summaries() -> None:
    player_id = uuid.uuid4()
    minimal_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        minimal_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "mine_entrance",
            "label": "Шахтный вход",
        },
    )

    handled_min, err_min, msg_min = ws_handlers._handle_group_action_request(
        minimal_sess,
        action="group_region_progress",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_min is True
    assert err_min is None
    assert "region_quiet" in str(msg_min)

    frontier_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        frontier_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )
    session_state.grant_player_map_knowledge(frontier_sess, player_id, "craft_town", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(frontier_sess, player_id, "craft_town", source="test")

    handled_frontier, err_frontier, msg_frontier = ws_handlers._handle_group_action_request(
        frontier_sess,
        action="group_region_progress",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_frontier is True
    assert err_frontier is None
    assert (
        "active_frontier" in str(msg_frontier)
        or "expanding_routes" in str(msg_frontier)
        or "newly_opened_region" in str(msg_frontier)
    )


def test_handle_group_region_gateways_returns_clean_minimal_and_authored_gateway_summaries() -> None:
    player_id = uuid.uuid4()
    minimal_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        minimal_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    handled_min, err_min, msg_min = ws_handlers._handle_group_action_request(
        minimal_sess,
        action="group_region_gateways",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_min is True
    assert err_min is None
    assert "нет видимых выходов" in str(msg_min)

    gateway_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        gateway_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "landmark",
            "node_id": "forgotten_shrine",
            "label": "Забытое святилище",
        },
    )

    handled_gateway, err_gateway, msg_gateway = ws_handlers._handle_group_action_request(
        gateway_sess,
        action="group_region_gateways",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_gateway is True
    assert err_gateway is None
    assert "Региональные выходы" in str(msg_gateway)
    assert "future_stub" in str(msg_gateway)


def test_handle_group_region_transition_execute_and_status_surface() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        empty_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )
    handled_empty, err_empty, msg_empty = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_region_transition_status",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_empty is True
    assert err_empty is None
    assert "пока нет region transition результата" in str(msg_empty)

    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_settlement",
            "label": "Лесной посёлок",
        },
    )
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )

    handled_exec, err_exec, msg_exec = ws_handlers._handle_group_action_request(
        sess,
        action="group_region_transition",
        actor_player_id=player_id,
        payload={"gateway_id": "forest_settlement_northwatch"},
        source="test",
    )
    assert handled_exec is True
    assert err_exec is None
    assert "Северный рубеж" in str(msg_exec)

    handled_status, err_status, msg_status = ws_handlers._handle_group_action_request(
        sess,
        action="group_region_transition_status",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_status is True
    assert err_status is None
    assert "completed" in str(msg_status)
    assert "Выход к северному рубежу" in str(msg_status)


def test_handle_group_region_links_and_gateway_history_surfaces() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        empty_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )
    handled_empty_links, err_empty_links, msg_empty_links = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_region_links",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    handled_empty_crossings, err_empty_crossings, msg_empty_crossings = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_gateway_history",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_empty_links is True
    assert err_empty_links is None
    assert "нет discovered region links" in str(msg_empty_links)
    assert handled_empty_crossings is True
    assert err_empty_crossings is None
    assert "нет истории gateway crossings" in str(msg_empty_crossings)

    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_settlement",
            "label": "Лесной посёлок",
        },
    )
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.resolve_group_region_transition(
        sess,
        "main",
        "forest_settlement_northwatch",
        player_id=player_id,
        source="test",
    )

    handled_links, err_links, msg_links = ws_handlers._handle_group_action_request(
        sess,
        action="group_region_links",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    handled_crossings, err_crossings, msg_crossings = ws_handlers._handle_group_action_request(
        sess,
        action="group_gateway_history",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_links is True
    assert err_links is None
    assert "впервые подтверждает связку регионов" in str(msg_links)
    assert handled_crossings is True
    assert err_crossings is None
    assert "Выход к северному рубежу" in str(msg_crossings)


def test_handle_group_known_region_route_and_primary_route_surfaces() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        empty_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    handled_empty_focus, err_empty_focus, msg_empty_focus = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_primary_region_route",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_empty_focus is True
    assert err_empty_focus is None
    assert "нет выраженного primary region route" in str(msg_empty_focus)

    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.reveal_player_map_node(sess, player_id, "forest_settlement", source="test")
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.record_group_gateway_traversal(
        sess,
        "main",
        gateway_id="forest_settlement_northwatch",
        gateway_label="Выход к северному рубежу",
        source_region_id="starter_frontier",
        source_region_label="Стартовое пограничье",
        target_region_id="northwatch_frontier",
        target_region_label="Северный рубеж",
        source="test",
    )
    groups = session_state._get_group_states(sess)
    group = groups["main"]
    group["discovered_regions"]["northwatch_frontier"] = {
        "region_id": "northwatch_frontier",
        "region_label": "Северный рубеж",
        "visit_count": 1,
        "first_entered_at": "2025-01-02T00:00:00+00:00",
        "last_entered_at": "2025-01-02T00:00:00+00:00",
        "first_anchor_node_id": "northwatch_outpost",
        "last_anchor_node_id": "northwatch_outpost",
        "summary": "Группа ранее входила в регион Северный рубеж.",
    }
    session_state._persist_group_states(sess, groups)
    session_state._sync_group_position_mirrors(sess, group)

    handled_route, err_route, msg_route = ws_handlers._handle_group_action_request(
        sess,
        action="group_known_region_route",
        actor_player_id=player_id,
        payload={"target_region_id": "northwatch_frontier"},
        source="test",
    )
    assert handled_route is True
    assert err_route is None
    assert "Северный рубеж" in str(msg_route)
    assert "group go forest_settlement" in str(msg_route)

    handled_focus, err_focus, msg_focus = ws_handlers._handle_group_action_request(
        sess,
        action="group_primary_region_route",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_focus is True
    assert err_focus is None
    assert "Стартовое пограничье" in str(msg_focus) or "Северный рубеж" in str(msg_focus)


def test_handle_group_region_status_and_discovered_regions_surface() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        empty_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )
    handled_here, err_here, msg_here = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_region_status",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_here is True
    assert err_here is None
    assert "Стартовое пограничье" in str(msg_here)

    handled_regions, err_regions, msg_regions = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_discovered_regions",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_regions is True
    assert err_regions is None
    assert "Открытые регионы группы main: 1." in str(msg_regions)
    assert "Стартовое пограничье" in str(msg_regions)


def test_handle_group_region_onboarding_surface() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        empty_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_settlement",
            "label": "Лесной посёлок",
        },
    )

    handled_empty, err_empty, msg_empty = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_region_onboarding",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_empty is True
    assert err_empty is None
    assert "пока нет region onboarding результата" in str(msg_empty)

    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)

    handled, err, msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_region_onboarding",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled is True
    assert err is None
    assert "Region onboarding группы main" in str(msg)
    assert "Стартовое пограничье" in str(msg)


def test_handle_group_region_world_and_focus_surfaces() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        empty_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_settlement",
            "label": "Лесной посёлок",
        },
    )

    handled_empty_world, err_empty_world, msg_empty_world = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_region_world",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_empty_world is True
    assert err_empty_world is None
    assert "слишком мало discovered-region данных" in str(msg_empty_world)

    handled_empty_focus, err_empty_focus, msg_empty_focus = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_region_focus",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_empty_focus is True
    assert err_empty_focus is None
    assert "пока нет выраженного region focus" in str(msg_empty_focus)

    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_settlement",
            "label": "Лесной посёлок",
        },
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.resolve_group_region_transition(
        sess,
        "main",
        "forest_settlement_northwatch",
        player_id=player_id,
        source="region_transition",
    )

    handled_world, err_world, msg_world = ws_handlers._handle_group_action_request(
        sess,
        action="group_region_world",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_world is True
    assert err_world is None
    assert "Мировой обзор регионов группы main" in str(msg_world)
    assert "открытых регионов" in str(msg_world)

    handled_focus, err_focus, msg_focus = ws_handlers._handle_group_action_request(
        sess,
        action="group_region_focus",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_focus is True
    assert err_focus is None
    assert "Region focus группы main" in str(msg_focus)


def test_handle_group_region_target_plan_and_focus_path_surfaces() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.reveal_player_map_node(sess, player_id, "forest_settlement", source="test")
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )

    handled_route, err_route, msg_route = ws_handlers._handle_group_action_request(
        sess,
        action="group_region_target_plan",
        actor_player_id=player_id,
        payload={"target_region_id": "northwatch_frontier"},
        source="test",
    )
    assert handled_route is True
    assert err_route is None
    assert "Северный рубеж" in str(msg_route)
    assert "group go forest_settlement" in str(msg_route)

    handled_focus, err_focus, msg_focus = ws_handlers._handle_group_action_request(
        sess,
        action="group_primary_region_focus_plan",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_focus is True
    assert err_focus is None
    assert "Стартовое пограничье" in str(msg_focus)

    handled_missing, err_missing, msg_missing = ws_handlers._handle_group_action_request(
        sess,
        action="group_region_target_plan",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_missing is True
    assert "target_region_id" in str(err_missing)
    assert msg_missing is None


def test_handle_group_region_pursuit_set_status_and_clear_surfaces() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        empty_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    handled_empty, err_empty, msg_empty = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_region_pursuit_status",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_empty is True
    assert err_empty is None
    assert "нет активного region pursuit" in str(msg_empty)

    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.reveal_player_map_node(sess, player_id, "forest_settlement", source="test")
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )

    handled_set, err_set, msg_set = ws_handlers._handle_group_action_request(
        sess,
        action="group_region_pursuit_set",
        actor_player_id=player_id,
        payload={"target_region_id": "northwatch_frontier"},
        source="test",
    )
    assert handled_set is True
    assert err_set is None
    assert "Лесной посёлок" in str(msg_set)

    handled_status, err_status, msg_status = ws_handlers._handle_group_action_request(
        sess,
        action="group_region_pursuit_status",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_status is True
    assert err_status is None
    assert "pursuing_gateway" in str(msg_status)
    assert "group go forest_settlement" in str(msg_status)

    handled_clear, err_clear, msg_clear = ws_handlers._handle_group_action_request(
        sess,
        action="group_region_pursuit_clear",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_clear is True
    assert err_clear is None
    assert "остановлен" in str(msg_clear)


def test_handle_group_region_pursuit_advance_and_step_status_surfaces() -> None:
    player_id = uuid.uuid4()
    empty_sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        empty_sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    handled_empty, err_empty, msg_empty = ws_handlers._handle_group_action_request(
        empty_sess,
        action="group_region_pursuit_step_status",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_empty is True
    assert err_empty is None
    assert "нет region pursuit step результата" in str(msg_empty)

    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "forest_road",
            "label": "Лесная дорога",
        },
    )
    session_state.get_current_group_current_region_state(sess, player_id=player_id)
    session_state.reveal_player_map_node(sess, player_id, "forest_settlement", source="test")
    session_state.add_group_node_state_flag(
        sess,
        "main",
        "forest_settlement",
        state_flag="forest_supplies_secured",
        summary="Лесной набор уже готов.",
        source="test",
    )
    session_state.set_group_region_pursuit(
        sess,
        "main",
        "northwatch_frontier",
        player_id=player_id,
        source="test",
    )

    handled_advance, err_advance, msg_advance = ws_handlers._handle_group_action_request(
        sess,
        action="group_region_pursuit_advance",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_advance is True
    assert err_advance is None
    assert "gateway завершён" in str(msg_advance)

    handled_status, err_status, msg_status = ws_handlers._handle_group_action_request(
        sess,
        action="group_region_pursuit_step_status",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    assert handled_status is True
    assert err_status is None
    assert "group exit forest_settlement_northwatch" in str(msg_status)


def test_handle_group_journey_set_advance_status_and_stop() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )
    for node_id in ("craft_town", "fortress_gate"):
        session_state.grant_player_map_knowledge(sess, player_id, node_id, knowledge_kind="known", source="test")
        session_state.reveal_player_map_node(sess, player_id, node_id, source="test")

    handled_set, err_set, msg_set = ws_handlers._handle_group_action_request(
        sess,
        action="group_journey_set",
        actor_player_id=player_id,
        payload={"target_node_id": "fortress_gate"},
        source="test",
    )
    handled_status, err_status, msg_status = ws_handlers._handle_group_action_request(
        sess,
        action="group_journey_status",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    handled_advance, err_advance, msg_advance = ws_handlers._handle_group_action_request(
        sess,
        action="group_journey_advance",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    arrived_group = session_state._get_group_states(sess)["main"]
    handled_stop, err_stop, msg_stop = ws_handlers._handle_group_action_request(
        sess,
        action="group_stop",
        actor_player_id=player_id,
        payload={},
        source="test",
    )
    handled_status_empty, err_status_empty, msg_status_empty = ws_handlers._handle_group_action_request(
        sess,
        action="group_journey_status",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_set is True
    assert err_set is None
    assert "активное путешествие" in str(msg_set)
    assert handled_status is True
    assert err_status is None
    assert "Путешествие группы main: planned к Ворота крепости" in str(msg_status)
    assert handled_advance is True
    assert err_advance is None
    assert msg_advance == "Путешествие к Ворота крепости завершено."
    assert arrived_group["current_map_position"]["node_id"] == "fortress_gate"
    assert arrived_group["active_journey"]["journey_status"] == "arrived"
    assert handled_stop is True
    assert err_stop is None
    assert msg_stop == "Путешествие группы main остановлено."
    assert "active_journey" not in session_state._get_group_states(sess)["main"]
    assert handled_status_empty is True
    assert err_status_empty is None
    assert msg_status_empty == "У группы main сейчас нет активного путешествия."


def test_handle_group_journey_reports_unavailable_and_blocked_mid_route_cleanly() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )
    session_state.grant_player_map_knowledge(sess, player_id, "watchtower", knowledge_kind="known", source="test")
    handled_unavailable, err_unavailable, msg_unavailable = ws_handlers._handle_group_action_request(
        sess,
        action="group_journey_set",
        actor_player_id=player_id,
        payload={"target_node_id": "watchtower"},
        source="test",
    )
    assert handled_unavailable is True
    assert err_unavailable == "Точка Сторожевая башня ещё не раскрыта для текущей группы."
    assert msg_unavailable is None

    for node_id in ("craft_town", "fortress_gate"):
        session_state.grant_player_map_knowledge(sess, player_id, node_id, knowledge_kind="known", source="test")
        session_state.reveal_player_map_node(sess, player_id, node_id, source="test")
    handled_set, err_set, _msg_set = ws_handlers._handle_group_action_request(
        sess,
        action="group_journey_set",
        actor_player_id=player_id,
        payload={"target_node_id": "craft_town"},
        source="test",
    )
    assert handled_set is True
    assert err_set is None
    session_state.set_group_route_access_state(
        sess,
        "main",
        "start_trakt->craft_town:move",
        access_state="blocked",
        summary="Путь перекрыт.",
        block_reason="blocked_path",
        source="test",
    )
    session_state.set_group_route_access_state(
        sess,
        "main",
        "fortress_gate->craft_town:move",
        access_state="blocked",
        summary="Обход к городку тоже закрыт.",
        block_reason="fortress_lockdown",
        source="test",
    )

    handled_blocked, err_blocked, msg_blocked = ws_handlers._handle_group_action_request(
        sess,
        action="group_journey_advance",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_blocked is True
    assert err_blocked == "Путь к Озёрный городок упирается в заблокированный маршрут."
    assert msg_blocked is None
    blocked_group = session_state._get_group_states(sess)["main"]
    assert blocked_group["active_journey"]["journey_status"] == "blocked"


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


def test_handle_group_event_resolve_and_ignore_requests() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(sess, [player_id], "Стартовый тракт")

    session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "zone_move",
            "action_kind": "move",
            "target_label": "Край болот",
            "target_node": {
                "map_level": "region",
                "node_type": "zone",
                "node_id": "marsh_edge",
                "label": "Край болот",
                "zone_label": "Край болот",
                "area_label": "Край болот",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "region",
                "node_type": "zone",
                "node_id": "marsh_edge",
                "label": "Край болот",
            },
            "next_zone_label": "Край болот",
            "traversal_kind": "marsh_path",
            "risk_band": "high",
            "terrain_hint": "marsh",
            "travel_tags": ["poor_visibility"],
        },
        source="test",
    )

    handled_resolve, err_resolve, msg_resolve = ws_handlers._handle_group_action_request(
        sess,
        action="group_event_resolve",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_resolve is True
    assert err_resolve is None
    assert msg_resolve == "Группа main разбирается с дорожным событием: blocked_path."
    resolved_group = session_state._get_group_states(sess)["main"]
    assert resolved_group["status"] == "moving"
    assert resolved_group["travel_state"]["paused"] is False
    assert resolved_group["travel_event"]["active"] is False
    assert resolved_group["travel_event"]["resolution"] == "resolve"
    assert resolved_group["last_travel_event_outcome"]["outcome_type"] == "obstacle_cleared"

    session_state.start_group_travel(
        sess,
        "main",
        {
            "allowed": True,
            "route_kind": "landmark_move",
            "action_kind": "move",
            "target_label": "Ворота крепости",
            "target_node": {
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "fortress_gate",
                "label": "Ворота крепости",
                "zone_label": "Стартовый тракт",
                "area_label": "Стартовый тракт",
            },
            "next_map_position": {
                "v": 1,
                "map_level": "landmark",
                "node_type": "landmark",
                "node_id": "fortress_gate",
                "label": "Ворота крепости",
                "area_label": "Стартовый тракт",
            },
            "next_zone_label": "Стартовый тракт",
            "source": "registry",
            "traversal_kind": "road",
            "risk_band": "low",
            "terrain_hint": "open",
        },
        source="test",
    )

    handled_ignore, err_ignore, msg_ignore = ws_handlers._handle_group_action_request(
        sess,
        action="group_event_ignore",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_ignore is True
    assert err_ignore is None
    assert msg_ignore == "Группа main игнорирует дорожное событие: roadside_finding."
    ignored_group = session_state._get_group_states(sess)["main"]
    assert ignored_group["status"] == "moving"
    assert ignored_group["travel_state"]["active"] is True
    assert ignored_group["travel_event"]["active"] is False
    assert ignored_group["travel_event"]["resolution"] == "ignore"
    assert ignored_group["last_travel_event_outcome"]["outcome_type"] == "ignored_event"

    handled_missing, err_missing, msg_missing = ws_handlers._handle_group_action_request(
        sess,
        action="group_event_resolve",
        actor_player_id=player_id,
        payload={},
        source="test",
    )

    assert handled_missing is True
    assert err_missing == "У группы нет активного travel event."
    assert msg_missing is None

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


def test_handle_group_move_respects_player_known_static_nodes() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    known_node_ids = session_state.get_player_known_node_ids(sess, player_id)
    revealed_node_ids = session_state.get_player_revealed_node_ids(sess, player_id)

    assert "start_trakt" in known_node_ids
    assert "fortress_gate" in known_node_ids
    assert "eastern_bank" not in known_node_ids
    assert "start_trakt" in revealed_node_ids
    assert "fortress_gate" in revealed_node_ids
    assert "eastern_bank" not in revealed_node_ids

    handled_known, err_known, msg_known = ws_handlers._handle_group_action_request(
        sess,
        action="group_move",
        actor_player_id=player_id,
        payload={"target_hint": "ворота крепости"},
        source="test",
    )

    assert handled_known is True
    assert err_known is None
    assert msg_known == "Группа main движется к Ворота крепости."

    session_state.interrupt_group_travel(sess, "main")

    handled_unknown, err_unknown, msg_unknown = ws_handlers._handle_group_action_request(
        sess,
        action="group_move",
        actor_player_id=player_id,
        payload={"target_hint": "Восточный берег"},
        source="test",
    )

    assert handled_unknown is True
    assert err_unknown == "Группа пока не знает эту точку карты."
    assert msg_unknown is None


def test_handle_group_navigate_executes_registry_option_for_move_and_enter() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )
    session_state.grant_player_map_knowledge(sess, player_id, "craft_town", knowledge_kind="known", source="test")

    handled_move, err_move, msg_move = ws_handlers._handle_group_action_request(
        sess,
        action="group_navigate",
        actor_player_id=player_id,
        payload={"target_node_id": "craft_town"},
        source="test",
    )

    assert handled_move is True
    assert err_move is None
    assert msg_move == "Группа main движется к Озёрный городок."
    moving_group = session_state._get_group_states(sess)["main"]
    assert moving_group["movement_intent"]["target_node_id"] == "craft_town"
    assert moving_group["movement_intent"]["action_kind"] == "move"
    assert moving_group["travel_state"]["route_summary"]["source"] == "registry"

    session_state.interrupt_group_travel(sess, "main")
    session_state.grant_player_map_knowledge(sess, player_id, "forest_road", knowledge_kind="known", source="test")
    groups = session_state._get_group_states(sess)
    group = groups["main"]
    group["current_map_position"] = {
        "v": 1,
        "map_level": "region",
        "node_type": "zone",
        "node_id": "ruined_settlement",
        "label": "Разрушенный посёлок",
        "area_label": "Разрушенный посёлок",
    }
    group["area_label"] = "Разрушенный посёлок"
    session_state._persist_group_states(sess, groups)
    session_state.grant_player_map_knowledge(sess, player_id, "mine_entrance", knowledge_kind="known", source="test")

    handled_enter, err_enter, msg_enter = ws_handlers._handle_group_action_request(
        sess,
        action="group_navigate",
        actor_player_id=player_id,
        payload={"target_node_id": "mine_entrance"},
        source="test",
    )

    assert handled_enter is True
    assert err_enter is None
    assert msg_enter == "Группа main входит в Шахтный вход."
    entered_group = session_state._get_group_states(sess)["main"]
    assert entered_group["movement_intent"]["action_kind"] == "enter"
    assert entered_group["travel_state"]["paused"] is True
    assert entered_group["travel_state"]["pause_reason"] == "target_requires_enter"


def test_handle_group_navigate_returns_clear_errors_for_unknown_and_unavailable_targets() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )

    handled_unknown, err_unknown, msg_unknown = ws_handlers._handle_group_action_request(
        sess,
        action="group_navigate",
        actor_player_id=player_id,
        payload={"target_node_id": "missing_node"},
        source="test",
    )

    assert handled_unknown is True
    assert err_unknown == "Неизвестная navigation цель группы."
    assert msg_unknown is None

    handled_not_known, err_not_known, msg_not_known = ws_handlers._handle_group_action_request(
        sess,
        action="group_navigate",
        actor_player_id=player_id,
        payload={"target_node_id": "watchtower"},
        source="test",
    )

    assert handled_not_known is True
    assert err_not_known == "Группа пока не знает эту точку карты."
    assert msg_not_known is None

    session_state.grant_player_map_knowledge(sess, player_id, "watchtower", knowledge_kind="known", source="test")
    handled_unavailable, err_unavailable, msg_unavailable = ws_handlers._handle_group_action_request(
        sess,
        action="group_navigate",
        actor_player_id=player_id,
        payload={"target_node_id": "watchtower"},
        source="test",
    )

    assert handled_unavailable is True
    assert err_unavailable == "Эта navigation цель сейчас недоступна из текущей точки."
    assert msg_unavailable is None


def test_handle_group_navigate_rejects_revealed_but_blocked_route() -> None:
    player_id = uuid.uuid4()
    sess = SimpleNamespace(settings={})
    session_state._initialize_default_group(
        sess,
        [player_id],
        {
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
    )
    session_state.grant_player_map_knowledge(sess, player_id, "craft_town", knowledge_kind="known", source="test")
    session_state.reveal_player_map_node(sess, player_id, "craft_town", source="test")
    session_state.set_group_route_access_state(
        sess,
        "main",
        "start_trakt->craft_town:move",
        access_state="blocked",
        summary="Путь к городку перекрыт.",
        block_reason="оползень",
        source="test",
    )

    handled, err, msg = ws_handlers._handle_group_action_request(
        sess,
        action="group_navigate",
        actor_player_id=player_id,
        payload={"target_node_id": "craft_town"},
        source="test",
    )

    assert handled is True
    assert err == "Маршрут к Озёрный городок сейчас заблокирован: оползень."
    assert msg is None


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
