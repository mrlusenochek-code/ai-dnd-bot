from __future__ import annotations

from app.web.map_registry import (
    find_static_link,
    get_current_node_context_actions,
    get_obvious_linked_static_node_ids,
    get_static_node_detail,
    get_static_node_context,
    get_static_node_destination_events,
    get_static_node_context_action_requirements,
    get_static_node_context_action_effects,
    get_static_node_scout_discoveries,
    get_static_node_service_effects,
    get_static_node_service_requirements,
    get_static_node_inspect_result,
    get_static_node_state_overlays,
    get_static_node_entry_overlays,
    get_static_region_gateways,
    get_static_node_region_gateways,
    get_static_node_service_result,
    get_static_node_services,
    get_static_navigation_options,
    get_static_link_metadata,
    get_static_map_links,
    get_static_map_nodes,
    get_static_node_metadata,
    get_static_node,
    get_static_region_identity,
    get_static_region_onboarding,
    resolve_static_map_node,
)
from app.web.map_targeting import resolve_action_target_node, resolve_group_target_route, validate_group_target_transition


def test_static_map_registry_loads_known_nodes_and_links() -> None:
    nodes = get_static_map_nodes()
    links = get_static_map_links()

    node_ids = [node["node_id"] for node in nodes]

    assert len(nodes) >= 12
    assert len(node_ids) == len(set(node_ids))
    assert "craft_town" in node_ids
    assert "road_hamlet" in node_ids
    assert "chapel_village" in node_ids
    assert "forest_settlement" in node_ids
    assert "ruined_settlement" in node_ids
    assert "old_fortress_edge" in node_ids
    assert "marsh_edge" in node_ids
    assert "forgotten_shrine" in node_ids
    assert any(node["node_type"] == "zone" for node in nodes)
    assert any(node["node_type"] == "landmark" for node in nodes)
    assert any(node["node_type"] == "interior_entry" for node in nodes)
    assert get_static_node_metadata(get_static_node("craft_town")) == {
        "settlement_kind": "town",
        "environment_hint": "lakeshore",
        "safe_rest_hint": True,
    }
    assert get_static_node("start_trakt") == {
        "node_id": "start_trakt",
        "label": "Стартовый тракт",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Стартовый тракт",
        "zone_band": "safe",
        "settlement_kind": "roadside",
        "environment_hint": "roadland",
        "safe_rest_hint": True,
        "short_description": "Широкий тракт у стартового лагеря, где сходятся безопасные дороги региона.",
        "inspect_summary": "По тракту удобно держать путь к воротам крепости и к озёрному городку.",
        "travel_note": "Хороший ориентир для сбора группы и спокойного перехода.",
        "service_hints": ["можно переждать у дороги", "подходит для сбора перед выходом"],
        "aliases": (
            "стартовый тракт",
            "тракт",
            "дорога у лагеря",
            "лагерный тракт",
        ),
    }
    assert find_static_link("start_trakt", "fortress_gate", "move") == {
        "from_node_id": "start_trakt",
        "to_node_id": "fortress_gate",
        "action_kind": "move",
        "route_id": "start_trakt->fortress_gate:move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
        "traversal_kind": "gate_approach",
        "risk_band": "low",
        "terrain_hint": "fortified",
        "travel_tags": ["fortified"],
    }
    assert find_static_link("craft_town", "fortress_gate", "move") == {
        "from_node_id": "craft_town",
        "to_node_id": "fortress_gate",
        "action_kind": "move",
        "route_id": "craft_town->fortress_gate:move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
        "traversal_kind": "gate_approach",
        "risk_band": "low",
        "terrain_hint": "fortified",
        "travel_tags": ["fortified"],
    }
    assert find_static_link("forest_settlement", "old_fortress_edge", "move") == {
        "from_node_id": "forest_settlement",
        "to_node_id": "old_fortress_edge",
        "action_kind": "move",
        "route_id": "forest_settlement->old_fortress_edge:move",
        "route_kind": "landmark_move",
        "link_kind": "ruin_path",
        "traversal_kind": "ruin_path",
        "risk_band": "high",
        "terrain_hint": "ruins",
        "travel_tags": ["ruins", "elevated_watch"],
    }
    assert find_static_link("ruined_settlement", "mine_entrance", "enter") == {
        "from_node_id": "ruined_settlement",
        "to_node_id": "mine_entrance",
        "action_kind": "enter",
        "route_id": "ruined_settlement->mine_entrance:enter",
        "route_kind": "enter_location",
        "link_kind": "entrance",
        "traversal_kind": "entry",
        "risk_band": "high",
        "terrain_hint": "ruins",
        "travel_tags": ["transition", "interior_threshold"],
    }
    assert any(link["action_kind"] == "enter" for link in links)
    assert get_static_link_metadata(find_static_link("ruined_settlement", "mine_entrance", "enter")) == {
        "traversal_kind": "entry",
        "risk_band": "high",
        "terrain_hint": "ruins",
        "travel_tags": ["transition", "interior_threshold"],
    }
    assert get_obvious_linked_static_node_ids("start_trakt") == ["fortress_gate"]


def test_get_static_navigation_options_returns_expected_registry_options() -> None:
    options = get_static_navigation_options(
        current_node_id="start_trakt",
        known_node_ids={"start_trakt", "fortress_gate", "craft_town"},
        revealed_node_ids={"start_trakt", "fortress_gate"},
    )

    assert options == [
        {
            "route_id": "start_trakt->fortress_gate:move",
            "target_node_id": "fortress_gate",
            "target_label": "Ворота крепости",
            "target_node_type": "landmark",
            "action_kind": "move",
            "route_kind": "landmark_move",
            "traversal_kind": "gate_approach",
            "risk_band": "low",
            "terrain_hint": "fortified",
            "travel_tags": ["fortified"],
            "source": "registry",
            "known": True,
            "revealed": True,
            "visible": True,
        },
        {
            "route_id": "start_trakt->craft_town:move",
            "target_node_id": "craft_town",
            "target_label": "Озёрный городок",
            "target_node_type": "zone",
            "action_kind": "move",
            "route_kind": "zone_move",
            "traversal_kind": "road",
            "risk_band": "low",
            "terrain_hint": "open",
            "travel_tags": ["settled_route"],
            "source": "registry",
            "known": True,
            "revealed": False,
            "visible": False,
        },
    ]


def test_get_static_navigation_options_hides_unknown_static_targets() -> None:
    options = get_static_navigation_options(
        current_node_id="start_trakt",
        known_node_ids={"start_trakt", "fortress_gate"},
        revealed_node_ids={"start_trakt", "fortress_gate"},
    )

    assert [option["target_node_id"] for option in options] == ["fortress_gate"]


