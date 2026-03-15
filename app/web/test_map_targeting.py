from __future__ import annotations

from app.web.map_registry import (
    find_static_link,
    get_current_node_context_actions,
    get_obvious_linked_static_node_ids,
    get_static_node_detail,
    get_static_node_context,
    get_static_node_service_effects,
    get_static_node_inspect_result,
    get_static_node_state_overlays,
    get_static_node_service_result,
    get_static_node_services,
    get_static_navigation_options,
    get_static_link_metadata,
    get_static_map_links,
    get_static_map_nodes,
    get_static_node_metadata,
    get_static_node,
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


def test_get_static_node_state_overlays_returns_authored_notes_for_flags() -> None:
    assert get_static_node_state_overlays(node_id="forest_road", state_flags=["old_road_cleared"]) == [
        {
            "node_id": "forest_road",
            "state_flag": "old_road_cleared",
            "context_note": "У старой дороги видны следы недавней расчистки, и проход к руинам читается увереннее.",
            "detail_note": "Сломанные ветви и свежие борозды в грязи показывают, что завал уже разбирали совсем недавно.",
        }
    ]


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