def test_get_static_node_context_builds_zone_landmark_and_interior_summaries() -> None:
    assert get_static_node_context(node_id="craft_town") == {
        "node_id": "craft_town",
        "label": "Озёрный городок",
        "node_type": "zone",
        "area_label": "Озёрный городок",
        "zone_band": "safe",
        "settlement_kind": "town",
        "environment_hint": "lakeshore",
        "safe_rest_hint": True,
        "detail_summary": "Здесь легко пополнить припасы, переждать дорогу и собрать слухи о ближних тропах.",
    }
    assert get_static_node_context(node_id="fortress_gate") == {
        "node_id": "fortress_gate",
        "label": "Ворота крепости",
        "node_type": "landmark",
        "area_label": "Стартовый тракт",
        "zone_band": "safe",
        "poi_kind": "fortified",
        "environment_hint": "fortified",
        "safe_rest_hint": False,
        "detail_summary": "У ворот хорошо видно дорогу, подходы к городку и кто проходит в сторону границы.",
    }
    assert get_static_node_context(node_id="mine_entrance") == {
        "node_id": "mine_entrance",
        "label": "Шахтный вход",
        "node_type": "interior_entry",
        "area_label": "Разрушенный посёлок",
        "zone_band": "danger",
        "poi_kind": "mine",
        "environment_hint": "ruined_frontier",
        "safe_rest_hint": False,
        "detail_summary": "Перед спуском можно заметить свежие следы, обваленные крепи и узкий безопасный проход.",
    }


def test_get_current_node_context_actions_uses_metadata_honestly() -> None:
    assert get_current_node_context_actions(node_id="craft_town") == [
        {"action_id": "navigate", "action_key": "navigate", "label": "Продолжить путь", "action_type": "action", "action_kind": "navigate"},
        {"action_id": "inspect", "action_key": "inspect", "label": "Осмотреться", "action_type": "action", "action_kind": "inspect"},
        {"action_id": "wait", "action_key": "wait", "label": "Подождать", "action_type": "action", "action_kind": "wait"},
        {"action_id": "rest_hint", "action_key": "rest_hint", "label": "Есть место для передышки", "action_type": "hint", "action_kind": "rest_hint"},
        {"action_id": "trace_watchtower_bearing", "action_key": "trace_watchtower_bearing", "label": "Сверить береговой ориентир", "action_type": "action", "action_kind": "clue", "source": "registry", "one_shot": False},
    ]
    assert get_current_node_context_actions(node_id="mine_entrance") == [
        {"action_id": "enter", "action_key": "enter", "label": "Войти", "action_type": "action", "action_kind": "enter"},
        {"action_id": "inspect", "action_key": "inspect", "label": "Осмотреть вход", "action_type": "action", "action_kind": "inspect"},
        {"action_id": "wait", "action_key": "wait", "label": "Подождать", "action_type": "action", "action_kind": "wait"},
    ]
    assert get_current_node_context_actions(node_id="marsh_edge") == [
        {"action_id": "navigate", "action_key": "navigate", "label": "Продолжить путь", "action_type": "action", "action_kind": "navigate"},
        {"action_id": "inspect", "action_key": "inspect", "label": "Осмотреться", "action_type": "action", "action_kind": "inspect"},
        {"action_id": "wait", "action_key": "wait", "label": "Подождать", "action_type": "action", "action_kind": "wait"},
        {"action_id": "camp", "action_key": "camp", "label": "Разбить лагерь", "action_type": "action", "action_kind": "camp"},
    ]


def test_get_current_node_context_actions_exposes_authored_action_ids() -> None:
    actions = get_current_node_context_actions(node_id="forest_road")

    assert any(action["action_id"] == "clear_old_road" for action in actions)
    authored_action = next(action for action in actions if action["action_id"] == "clear_old_road")
    assert authored_action == {
        "action_id": "clear_old_road",
        "action_key": "clear_old_road",
        "label": "Расчистить старую дорогу",
        "action_type": "action",
        "action_kind": "route_access",
        "source": "registry",
        "one_shot": True,
    }


def test_get_static_local_interaction_requirements_return_authored_gates() -> None:
    assert get_static_node_context_action_requirements(node_id="craft_town") == [
        {
            "node_id": "craft_town",
            "action_id": "trace_watchtower_bearing",
            "unlock_hint": "Сначала получить береговую наводку при первом прибытии в городок.",
            "requires_node_state_flag": "craft_arrival_notice_taken",
            "first_visit_only": True,
        }
    ]
    assert get_static_node_service_requirements(node_id="craft_town") == [
        {
            "node_id": "craft_town",
            "service_id": "craft_town_local_guidance",
            "service_key": "",
            "unlock_hint": "Сначала получить местную наводку при прибытии в городок.",
            "requires_destination_event_id": "craft_town_arrival_notice",
            "requires_destination_event_result_type": "settlement_notice",
        }
    ]


def test_get_static_node_state_overlays_returns_authored_notes_for_flags() -> None:
    assert get_static_node_state_overlays(node_id="forest_road", state_flags=["old_road_cleared"]) == [
        {
            "node_id": "forest_road",
            "state_flag": "old_road_cleared",
            "context_note": "У старой дороги видны следы недавней расчистки, и проход к руинам читается увереннее.",
            "detail_note": "Сломанные ветви и свежие борозды в грязи показывают, что завал уже разбирали совсем недавно.",
        }
    ]


def test_get_static_node_entry_overlays_returns_authored_first_return_and_state_sensitive_notes() -> None:
    assert get_static_node_entry_overlays(node_id="craft_town") == [
        {
            "node_id": "craft_town",
            "first_entry_type": "settlement_welcome",
            "first_entry_title": "Озёрный городок принимает путников",
            "first_entry_note": "Городок встречает группу как новый спокойный узел пути у воды.",
            "return_entry_type": "return_entry",
            "return_entry_title": "Возвращение в Озёрный городок",
            "return_entry_note": "Знакомые улицы и пристань быстро возвращают группе прежний ориентир.",
        }
    ]
    assert get_static_node_entry_overlays(node_id="forest_road", state_flags=["old_road_cleared"]) == [
        {
            "node_id": "forest_road",
            "state_flag": "old_road_cleared",
            "entry_type": "changed_place",
            "entry_title": "Лесная дорога изменилась",
            "entry_note": "У входа на лесную дорогу сразу заметно, что старый завал уже разобран и место ощущается иначе.",
        }
    ]


def test_get_static_node_destination_events_returns_authored_arrival_events() -> None:
    assert get_static_node_destination_events(node_id="craft_town", state_flags=[], visit_count=1) == [
        {
            "node_id": "craft_town",
            "event_id": "craft_town_arrival_notice",
            "label": "Береговая наводка у городка",
            "first_visit_only": True,
            "one_shot": True,
            "result_type": "settlement_notice",
            "title": "У причала быстро находят ориентиры",
            "summary": "На первом прибытии местные сразу указывают группе полезный береговой ориентир.",
            "result_summary": "Озёрный городок встречает группу короткой береговой наводкой и подсказывает, где проще держать следующий ход.",
            "discovered_notes": [
                "У причала советуют держаться видимой башни на берегу: так проще не потерять темп и не уйти в пустые дворы."
            ],
            "intel_entry_type": "guidance",
            "intel_title": "Береговая наводка из Озёрного городка",
            "reveal_node_ids": ["watchtower"],
            "node_state_flags": ["craft_arrival_notice_taken"],
            "node_state_summary": "В городке уже отмечено первое береговое указание, которое группа получила при прибытии.",
            "applied_effects": ["destination_notice:craft_town", "node_revealed:watchtower", "intel:guidance"],
            "tags": ["settlement", "guidance", "watchtower"],
            "required_state_flags": [],
        }
    ]
    assert get_static_node_destination_events(node_id="ruined_settlement", state_flags=["mine_path_shored"], visit_count=2)[0]["result_type"] == "changed_place_notice"
    assert get_static_node_destination_events(node_id="forest_settlement", state_flags=[], visit_count=1)[0]["event_id"] == "forest_settlement_hunters_warning"
    assert get_static_node_destination_events(node_id="ruined_settlement", state_flags=[], visit_count=1)[0]["event_id"] == "ruined_settlement_watchfire_trace"
    assert get_static_node_destination_events(node_id="northwatch_outpost", state_flags=[], visit_count=1)[0]["event_id"] == "northwatch_outpost_briefing"
    assert get_static_node_destination_events(node_id="ash_pass", state_flags=[], visit_count=1)[0]["result_type"] == "local_warning"
    assert get_static_node_destination_events(node_id="broken_redoubt", state_flags=[], visit_count=1)[0]["event_id"] == "broken_redoubt_supply_trace"


def test_get_static_region_gateways_returns_authored_frontier_exit_definitions() -> None:
    all_gateways = get_static_region_gateways(region_id="region")
    assert len(all_gateways) == 7
    assert get_static_node_region_gateways(node_id="forest_settlement") == [
        {
            "gateway_id": "forest_settlement_northwatch",
            "source_node_id": "forest_settlement",
            "route_id": "forest_settlement->old_fortress_edge:move",
            "target_region_id": "northwatch_frontier",
            "target_region_label": "Северный рубеж",
            "target_anchor_node_id": "northwatch_outpost",
            "label": "Выход к северному рубежу",
            "future_stub": False,
            "unlock_hint": "Сначала собрать лесные припасы перед дальним выходом к северному рубежу.",
            "requires_node_state_flag": "forest_supplies_secured",
        }
    ]
    assert get_static_node_region_gateways(node_id="northwatch_outpost") == [
        {
            "gateway_id": "northwatch_outpost_starter_frontier",
            "source_node_id": "northwatch_outpost",
            "route_id": "northwatch_outpost->northwatch_quartermaster:move",
            "target_region_id": "starter_frontier",
            "target_region_label": "Стартовое пограничье",
            "target_anchor_node_id": "forest_settlement",
            "label": "Тропа обратно к лесному посёлку",
            "future_stub": False,
            "unlock_hint": "Дозор держит обратную тропу открытой, пока погода не ломает северный подход.",
        }
    ]
    assert get_static_node_region_gateways(node_id="deep_marsh_threshold") == [
        {
            "gateway_id": "deep_marsh_threshold_starter_frontier",
            "source_node_id": "deep_marsh_threshold",
            "route_id": "deep_marsh_threshold->reed_shelter:move",
            "target_region_id": "starter_frontier",
            "target_region_label": "Стартовое пограничье",
            "target_anchor_node_id": "marsh_edge",
            "label": "Обратный ход к болотной кромке",
            "future_stub": False,
            "unlock_hint": "Пока держатся первые сухие кочки, обратный ход к кромке болот остаётся различимым.",
        }
    ]
    assert get_static_node_region_gateways(node_id="western_road_watch") == [
        {
            "gateway_id": "western_road_watch_starter_frontier",
            "source_node_id": "western_road_watch",
            "route_id": "western_road_watch->waystation_yard:move",
            "target_region_id": "starter_frontier",
            "target_region_label": "Стартовое пограничье",
            "target_anchor_node_id": "fortress_gate",
            "label": "Возврат к воротам крепости",
            "future_stub": False,
            "unlock_hint": "Пока тракт читается по первым дорожным меткам, обратный ход к воротам остаётся явным.",
        }
    ]
    assert get_static_node_region_gateways(node_id="forgotten_shrine")[0]["future_stub"] is True


def test_northwatch_frontier_registry_content_and_onboarding_are_real() -> None:
    identity = get_static_region_identity(node_id="northwatch_quartermaster")
    onboarding = get_static_region_onboarding("northwatch_frontier")

    assert identity is not None
    assert identity["region_id"] == "northwatch_frontier"
    assert set(identity["node_ids"]) >= {
        "northwatch_outpost",
        "northwatch_quartermaster",
        "northwatch_palisade",
        "ash_pass",
        "broken_redoubt",
    }
    assert onboarding is not None
    assert onboarding["anchor_node_id"] == "northwatch_outpost"
    assert onboarding["starter_reveal_node_ids"] == [
        "northwatch_quartermaster",
        "northwatch_palisade",
        "ash_pass",
    ]
    assert "northwatch_outpost->ash_pass:move" in onboarding["starter_reveal_route_ids"]


def test_northwatch_nodes_expose_services_actions_and_details() -> None:
    quartermaster_services = get_static_node_services(node_id="northwatch_quartermaster")
    palisade_actions = get_current_node_context_actions(node_id="northwatch_palisade")
    palisade_requirements = get_static_node_context_action_requirements(node_id="northwatch_palisade")
    palisade_effects = [
        item
        for item in get_static_node_context_action_effects(node_id="northwatch_palisade")
        if item["action_id"] == "set_relay_watch"
    ]

    assert [item["service_id"] for item in quartermaster_services] == [
        "northwatch_quartermaster:safe_rest",
        "northwatch_quartermaster_resupply",
        "northwatch_quartermaster:local_guidance",
    ]
    assert get_static_node_service_requirements(node_id="northwatch_quartermaster") == [
        {
            "node_id": "northwatch_quartermaster",
            "service_id": "northwatch_quartermaster_resupply",
            "service_key": "",
            "min_visit_count": 2,
            "return_visit_only": True,
            "unlock_hint": "Интендант открывает рубежный склад только тем, кто уже сходил на короткую вылазку по рубежу и вернулся с первой сводкой.",
        }
    ]
    assert any(item["action_id"] == "review_signal_chalk" for item in palisade_actions)
    assert any(item["action_id"] == "set_relay_watch" for item in palisade_actions)
    assert palisade_requirements == [
        {
            "node_id": "northwatch_palisade",
            "action_id": "set_relay_watch",
            "unlock_hint": "Палисада разворачивает relay-дозор только когда база уже начала тянуть наружу практическую рубежную поддержку.",
            "requires_any_group_node_state_flags": [
                "frontier_support_prepared",
                "frontier_support_ready",
                "frontier_support_committed",
            ],
        }
    ]
    assert len(palisade_effects) == 3
    assert all(item["reveal_node_ids"] == ["broken_redoubt"] for item in palisade_effects)
    redoubt_effect = next(
        item for item in get_static_node_service_effects(node_id="northwatch_quartermaster") if item["service_id"] == "northwatch_quartermaster_resupply"
    )
    assert redoubt_effect["node_state_flags"] == ["northwatch_quartermaster_supplies", "northwatch_redoubt_return_logged"]
    assert "обратный доклад" in redoubt_effect["result_summary"]
    quartermaster_actions = get_current_node_context_actions(node_id="northwatch_quartermaster")
    quartermaster_action_requirements = get_static_node_context_action_requirements(node_id="northwatch_quartermaster")
    assert any(item["action_id"] == "post_redoubt_orders" for item in quartermaster_actions)
    assert any(item["action_id"] == "confirm_redoubt_watch" for item in quartermaster_actions)
    assert {
        "node_id": "northwatch_quartermaster",
        "action_id": "confirm_redoubt_watch",
        "requires_node_state_flag": "northwatch_directive_posted",
        "unlock_hint": "Сначала разложить присланный redoubt order на интендантском дворе и только потом закреплять watch-line в поле.",
    } in quartermaster_action_requirements
    redoubt_actions = get_current_node_context_actions(node_id="broken_redoubt")
    redoubt_requirements = get_static_node_context_action_requirements(node_id="broken_redoubt")
    assert any(item["action_id"] == "log_redoubt_signal_cache" for item in redoubt_actions)
    assert redoubt_requirements == [
        {
            "node_id": "broken_redoubt",
            "action_id": "log_redoubt_signal_cache",
            "unlock_hint": "Сначала активировать relay-дозор на палисаде и уже на месте увидеть свежий след у редута.",
            "requires_any_group_node_state_flags": [
                "northwatch_relay_watch_prepared",
                "northwatch_relay_watch_ready",
                "northwatch_relay_watch_committed",
            ],
            "requires_destination_event_id": "broken_redoubt_supply_trace",
            "requires_destination_event_result_type": "first_discovery",
        }
    ]


def test_deep_marsh_registry_content_and_onboarding_are_real() -> None:
    identity = get_static_region_identity(node_id="reed_shelter")
    onboarding = get_static_region_onboarding("deep_marsh")

    assert identity is not None
    assert identity["region_id"] == "deep_marsh"
    assert set(identity["node_ids"]) >= {
        "deep_marsh_threshold",
        "reed_shelter",
        "drowned_waystone",
        "blackwater_run",
        "sunken_ferry",
    }
    assert onboarding is not None
    assert onboarding["anchor_node_id"] == "deep_marsh_threshold"
    assert onboarding["starter_reveal_node_ids"] == [
        "reed_shelter",
        "drowned_waystone",
        "blackwater_run",
    ]
    assert "deep_marsh_threshold->blackwater_run:move" in onboarding["starter_reveal_route_ids"]


def test_western_road_registry_content_and_onboarding_are_real() -> None:
    identity = get_static_region_identity(node_id="waystation_yard")
    onboarding = get_static_region_onboarding("western_road")

    assert identity is not None
    assert identity["region_id"] == "western_road"
    assert set(identity["node_ids"]) >= {
        "western_road_watch",
        "waystation_yard",
        "mile_marker_arch",
        "rutted_detour",
        "broken_waycart",
    }
    assert onboarding is not None
    assert onboarding["anchor_node_id"] == "western_road_watch"
    assert onboarding["starter_reveal_node_ids"] == [
        "waystation_yard",
        "mile_marker_arch",
        "rutted_detour",
    ]
    assert "western_road_watch->rutted_detour:move" in onboarding["starter_reveal_route_ids"]


def test_western_road_nodes_expose_services_actions_events_and_scout_discovery() -> None:
    yard_services = get_static_node_services(node_id="waystation_yard")
    yard_actions = get_current_node_context_actions(node_id="waystation_yard")
    yard_action_requirements = get_static_node_context_action_requirements(node_id="waystation_yard")
    marker_actions = get_current_node_context_actions(node_id="mile_marker_arch")
    marker_requirements = get_static_node_context_action_requirements(node_id="mile_marker_arch")
    marker_effects = [
        item
        for item in get_static_node_context_action_effects(node_id="mile_marker_arch")
        if item["action_id"] == "reset_detour_markers"
    ]

    assert [item["service_id"] for item in yard_services] == [
        "waystation_yard:safe_rest",
        "waystation_yard_resupply",
        "waystation_yard:local_guidance",
    ]
    assert get_static_node_service_requirements(node_id="waystation_yard") == [
        {
            "node_id": "waystation_yard",
            "service_id": "waystation_yard_resupply",
            "service_key": "",
            "min_visit_count": 2,
            "return_visit_only": True,
            "unlock_hint": "Постоялый двор собирает полный дорожный набор только тем, кто уже сходил по следу задержанного обоза и вернулся с дороги.",
        }
    ]
    assert any(item["action_id"] == "chalk_corridor_orders" for item in yard_actions)
    assert any(item["action_id"] == "stabilize_corridor_handling" for item in yard_actions)
    assert {
        "node_id": "waystation_yard",
        "action_id": "stabilize_corridor_handling",
        "requires_node_state_flag": "western_road_directive_posted",
        "unlock_hint": "Сначала отметить corridor order на дворе и только потом закреплять detour handling как рабочий порядок.",
    } in yard_action_requirements
    assert any(item["action_id"] == "read_waybill_marks" for item in marker_actions)
    assert any(item["action_id"] == "reset_detour_markers" for item in marker_actions)
    assert marker_requirements == [
        {
            "node_id": "mile_marker_arch",
            "action_id": "reset_detour_markers",
            "unlock_hint": "Detour-маркеры обновляют только когда с базы уже дошёл хотя бы первый practical support tier для дальних выходов.",
            "requires_any_group_node_state_flags": [
                "frontier_support_prepared",
                "frontier_support_ready",
                "frontier_support_committed",
            ],
        }
    ]
    assert len(marker_effects) == 3
    assert all(
        [route_update["route_id"] for route_update in item["route_access_updates"]] == [
            "rutted_detour->broken_waycart:move",
            "broken_waycart->rutted_detour:move",
        ]
        for item in marker_effects
    )
    scout_discovery = get_static_node_scout_discoveries(node_id="mile_marker_arch")
    assert scout_discovery == [
        {
            "node_id": "mile_marker_arch",
            "result_type": "landmark_revealed",
            "discovery_scope": "roadside_trace",
            "discovered_node_ids": ["broken_waycart"],
            "discovered_route_ids": ["rutted_detour->broken_waycart:move"],
            "discovered_notes": [
                "По дорожным пометкам на верстовой арке становится понятнее, где у разбитого объезда стоит брошенная повозка и почему след свежего обоза уходит именно туда."
            ],
        }
    ]
    assert get_static_node_destination_events(node_id="western_road_watch", state_flags=[], visit_count=1)[0]["event_id"] == "western_road_watch_delay_notice"
    assert get_static_node_destination_events(node_id="broken_waycart", state_flags=[], visit_count=1)[0]["event_id"] == "broken_waycart_trace"

    northwatch_effects = [
        item
        for item in get_static_node_service_effects(node_id="northwatch_quartermaster")
        if item["service_id"] == "northwatch_quartermaster_resupply"
    ]
    deep_marsh_effects = [
        item
        for item in get_static_node_service_effects(node_id="reed_shelter")
        if item["service_id"] == "reed_shelter_shrine_aid"
    ]
    western_effects = [
        item
        for item in get_static_node_service_effects(node_id="waystation_yard")
        if item["service_id"] == "waystation_yard_resupply"
    ]
    assert len(northwatch_effects) == 4
    assert len(deep_marsh_effects) == 4
    assert len(western_effects) == 4
    waycart_actions = get_current_node_context_actions(node_id="broken_waycart")
    waycart_requirements = get_static_node_context_action_requirements(node_id="broken_waycart")
    assert any(item["action_id"] == "sort_waycart_manifest" for item in waycart_actions)
    assert waycart_requirements == [
        {
            "node_id": "broken_waycart",
            "action_id": "sort_waycart_manifest",
            "unlock_hint": "Сначала обновить detour-маркеры у арки и уже у повозки найти свежий дорожный след.",
            "requires_any_group_node_state_flags": [
                "western_road_detour_markers_prepared",
                "western_road_detour_markers_ready",
                "western_road_detour_markers_committed",
            ],
            "requires_destination_event_id": "broken_waycart_trace",
            "requires_destination_event_result_type": "first_discovery",
        }
    ]


def test_deep_marsh_nodes_expose_services_actions_events_and_scout_discovery() -> None:
    shelter_services = get_static_node_services(node_id="reed_shelter")
    waystone_actions = get_current_node_context_actions(node_id="drowned_waystone")
    waystone_scout = get_static_node_scout_discoveries(node_id="drowned_waystone")
    shelter_actions = get_current_node_context_actions(node_id="reed_shelter")
    shelter_requirements = get_static_node_context_action_requirements(node_id="reed_shelter")
    shelter_effects = [
        item
        for item in get_static_node_context_action_effects(node_id="reed_shelter")
        if item["action_id"] == "braid_reed_wayline"
    ]

    assert [item["service_id"] for item in shelter_services] == [
        "reed_shelter:safe_rest",
        "reed_shelter_shrine_aid",
        "reed_shelter:local_guidance",
    ]
    assert get_static_node_service_requirements(node_id="reed_shelter") == [
        {
            "node_id": "reed_shelter",
            "service_id": "reed_shelter_shrine_aid",
            "service_key": "",
            "min_visit_count": 2,
            "return_visit_only": True,
            "unlock_hint": "Тростниковый приют открывает сухой настил только тем, кто уже сходил в сырой ход и вернулся до полной темноты.",
        }
    ]
    assert any(item["action_id"] == "read_moss_waymarks" for item in waystone_actions)
    assert any(item["action_id"] == "braid_reed_wayline" for item in shelter_actions)
    assert any(item["action_id"] == "tie_crossing_orders" for item in shelter_actions)
    assert any(item["action_id"] == "secure_crossing_line" for item in shelter_actions)
    assert {
        "node_id": "reed_shelter",
        "action_id": "braid_reed_wayline",
        "unlock_hint": "Тростниковую wayline имеет смысл плести только после того, как база реально начала поддерживать дальние возвраты.",
        "requires_any_group_node_state_flags": [
            "frontier_support_prepared",
            "frontier_support_ready",
            "frontier_support_committed",
        ],
    } in shelter_requirements
    assert {
        "node_id": "reed_shelter",
        "action_id": "secure_crossing_line",
        "requires_node_state_flag": "deep_marsh_directive_posted",
        "unlock_hint": "Сначала связать присланный crossing order у приюта и только потом закреплять quiet crossing line.",
    } in shelter_requirements
    assert len(shelter_effects) == 3
    assert all(item["reveal_node_ids"] == ["sunken_ferry"] for item in shelter_effects)
    assert all(
        [route_update["route_id"] for route_update in item["route_access_updates"]] == [
            "blackwater_run->sunken_ferry:move",
            "sunken_ferry->blackwater_run:move",
        ]
        for item in shelter_effects
    )
    assert waystone_scout == [
        {
            "node_id": "drowned_waystone",
            "result_type": "landmark_revealed",
            "discovery_scope": "marsh_waymark",
            "discovered_node_ids": ["sunken_ferry"],
            "discovered_route_ids": ["blackwater_run->sunken_ferry:move"],
            "discovered_notes": [
                "По болотным зарубкам у камня становится понятнее, где за чёрной протокой проступает затонувшая переправа и как к ней держать короткий рискованный ход."
            ],
        }
    ]
    assert get_static_node_destination_events(node_id="deep_marsh_threshold", state_flags=[], visit_count=1)[0]["event_id"] == "deep_marsh_mist_notice"
    assert get_static_node_destination_events(node_id="sunken_ferry", state_flags=[], visit_count=1)[0]["event_id"] == "sunken_ferry_trace"
    ferry_actions = get_current_node_context_actions(node_id="sunken_ferry")
    ferry_requirements = get_static_node_context_action_requirements(node_id="sunken_ferry")
    assert any(item["action_id"] == "trace_ferry_moorings" for item in ferry_actions)
    assert ferry_requirements == [
        {
            "node_id": "sunken_ferry",
            "action_id": "trace_ferry_moorings",
            "unlock_hint": "Сначала протянуть wayline от приюта и уже на переправе увидеть свежий болотный след.",
            "requires_any_group_node_state_flags": [
                "deep_marsh_wayline_prepared",
                "deep_marsh_wayline_ready",
                "deep_marsh_wayline_committed",
            ],
            "requires_destination_event_id": "sunken_ferry_trace",
            "requires_destination_event_result_type": "first_discovery",
        }
    ]


def test_starter_frontier_nodes_expose_local_progression_arc_surfaces() -> None:
    forest_services = get_static_node_services(node_id="forest_settlement")
    forest_requirements = get_static_node_service_requirements(node_id="forest_settlement")
    forest_effect = next(
        item for item in get_static_node_service_effects(node_id="forest_settlement") if item["service_id"] == "forest_settlement_resupply"
    )
    support_effects = [
        item
        for item in get_static_node_service_effects(node_id="forest_settlement")
        if item["service_id"] == "forest_settlement_frontier_support"
    ]
    forest_actions = get_current_node_context_actions(node_id="forest_settlement")
    forest_action_requirements = get_static_node_context_action_requirements(node_id="forest_settlement")

    assert [item["service_id"] for item in forest_services] == [
        "forest_settlement:safe_rest",
        "forest_settlement_resupply",
        "forest_settlement:local_guidance",
        "forest_settlement_frontier_support",
    ]
    assert forest_requirements == [
        {
            "node_id": "forest_settlement",
            "service_id": "forest_settlement_resupply",
            "service_key": "",
            "requires_destination_event_id": "forest_settlement_hunters_warning",
            "requires_destination_event_result_type": "settlement_notice",
            "min_visit_count": 2,
            "unlock_hint": "Полный лесной набор выдают только после первой охотничьей сводки и повторного захода в посёлок.",
        },
        {
            "node_id": "forest_settlement",
            "service_id": "forest_settlement_frontier_support",
            "service_key": "",
            "unlock_hint": "Сначала свести хотя бы первую frontier-сводку по внешнему рубежу.",
            "requires_node_state_flag": "frontier_report_started",
        }
    ]
    assert forest_effect["node_state_flags"] == ["forest_supplies_secured", "forest_return_report_logged"]
    assert "обратный рассказ" in forest_effect["result_summary"]
    assert len(support_effects) == 3
    assert [item["required_state_flags"] for item in support_effects] == [
        ["frontier_report_started"],
        ["frontier_pattern_seen"],
        ["frontier_full_pattern_logged"],
    ]
    assert any(item["action_id"] == "compile_frontier_report" for item in forest_actions)
    assert any(item["action_id"] == "arrange_frontier_evidence" for item in forest_actions)
    assert any(item["action_id"] == "issue_frontier_directives" for item in forest_actions)
    assert forest_action_requirements == [
        {
            "node_id": "forest_settlement",
            "action_id": "compile_frontier_report",
            "unlock_hint": "Сначала вернуться хотя бы с одного подтверждённого дальнего доклада с соседнего рубежа.",
            "requires_any_group_node_state_flags": [
                "northwatch_redoubt_return_logged",
                "deep_marsh_shelter_aid_received",
                "western_road_waystation_aid_received",
            ],
        },
        {
            "node_id": "forest_settlement",
            "action_id": "arrange_frontier_evidence",
            "unlock_hint": "Сначала вернуть домой хотя бы один конкретный field proof с activated frontier branch.",
            "requires_any_group_node_state_flags": [
                "northwatch_redoubt_cache_logged",
                "deep_marsh_ferry_moorings_logged",
                "western_road_waycart_manifest_logged",
            ],
        },
        {
            "node_id": "forest_settlement",
            "action_id": "issue_frontier_directives",
            "unlock_hint": "Сначала собрать хотя бы первую returned frontier evidence picture по activated field proofs.",
            "requires_node_state_flag": "frontier_evidence_started",
            "requires_any_group_node_state_flags": [
                "northwatch_redoubt_cache_logged",
                "deep_marsh_ferry_moorings_logged",
                "western_road_waycart_manifest_logged",
            ],
        },
    ]
    northwatch_actions = get_current_node_context_actions(node_id="northwatch_quartermaster")
    northwatch_action_requirements = get_static_node_context_action_requirements(node_id="northwatch_quartermaster")
    assert any(item["action_id"] == "post_redoubt_orders" for item in northwatch_actions)
    assert any(item["action_id"] == "confirm_redoubt_watch" for item in northwatch_actions)
    assert {
        "node_id": "northwatch_quartermaster",
        "action_id": "post_redoubt_orders",
        "requires_any_group_node_state_flags": ["northwatch_field_directive_issued"],
        "unlock_hint": "Сначала вернуть evidence домой и дождаться, пока база отправит назад redoubt directive на северный рубеж.",
    } in northwatch_action_requirements
    assert {
        "node_id": "northwatch_quartermaster",
        "action_id": "confirm_redoubt_watch",
        "requires_node_state_flag": "northwatch_directive_posted",
        "unlock_hint": "Сначала разложить присланный redoubt order на интендантском дворе и только потом закреплять watch-line в поле.",
    } in northwatch_action_requirements
    marsh_actions = get_current_node_context_actions(node_id="reed_shelter")
    marsh_action_requirements = get_static_node_context_action_requirements(node_id="reed_shelter")
    assert any(item["action_id"] == "tie_crossing_orders" for item in marsh_actions)
    assert any(item["action_id"] == "secure_crossing_line" for item in marsh_actions)
    assert {
        "node_id": "reed_shelter",
        "action_id": "tie_crossing_orders",
        "requires_any_group_node_state_flags": ["deep_marsh_field_directive_issued"],
        "unlock_hint": "Сначала вернуть болотный evidence домой и дождаться, пока база отправит назад crossing directive.",
    } in marsh_action_requirements
    assert {
        "node_id": "reed_shelter",
        "action_id": "secure_crossing_line",
        "requires_node_state_flag": "deep_marsh_directive_posted",
        "unlock_hint": "Сначала связать присланный crossing order у приюта и только потом закреплять quiet crossing line.",
    } in marsh_action_requirements
    road_actions = get_current_node_context_actions(node_id="waystation_yard")
    road_action_requirements = get_static_node_context_action_requirements(node_id="waystation_yard")
    assert any(item["action_id"] == "chalk_corridor_orders" for item in road_actions)
    assert any(item["action_id"] == "stabilize_corridor_handling" for item in road_actions)
    assert {
        "node_id": "waystation_yard",
        "action_id": "chalk_corridor_orders",
        "requires_any_group_node_state_flags": ["western_road_field_directive_issued"],
        "unlock_hint": "Сначала вернуть дорожный evidence домой и дождаться, пока база отправит назад corridor directive.",
    } in road_action_requirements
    assert {
        "node_id": "waystation_yard",
        "action_id": "stabilize_corridor_handling",
        "requires_node_state_flag": "western_road_directive_posted",
        "unlock_hint": "Сначала отметить corridor order на дворе и только потом закреплять detour handling как рабочий порядок.",
    } in road_action_requirements
    assert any(item["action_id"] == "clear_old_road" for item in get_current_node_context_actions(node_id="forest_road"))


def test_static_node_detail_and_inspect_result_expose_handcrafted_content() -> None:
    assert get_static_node_detail(node_id="craft_town") == {
        "node_id": "craft_town",
        "label": "Озёрный городок",
        "node_type": "zone",
        "area_label": "Озёрный городок",
        "short_description": "Небольшой ремесленный городок у воды с пристанью, мастерскими и постоялым двором.",
        "inspect_summary": "Здесь легко пополнить припасы, переждать дорогу и собрать слухи о ближних тропах.",
        "travel_note": "Самая надёжная безопасная точка региона перед выходом в пограничные земли.",
        "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
    }
    assert get_static_node_detail(node_id="ruined_settlement") == {
        "node_id": "ruined_settlement",
        "label": "Разрушенный посёлок",
        "node_type": "zone",
        "area_label": "Разрушенный посёлок",
        "short_description": "Пустые улицы и обгоревшие дворы оставили от посёлка лишь редкие укрытия и плохие следы.",
        "inspect_summary": "Руины ведут к шахтному входу, но вокруг много слепых углов и тревожной тишины.",
        "travel_note": "Стоянка здесь рискованна; двигаться лучше короткими переходами и с дозором.",
        "danger_note": "Высокий риск засады и скрытых проходов между руинами.",
    }
    assert get_static_node_inspect_result(node_id="mine_entrance", source="test") == {
        "node_id": "mine_entrance",
        "label": "Шахтный вход",
        "node_type": "interior_entry",
        "inspect_summary": "Перед спуском можно заметить свежие следы, обваленные крепи и узкий безопасный проход.",
        "short_description": "Чёрный провал шахтного входа уходит под холм и пахнет сыростью, ржавчиной и старой пылью.",
        "travel_note": "Порог между открытыми руинами и тесным опасным подземельем.",
        "service_hints": None,
        "danger_note": "Внутри легко потерять обзор и отход к поверхности.",
        "source": "test",
    }


def test_static_node_services_and_service_results_expose_handcrafted_service_surface() -> None:
    assert get_static_node_services(node_id="craft_town") == [
        {
            "service_id": "craft_town:safe_rest",
            "service_key": "safe_rest",
            "label": "Безопасный отдых",
            "service_type": "rest",
            "service_kind": "rest",
            "summary": "Можно перевести дух и переждать путь в сравнительно безопасных условиях.",
            "source": "registry",
            "available": True,
            "status": "available",
            "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
        },
        {
            "service_id": "craft_town:resupply",
            "service_key": "resupply",
            "label": "Пополнение припасов",
            "service_type": "supplies",
            "service_kind": "supplies",
            "summary": "Здесь можно пополнить базовые дорожные запасы перед выходом.",
            "source": "registry",
            "available": True,
            "status": "available",
            "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
        },
        {
            "service_id": "craft_town_local_guidance",
            "service_key": "local_guidance",
            "label": "Местные указания",
            "service_type": "guidance",
            "service_kind": "guidance",
            "summary": "Здесь можно получить ориентиры, слухи и безопасные подсказки по ближайшим дорогам.",
            "source": "registry",
            "available": True,
            "status": "available",
            "one_shot": True,
            "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
        },
        {
            "service_id": "craft_town:healing_aid",
            "service_key": "healing_aid",
            "label": "Помощь с ранами",
            "service_type": "aid",
            "service_kind": "aid",
            "summary": "На месте можно получить перевязку, уход или базовую помощь после дороги.",
            "source": "registry",
            "available": True,
            "status": "available",
            "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
        },
    ]
    assert get_static_node_services(node_id="ruined_settlement") == []
    assert get_static_node_service_result(node_id="chapel_village", service_key="shrine_aid", source="test") == {
        "service_id": "chapel_village_shrine_aid",
        "service_key": "shrine_aid",
        "service_label": "Поддержка у святыни",
        "label": "Поддержка у святыни",
        "service_type": "shrine",
        "service_kind": "shrine",
        "summary": "Здесь могут дать тихий приют, совет или скромную духовную помощь.",
        "node_id": "chapel_village",
        "node_label": "Часовенное село",
        "source": "test",
        "result_summary": "У святыни можно получить благословение, тишину и скромную помощь в дороге.",
        "service_hints": ["убежище при часовне", "местные слухи"],
    }
    assert get_static_node_service_effects(node_id="craft_town") == [
        {
            "node_id": "craft_town",
            "service_key": "local_guidance",
            "service_id": "craft_town_local_guidance",
            "service_kind": "guidance",
            "result_type": "guidance_received",
            "summary": "Получить у местных проверенную дорожную наводку.",
            "result_summary": "Городские проводники отмечают для группы надёжный береговой ориентир у сторожевой башни.",
            "source": "registry",
            "one_shot": True,
            "discovered_notes": ["Местные советуют держаться берегового ориентира у сторожевой башни: там проще не потерять темп и не свернуть в пустые дворы."],
            "reveal_node_ids": ["watchtower"],
            "applied_effects": ["guidance_recorded", "node_revealed:watchtower"],
            "node_state_flags": ["craft_guidance_taken"],
            "node_state_summary": "В городке уже собраны местные указания по береговому ориентиру у сторожевой башни.",
        }
    ]


def test_resolve_static_map_node_supports_labels_and_aliases() -> None:
    assert resolve_static_map_node("ворота крепости") == {
        "node_id": "fortress_gate",
        "label": "Ворота крепости",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Стартовый тракт",
        "zone_band": "safe",
        "poi_kind": "fortified",
        "environment_hint": "fortified",
        "safe_rest_hint": False,
        "short_description": "Каменные ворота крепости возвышаются над трактом и задают ритм всему безопасному ядру региона.",
        "inspect_summary": "У ворот хорошо видно дорогу, подходы к городку и кто проходит в сторону границы.",
        "travel_note": "Надёжный ориентир и точка встречи перед выходом в опасные земли.",
        "service_hints": ["караул", "укрытие у стены"],
        "services": ["safe_rest", "local_guidance"],
        "aliases": (
            "ворота крепости",
            "крепостные ворота",
            "ворота",
        ),
    }
    assert resolve_static_map_node("иду к шахте") == {
        "node_id": "mine_entrance",
        "label": "Шахтный вход",
        "node_type": "interior_entry",
        "map_level": "interior",
        "area_label": "Разрушенный посёлок",
        "zone_band": "danger",
        "poi_kind": "mine",
        "environment_hint": "ruined_frontier",
        "safe_rest_hint": False,
        "short_description": "Чёрный провал шахтного входа уходит под холм и пахнет сыростью, ржавчиной и старой пылью.",
        "inspect_summary": "Перед спуском можно заметить свежие следы, обваленные крепи и узкий безопасный проход.",
        "travel_note": "Порог между открытыми руинами и тесным опасным подземельем.",
        "danger_note": "Внутри легко потерять обзор и отход к поверхности.",
        "aliases": (
            "шахтный вход",
            "вход в шахту",
            "шахта",
            "шахте",
            "к шахте",
        ),
    }
    assert resolve_static_map_node("ремесленный городок") == {
        "node_id": "craft_town",
        "label": "Озёрный городок",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Озёрный городок",
        "zone_band": "safe",
        "settlement_kind": "town",
        "environment_hint": "lakeshore",
        "safe_rest_hint": True,
        "short_description": "Небольшой ремесленный городок у воды с пристанью, мастерскими и постоялым двором.",
        "inspect_summary": "Здесь легко пополнить припасы, переждать дорогу и собрать слухи о ближних тропах.",
        "travel_note": "Самая надёжная безопасная точка региона перед выходом в пограничные земли.",
        "service_hints": ["припасы", "постоялый двор", "ремесленные мастерские"],
        "services": ["safe_rest", "resupply", "local_guidance", "healing_aid"],
        "aliases": (
            "озёрный городок",
            "ремесленный городок",
            "городок у озера",
            "городок",
        ),
    }
    assert resolve_static_map_node("старое святилище") == {
        "node_id": "forgotten_shrine",
        "label": "Забытое святилище",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Край болот",
        "zone_band": "danger",
        "poi_kind": "shrine",
        "environment_hint": "marsh",
        "safe_rest_hint": False,
        "aliases": (
            "забытое святилище",
            "святилище в болотах",
            "старое святилище",
        ),
    }


def test_resolve_action_target_node_prefers_static_registry_for_move_text() -> None:
    target = resolve_action_target_node(
        action_text="иду к воротам крепости",
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
        current_area_label="Стартовый тракт",
        action_kind="move",
        known_node_ids={"fortress_gate"},
        require_known_static=True,
    )

    assert target == {
        "map_level": "landmark",
        "node_type": "landmark",
        "node_id": "fortress_gate",
        "label": "Ворота крепости",
        "zone_label": "Стартовый тракт",
        "area_label": "Стартовый тракт",
        "zone_band": "safe",
        "poi_kind": "fortified",
        "environment_hint": "fortified",
        "safe_rest_hint": False,
    }


def test_resolve_action_target_node_prefers_static_registry_for_enter_text() -> None:
    target = resolve_action_target_node(
        target_text="шахта",
        current_area_label="Разрушенный посёлок",
        action_kind="enter",
        known_node_ids={"mine_entrance"},
        require_known_static=True,
    )

    assert target == {
        "map_level": "interior",
        "node_type": "interior_entry",
        "node_id": "mine_entrance",
        "label": "Шахтный вход",
        "zone_label": "Разрушенный посёлок",
        "area_label": "Разрушенный посёлок",
        "zone_band": "danger",
        "poi_kind": "mine",
        "environment_hint": "ruined_frontier",
        "safe_rest_hint": False,
    }


def test_resolve_action_target_node_falls_back_to_heuristic_if_registry_has_no_match() -> None:
    target = resolve_action_target_node(
        action_text="выхожу на улицу",
        current_area_label="Старый подвал",
        action_kind="move",
    )

    assert target == {
        "map_level": "region",
        "node_type": "zone",
        "node_id": "улица у таверны",
        "label": "улица у таверны",
        "zone_label": "улица у таверны",
        "area_label": "улица у таверны",
    }


def test_resolve_action_target_node_blocks_unknown_static_target_in_strict_known_mode() -> None:
    target = resolve_action_target_node(
        action_text="иду к воротам крепости",
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
        current_area_label="Стартовый тракт",
        action_kind="move",
        known_node_ids={"start_trakt"},
        require_known_static=True,
    )

    assert target is None


def test_validate_group_target_transition_allows_move_zone_and_landmark() -> None:
    assert validate_group_target_transition(
        action_kind="move",
        target_node={
            "map_level": "region",
            "node_type": "zone",
            "node_id": "eastern_bank",
            "label": "Восточный берег",
            "zone_label": "Восточный берег",
        },
    ) == (True, None)
    assert validate_group_target_transition(
        action_kind="move",
        target_node={
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "fortress_gate",
            "label": "Ворота крепости",
            "zone_label": "Стартовый тракт",
        },
    ) == (True, None)


def test_validate_group_target_transition_allows_enter_interior_entry() -> None:
    assert validate_group_target_transition(
        action_kind="enter",
        target_node={
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "mine_entrance",
            "label": "Шахтный вход",
            "zone_label": "Лесная дорога",
        },
    ) == (True, None)


def test_validate_group_target_transition_rejects_enter_zone_with_clear_error() -> None:
    valid, error = validate_group_target_transition(
        action_kind="enter",
        target_node={
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
            "zone_label": "Стартовый тракт",
        },
    )

    assert valid is False
    assert error == "Для `group enter` нужна interior/building цель, а не обычная zone."


def test_resolve_group_target_route_zone_to_zone_move_valid() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
        target_node={
            "map_level": "region",
            "node_type": "zone",
            "node_id": "eastern_bank",
            "label": "Восточный берег",
            "zone_label": "Восточный берег",
            "area_label": "Восточный берег",
        },
        action_kind="move",
    )

    assert route["allowed"] is True
    assert route["route_kind"] == "zone_move"
    assert route["action_kind"] == "move"
    assert route["source"] == "registry"
    assert route["traversal_kind"] == "road"
    assert route["risk_band"] == "low"
    assert route["terrain_hint"] == "open"
    assert route["target_node_type"] == "zone"
    assert route["target_node_id"] == "eastern_bank"


def test_resolve_group_target_route_zone_to_landmark_move_valid() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
        target_node={
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "fortress_gate",
            "label": "Ворота крепости",
            "zone_label": "Стартовый тракт",
            "area_label": "Стартовый тракт",
        },
        action_kind="move",
    )

    assert route["allowed"] is True
    assert route["route_kind"] == "landmark_move"
    assert route["source"] == "registry"
    assert route["traversal_kind"] == "gate_approach"
    assert route["risk_band"] == "low"
    assert route["terrain_hint"] == "fortified"
    assert route["target_node_type"] == "landmark"
    assert route["target_node_id"] == "fortress_gate"


def test_resolve_group_target_route_zone_to_interior_entry_enter_valid() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "ruined_settlement",
            "label": "Разрушенный посёлок",
        },
        target_node={
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "mine_entrance",
            "label": "Шахтный вход",
            "zone_label": "Разрушенный посёлок",
            "area_label": "Разрушенный посёлок",
        },
        action_kind="enter",
    )

    assert route["allowed"] is True
    assert route["route_kind"] == "enter_location"
    assert route["action_kind"] == "enter"
    assert route["source"] == "registry"
    assert route["traversal_kind"] == "entry"
    assert route["risk_band"] == "high"
    assert route["terrain_hint"] == "ruins"


def test_resolve_group_target_route_registry_missing_link_is_authoritative_error() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
        target_node={
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "watchtower",
            "label": "Сторожевая башня",
            "zone_label": "Восточный берег",
            "area_label": "Восточный берег",
        },
        action_kind="move",
    )

    assert route["allowed"] is False
    assert route["route_kind"] == "invalid"
    assert route["error"] == "Для известных узлов карты нет допустимого перехода по registry link."


def test_resolve_group_target_route_zone_to_interior_entry_move_invalid() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "ruined_settlement",
            "label": "Разрушенный посёлок",
        },
        target_node={
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "mine_entrance",
            "label": "Шахтный вход",
            "zone_label": "Разрушенный посёлок",
            "area_label": "Разрушенный посёлок",
        },
        action_kind="move",
    )

    assert route["allowed"] is False
    assert route["route_kind"] == "invalid"
    assert route["error"] == "Для `group move` допустимы только zone или landmark цели."


def test_resolve_group_target_route_safe_and_danger_links_use_expanded_registry() -> None:
    safe_route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "craft_town",
            "label": "Озёрный городок",
        },
        target_node={
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "fortress_gate",
            "label": "Ворота крепости",
            "zone_label": "Стартовый тракт",
            "area_label": "Стартовый тракт",
        },
        action_kind="move",
    )
    danger_route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "marsh_edge",
            "label": "Край болот",
        },
        target_node={
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "forgotten_shrine",
            "label": "Забытое святилище",
            "zone_label": "Край болот",
            "area_label": "Край болот",
        },
        action_kind="move",
    )

    assert safe_route["allowed"] is True
    assert safe_route["route_kind"] == "landmark_move"
    assert safe_route["traversal_kind"] == "gate_approach"
    assert danger_route["allowed"] is True
    assert danger_route["target_node_id"] == "forgotten_shrine"
    assert danger_route["risk_band"] == "high"
    assert danger_route["terrain_hint"] == "marsh"


def test_resolve_group_target_route_zone_enter_zone_invalid() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "start_trakt",
            "label": "Стартовый тракт",
        },
        target_node={
            "map_level": "region",
            "node_type": "zone",
            "node_id": "eastern_bank",
            "label": "Восточный берег",
            "zone_label": "Восточный берег",
            "area_label": "Восточный берег",
        },
        action_kind="enter",
    )

    assert route["allowed"] is False
    assert route["source"] == "fallback"
    assert route["error"] == "Для `group enter` нужна interior/building цель, а не обычная zone."


def test_resolve_group_target_route_landmark_to_interior_entry_enter_falls_back_when_registry_data_missing() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "ворота",
            "label": "ворота",
            "area_label": "центр города",
        },
        target_node={
            "map_level": "interior",
            "node_type": "interior_entry",
            "node_id": "замок",
            "label": "замок",
            "zone_label": "центр города",
            "area_label": "центр города",
        },
        action_kind="enter",
    )

    assert route["allowed"] is True
    assert route["route_kind"] == "enter_location"
    assert route["action_kind"] == "enter"
    assert route["source"] == "fallback"
    assert route["traversal_kind"] == "entry"


def test_resolve_group_target_route_falls_back_when_registry_data_is_missing() -> None:
    route = resolve_group_target_route(
        current_map_position={
            "v": 1,
            "map_level": "region",
            "node_type": "zone",
            "node_id": "неизвестная поляна",
            "label": "неизвестная поляна",
        },
        target_node={
            "map_level": "landmark",
            "node_type": "landmark",
            "node_id": "ворота",
            "label": "ворота",
            "zone_label": "неизвестная поляна",
            "area_label": "неизвестная поляна",
        },
        action_kind="move",
    )

    assert route["allowed"] is True
    assert route["route_kind"] == "landmark_move"
    assert route["target_node_id"] == "ворота"
    assert route["source"] == "fallback"
    assert route["risk_band"] == "medium"
    assert route["terrain_hint"] == "mixed"
