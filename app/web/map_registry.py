from __future__ import annotations

from typing import Any


STATIC_MAP_NODES: tuple[dict[str, Any], ...] = (
    {
        "node_id": "start_trakt",
        "label": "Стартовый тракт",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Стартовый тракт",
        "zone_band": "safe",
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
    },
    {
        "node_id": "eastern_bank",
        "label": "Восточный берег",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Восточный берег",
        "zone_band": "safe",
        "aliases": (
            "восточный берег",
            "берег",
            "берег реки",
        ),
    },
    {
        "node_id": "craft_town",
        "label": "Озёрный городок",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Озёрный городок",
        "zone_band": "safe",
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
    },
    {
        "node_id": "forest_road",
        "label": "Лесная дорога",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Лесная дорога",
        "zone_band": "border",
        "aliases": (
            "лесная дорога",
            "лесная тропа",
            "дорога в лес",
        ),
    },
    {
        "node_id": "road_hamlet",
        "label": "Дорожный хутор",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Дорожный хутор",
        "zone_band": "border",
        "services": ["safe_rest", "resupply", "local_guidance"],
        "aliases": (
            "дорожный хутор",
            "хутор у тракта",
            "хутор",
        ),
    },
    {
        "node_id": "chapel_village",
        "label": "Часовенное село",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Часовенное село",
        "zone_band": "border",
        "short_description": "Малое село вокруг старой часовни, где путники ищут приют на границе обжитых мест.",
        "inspect_summary": "Жители держатся настороженно, но могут подсказать безопасную дорогу и где не ночевать.",
        "travel_note": "Удобная пограничная остановка между берегом и лесными дорогами.",
        "service_hints": ["убежище при часовне", "местные слухи"],
        "services": ["safe_rest", "local_guidance", "shrine_aid", "healing_aid"],
        "aliases": (
            "часовенное село",
            "часовня",
            "село у часовни",
        ),
    },
    {
        "node_id": "forest_settlement",
        "label": "Лесной посёлок",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Лесной посёлок",
        "zone_band": "border",
        "short_description": "Лесной посёлок на краю чащи, где охотники и сборщики держат последние безопасные дворы.",
        "inspect_summary": "Отсюда видно, где лес ещё под контролем людей, а где начинаются старые опасные руины.",
        "travel_note": "Последняя относительно спокойная стоянка перед дорогой к старой крепости.",
        "service_hints": ["охотничьи припасы", "ночлег под крышей"],
        "services": ["safe_rest", "resupply", "local_guidance"],
        "aliases": (
            "лесной посёлок",
            "посёлок в лесу",
            "лесное селение",
        ),
    },
    {
        "node_id": "ruined_settlement",
        "label": "Разрушенный посёлок",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Разрушенный посёлок",
        "zone_band": "danger",
        "short_description": "Пустые улицы и обгоревшие дворы оставили от посёлка лишь редкие укрытия и плохие следы.",
        "inspect_summary": "Руины ведут к шахтному входу, но вокруг много слепых углов и тревожной тишины.",
        "travel_note": "Стоянка здесь рискованна; двигаться лучше короткими переходами и с дозором.",
        "danger_note": "Высокий риск засады и скрытых проходов между руинами.",
        "aliases": (
            "разрушенный посёлок",
            "руины посёлка",
            "развалины",
        ),
    },
    {
        "node_id": "marsh_edge",
        "label": "Край болот",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Край болот",
        "zone_band": "danger",
        "aliases": (
            "край болот",
            "болотная кромка",
            "болота",
        ),
    },
    {
        "node_id": "fortress_gate",
        "label": "Ворота крепости",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Стартовый тракт",
        "zone_band": "safe",
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
    },
    {
        "node_id": "watchtower",
        "label": "Сторожевая башня",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Восточный берег",
        "zone_band": "border",
        "short_description": "Старая сторожевая башня над берегом всё ещё даёт хороший обзор на тропы и воду.",
        "inspect_summary": "Сверху можно быстро понять, куда уходит дорога и где граница безопасных мест.",
        "travel_note": "Полезная точка обзора перед выходом в пограничные зоны.",
        "aliases": (
            "сторожевая башня",
            "башня",
            "смотровая башня",
        ),
    },
    {
        "node_id": "old_fortress_edge",
        "label": "Край старой крепости",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Лесной посёлок",
        "zone_band": "danger",
        "aliases": (
            "старая крепость",
            "край старой крепости",
            "старые руины крепости",
        ),
    },
    {
        "node_id": "forgotten_shrine",
        "label": "Забытое святилище",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Край болот",
        "zone_band": "danger",
        "aliases": (
            "забытое святилище",
            "святилище в болотах",
            "старое святилище",
        ),
    },
    {
        "node_id": "mine_entrance",
        "label": "Шахтный вход",
        "node_type": "interior_entry",
        "map_level": "interior",
        "area_label": "Разрушенный посёлок",
        "zone_band": "danger",
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
    },
)


STATIC_MAP_LINKS: tuple[dict[str, str], ...] = (
    {
        "from_node_id": "start_trakt",
        "to_node_id": "eastern_bank",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "eastern_bank",
        "to_node_id": "start_trakt",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "start_trakt",
        "to_node_id": "craft_town",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "craft_town",
        "to_node_id": "start_trakt",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "craft_town",
        "to_node_id": "eastern_bank",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "shore_road",
    },
    {
        "from_node_id": "eastern_bank",
        "to_node_id": "craft_town",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "shore_road",
    },
    {
        "from_node_id": "craft_town",
        "to_node_id": "fortress_gate",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
    },
    {
        "from_node_id": "fortress_gate",
        "to_node_id": "craft_town",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "start_trakt",
        "to_node_id": "forest_road",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "forest_road",
        "to_node_id": "start_trakt",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "start_trakt",
        "to_node_id": "fortress_gate",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
    },
    {
        "from_node_id": "fortress_gate",
        "to_node_id": "start_trakt",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "eastern_bank",
        "to_node_id": "watchtower",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
    },
    {
        "from_node_id": "watchtower",
        "to_node_id": "eastern_bank",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "forest_road",
        "to_node_id": "road_hamlet",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "road_hamlet",
        "to_node_id": "forest_road",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "road_hamlet",
        "to_node_id": "chapel_village",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "branch_road",
    },
    {
        "from_node_id": "chapel_village",
        "to_node_id": "road_hamlet",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "branch_road",
    },
    {
        "from_node_id": "eastern_bank",
        "to_node_id": "chapel_village",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "shore_track",
    },
    {
        "from_node_id": "chapel_village",
        "to_node_id": "eastern_bank",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "shore_track",
    },
    {
        "from_node_id": "forest_road",
        "to_node_id": "forest_settlement",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "forest_track",
    },
    {
        "from_node_id": "forest_settlement",
        "to_node_id": "forest_road",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "forest_track",
    },
    {
        "from_node_id": "forest_road",
        "to_node_id": "ruined_settlement",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "old_road",
    },
    {
        "from_node_id": "ruined_settlement",
        "to_node_id": "forest_road",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "old_road",
    },
    {
        "from_node_id": "forest_settlement",
        "to_node_id": "old_fortress_edge",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "ruin_path",
    },
    {
        "from_node_id": "old_fortress_edge",
        "to_node_id": "forest_settlement",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "ruined_settlement",
        "to_node_id": "marsh_edge",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "bog_track",
    },
    {
        "from_node_id": "marsh_edge",
        "to_node_id": "ruined_settlement",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "bog_track",
    },
    {
        "from_node_id": "marsh_edge",
        "to_node_id": "forgotten_shrine",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
    },
    {
        "from_node_id": "forgotten_shrine",
        "to_node_id": "marsh_edge",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "forest_road",
        "to_node_id": "mine_entrance",
        "action_kind": "enter",
        "route_kind": "enter_location",
        "link_kind": "entrance",
    },
    {
        "from_node_id": "ruined_settlement",
        "to_node_id": "mine_entrance",
        "action_kind": "enter",
        "route_kind": "enter_location",
        "link_kind": "entrance",
    },
)


STATIC_MAP_SCOUT_DISCOVERIES: tuple[dict[str, Any], ...] = (
    {
        "node_id": "start_trakt",
        "result_type": "route_revealed",
        "discovery_scope": "adjacent_route",
        "discovered_node_ids": ["craft_town"],
        "discovered_route_ids": ["start_trakt->craft_town"],
        "discovered_notes": [
            "С тракта замечается надёжный боковой путь к озёрному городку."
        ],
    },
    {
        "node_id": "eastern_bank",
        "result_type": "landmark_revealed",
        "discovery_scope": "adjacent_landmark",
        "discovered_node_ids": ["watchtower"],
        "discovered_route_ids": ["eastern_bank->watchtower"],
        "discovered_notes": [
            "С берега становится яснее подъём к старой сторожевой башне."
        ],
    },
    {
        "node_id": "forest_road",
        "result_type": "hidden_path_revealed",
        "discovery_scope": "hidden_route",
        "discovered_node_ids": ["ruined_settlement"],
        "discovered_route_ids": ["forest_road->ruined_settlement"],
        "discovered_notes": [
            "В стороне от лесной дороги открывается старая тропа к разрушенному посёлку."
        ],
    },
)


STATIC_MAP_CONTEXT_ACTION_EFFECTS: tuple[dict[str, Any], ...] = (
    {
        "node_id": "forest_road",
        "action_id": "clear_old_road",
        "label": "Расчистить старую дорогу",
        "action_kind": "route_access",
        "one_shot": True,
        "route_id": "forest_road->ruined_settlement:move",
        "effect_type": "clear_route",
        "result_type": "route_cleared",
        "summary": "Разобрать завал и вернуть проход к разрушенному посёлку.",
        "result_summary": "Группа убирает завал с лесной дороги и открывает устойчивый проход к разрушенному посёлку.",
        "applied_effects": ["route_access:cleared", "route_target:ruined_settlement"],
        "node_state_flags": ["old_road_cleared"],
        "node_state_summary": "На лесной дороге заметны следы недавней расчистки старого прохода.",
    },
    {
        "node_id": "ruined_settlement",
        "action_id": "shore_up_mine_path",
        "label": "Проверить завал у шахты",
        "action_kind": "route_access",
        "one_shot": False,
        "route_id": "ruined_settlement->mine_entrance:enter",
        "effect_type": "keep_route_blocked",
        "result_type": "route_still_blocked",
        "summary": "Осмотреть завал у шахтного входа и понять, держится ли проход.",
        "result_summary": "Осмотр подтверждает, что шахтный подход всё ещё нестабилен и остаётся заблокированным.",
        "block_reason": "mine_collapse",
        "applied_effects": ["route_access:blocked", "route_target:mine_entrance"],
        "node_state_flags": ["mine_path_shored"],
        "node_state_summary": "У шахтного подхода видны свежие подпорки и следы поспешного укрепления.",
    },
    {
        "node_id": "chapel_village",
        "action_id": "listen_chapel_watch",
        "label": "Поговорить с дозорными у часовни",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": True,
        "result_type": "local_clue_found",
        "summary": "Собрать короткую местную подсказку у часовни.",
        "result_summary": "Местные дозорные делятся краткой полезной наводкой о ближайшей дороге и безопасном ночлеге.",
        "discovered_notes": [
            "Дозорные советуют держаться освящённой дороги и не сворачивать к руинам после заката."
        ],
        "applied_effects": ["local_clue:chapel_watch"],
        "node_state_flags": ["chapel_watch_clue_taken"],
        "node_state_summary": "Дозорные у часовни уже поделились с группой своей короткой дорожной наводкой.",
    },
)


STATIC_MAP_NODE_STATE_OVERLAYS: tuple[dict[str, Any], ...] = (
    {
        "node_id": "forest_road",
        "state_flag": "old_road_cleared",
        "context_note": "У старой дороги видны следы недавней расчистки, и проход к руинам читается увереннее.",
        "detail_note": "Сломанные ветви и свежие борозды в грязи показывают, что завал уже разбирали совсем недавно.",
    },
    {
        "node_id": "ruined_settlement",
        "state_flag": "mine_path_shored",
        "context_note": "Подход к шахте отмечен свежими подпорками, но место всё равно выглядит ненадёжным.",
        "detail_note": "У входа в шахту заметны новые подпорки и следы осмотра, но сам проход остаётся тревожно нестабильным.",
    },
    {
        "node_id": "chapel_village",
        "state_flag": "chapel_watch_clue_taken",
        "context_note": "У часовни уже собраны местные подсказки, и дозорные узнают группу.",
        "detail_note": "Разговор с дозорными оставил конкретную дорожную наводку, и местные уже не повторяют её как первую новость.",
        "service_note": "Местные советы уже собраны; теперь здесь скорее подтверждают прежнюю наводку, чем дают новую.",
    },
    {
        "node_id": "craft_town",
        "state_flag": "craft_guidance_taken",
        "context_note": "В городке уже получены местные указания, и проводники сразу понимают, что группа пришла не с пустыми руками.",
        "detail_note": "У пристани и у ворот уже повторяют ту же собранную для группы дорожную наводку, а не начинают рассказ заново.",
        "service_note": "Основная наводка уже выдана; теперь местные скорее подтверждают её, чем открывают новый маршрут.",
    },
    {
        "node_id": "chapel_village",
        "state_flag": "chapel_shelter_used",
        "context_note": "У часовни уже отмечен двор, где группе однажды дали тихий кров.",
        "detail_note": "Следы недавнего ночлега у часовни показывают, что это убежище уже использовали именно для этой группы.",
        "service_note": "Этот спокойный кров уже отмечен за группой как использованный ранее.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "forest_supplies_secured",
        "context_note": "В посёлке уже собран и выдан один дорожный набор для этой группы.",
        "detail_note": "У охотничьих сараев видно, что запас для выхода к руинам уже готовили и выдавали совсем недавно.",
        "service_note": "Основной лесной набор уже собран; дальше здесь скорее пополняют мелочи, чем собирают новый комплект.",
    },
)


STATIC_MAP_NODE_ENTRY_OVERLAYS: tuple[dict[str, Any], ...] = (
    {
        "node_id": "craft_town",
        "first_entry_type": "settlement_welcome",
        "first_entry_title": "Озёрный городок принимает путников",
        "first_entry_note": "Городок встречает группу как новый спокойный узел пути у воды.",
        "return_entry_type": "return_entry",
        "return_entry_title": "Возвращение в Озёрный городок",
        "return_entry_note": "Знакомые улицы и пристань быстро возвращают группе прежний ориентир.",
    },
    {
        "node_id": "fortress_gate",
        "first_entry_type": "landmark_reached",
        "first_entry_title": "Ворота крепости достигнуты",
        "first_entry_note": "Подъём к крепостным воротам отмечает явную веху на маршруте группы.",
        "return_entry_type": "return_entry",
        "return_entry_title": "Снова у ворот крепости",
        "return_entry_note": "Крепостной подход уже знаком, и группа быстро считывает прежний порядок пути.",
    },
    {
        "node_id": "forest_road",
        "state_flag": "old_road_cleared",
        "entry_type": "changed_place",
        "entry_title": "Лесная дорога изменилась",
        "entry_note": "У входа на лесную дорогу сразу заметно, что старый завал уже разобран и место ощущается иначе.",
    },
    {
        "node_id": "ruined_settlement",
        "state_flag": "mine_path_shored",
        "entry_type": "changed_place",
        "entry_title": "Руины с новым укреплением",
        "entry_note": "Подход к руинам теперь выглядит иначе: у шахтного направления заметны свежие подпорки и следы недавней работы.",
    },
    {
        "node_id": "road_hamlet",
        "first_entry_type": "quiet_entry",
        "first_entry_title": "Дорожный хутор на пути",
        "first_entry_note": "Небольшой хутор даёт группе короткую передышку без лишнего шума.",
        "return_entry_type": "return_entry",
        "return_entry_title": "Снова в дорожном хуторе",
        "return_entry_note": "Хутор уже знаком и воспринимается скорее как тихая отметка на маршруте.",
    },
)


STATIC_MAP_DESTINATION_EVENTS: tuple[dict[str, Any], ...] = (
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
    },
    {
        "node_id": "road_hamlet",
        "event_id": "road_hamlet_first_marker",
        "label": "Дорожная примета хутора",
        "first_visit_only": True,
        "one_shot": True,
        "result_type": "first_discovery",
        "title": "У хутора замечают старую дорожную метку",
        "summary": "У первого прибытия в хутор находится заметная дорожная примета для следующих переходов.",
        "result_summary": "Дорожный хутор даёт группе первую локальную находку: старую метку, по которой легче удерживать путь обратно к тракту.",
        "discovered_notes": [
            "У хуторского колодца оставлена старая метка на обратный путь: по ней проще не потерять тракт в сумерках."
        ],
        "intel_entry_type": "clue",
        "intel_title": "Дорожная метка у хутора",
        "node_state_flags": ["road_hamlet_marker_found"],
        "node_state_summary": "У хутора уже отмечена найденная группой дорожная примета.",
        "applied_effects": ["destination_notice:road_hamlet", "intel:clue"],
        "tags": ["clue", "hamlet", "road"],
    },
    {
        "node_id": "fortress_gate",
        "event_id": "fortress_gate_watch_warning",
        "label": "Предупреждение дозора у ворот",
        "first_visit_only": True,
        "one_shot": True,
        "result_type": "local_warning",
        "title": "У ворот слышно предупреждение дозора",
        "summary": "При первом подходе дозорные быстро предупреждают группу о напряжённом подходе вокруг крепости.",
        "result_summary": "У ворот крепости группа получает короткое местное предупреждение: подход под контролем, и задерживаться у стены без нужды не стоит.",
        "discovered_notes": [
            "Дозор советует не задерживаться под стеной после сумерек и заранее выбирать безопасный отход обратно к тракту."
        ],
        "intel_entry_type": "warning",
        "intel_title": "Предупреждение дозора у ворот",
        "applied_effects": ["destination_warning:fortress_gate", "intel:warning"],
        "tags": ["warning", "fortress", "watch"],
    },
    {
        "node_id": "mine_entrance",
        "event_id": "mine_entrance_air_warning",
        "label": "Тяжёлый воздух у шахтного входа",
        "result_type": "local_warning",
        "title": "У входа тянет тяжёлым воздухом",
        "summary": "Шахтный вход каждый раз напоминает о нестабильном и тревожном проходе вниз.",
        "result_summary": "У шахтного входа чувствуется тяжёлый воздух и явная опасность: место встречает группу предупреждением, а не спокойствием.",
        "discovered_notes": [
            "Даже на подходе к шахте слышно, как воздух гуляет в пустотах, и место не кажется устойчивым."
        ],
        "intel_entry_type": "warning",
        "intel_title": "Предупреждение у шахтного входа",
        "applied_effects": ["destination_warning:mine_entrance", "intel:warning"],
        "tags": ["warning", "mine", "ruins"],
    },
    {
        "node_id": "ruined_settlement",
        "event_id": "ruined_settlement_changed_notice",
        "label": "Следы свежего укрепления у руин",
        "required_state_flags": ["mine_path_shored"],
        "result_type": "changed_place_notice",
        "title": "Руины встречают новыми следами работы",
        "summary": "После укрепления шахтного подхода у руин сразу заметны свежие подпорки и изменившийся рисунок места.",
        "result_summary": "Руины больше не встречают группу прежней картиной: следы недавнего укрепления меняют локальное ощущение прибытия.",
        "discovered_notes": [
            "У шахтного направления заметны новые подпорки: место выглядит иначе и явно помнит недавнюю работу."
        ],
        "intel_entry_type": "warning",
        "intel_title": "Новая примета у руин",
        "applied_effects": ["destination_notice:ruined_settlement", "intel:warning"],
        "tags": ["ruins", "changed_place", "mine"],
    },
)


STATIC_MAP_SERVICE_EFFECTS: tuple[dict[str, Any], ...] = (
    {
        "node_id": "craft_town",
        "service_key": "local_guidance",
        "service_id": "craft_town_local_guidance",
        "service_kind": "guidance",
        "one_shot": True,
        "result_type": "guidance_received",
        "summary": "Получить у местных проверенную дорожную наводку.",
        "result_summary": "Городские проводники отмечают для группы надёжный береговой ориентир у сторожевой башни.",
        "discovered_notes": [
            "Местные советуют держаться берегового ориентира у сторожевой башни: там проще не потерять темп и не свернуть в пустые дворы."
        ],
        "reveal_node_ids": ["watchtower"],
        "applied_effects": ["guidance_recorded", "node_revealed:watchtower"],
        "node_state_flags": ["craft_guidance_taken"],
        "node_state_summary": "В городке уже собраны местные указания по береговому ориентиру у сторожевой башни.",
    },
    {
        "node_id": "chapel_village",
        "service_key": "shrine_aid",
        "service_id": "chapel_village_shrine_aid",
        "service_kind": "shrine",
        "one_shot": True,
        "result_type": "lodging_received",
        "summary": "Попросить тихий приют и помощь у часовни.",
        "result_summary": "При часовне группе дают спокойный кров и короткую дорожную поддержку перед следующим переходом.",
        "discovered_notes": [
            "Служители часовни отмечают безопасный двор для ночлега и предупреждают, где не стоит задерживаться после заката."
        ],
        "applied_effects": ["lodging_received", "shrine_support_recorded"],
        "node_state_flags": ["chapel_shelter_used"],
        "node_state_summary": "При часовне уже отмечен использованный для группы безопасный ночлег.",
    },
    {
        "node_id": "forest_settlement",
        "service_key": "resupply",
        "service_id": "forest_settlement_resupply",
        "service_kind": "supplies",
        "one_shot": True,
        "result_type": "supplies_secured",
        "summary": "Собрать лесные дорожные припасы перед выходом к руинам.",
        "result_summary": "Посёлок собирает для группы крепкий набор лесных припасов и помечает, что помощь уже выдана.",
        "discovered_notes": [
            "Охотники советуют не тянуть с выходом после пополнения запасов: дальше дорога к руинам быстро становится пустой."
        ],
        "applied_effects": ["supplies_secured"],
        "node_state_flags": ["forest_supplies_secured"],
        "node_state_summary": "В лесном посёлке уже подготовлен и выдан дорожный набор для этой группы.",
    },
)


def _normalized_text(value: Any) -> str:
    return str(value or "").strip().lower()


def build_static_route_id(from_node_id: str | None, to_node_id: str | None, action_kind: str | None) -> str:
    normalized_from = _normalized_text(from_node_id)
    normalized_to = _normalized_text(to_node_id)
    normalized_action = _normalized_text(action_kind)
    if not normalized_from or not normalized_to:
        return ""
    if normalized_action:
        return f"{normalized_from}->{normalized_to}:{normalized_action}"
    return f"{normalized_from}->{normalized_to}"


def get_static_node_metadata(node: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(node, dict):
        return {}
    node_type = _normalized_text(node.get("node_type"))
    zone_band = _normalized_text(node.get("zone_band"))
    node_id = _normalized_text(node.get("node_id"))
    metadata: dict[str, Any] = {}
    if node_type == "zone":
        if zone_band == "safe":
            metadata["settlement_kind"] = "town" if node_id == "craft_town" else "roadside"
            metadata["environment_hint"] = "lakeshore" if node_id in {"eastern_bank", "craft_town"} else "roadland"
            metadata["safe_rest_hint"] = True
        elif zone_band == "border":
            metadata["settlement_kind"] = "village" if node_id in {"chapel_village", "forest_settlement"} else "hamlet"
            metadata["environment_hint"] = "wooded" if node_id in {"forest_road", "forest_settlement"} else "frontier"
            metadata["safe_rest_hint"] = node_id in {"road_hamlet", "chapel_village", "forest_settlement"}
        elif zone_band == "danger":
            metadata["settlement_kind"] = "ruins" if node_id == "ruined_settlement" else "wilds"
            metadata["environment_hint"] = "marsh" if node_id == "marsh_edge" else "ruined_frontier"
            metadata["safe_rest_hint"] = False
    elif node_type == "landmark":
        metadata["poi_kind"] = "fortified" if node_id in {"fortress_gate", "old_fortress_edge", "watchtower"} else "shrine"
        metadata["environment_hint"] = "fortified" if node_id == "fortress_gate" else ("marsh" if node_id == "forgotten_shrine" else "frontier")
        metadata["safe_rest_hint"] = node_id == "watchtower"
    elif node_type == "interior_entry":
        metadata["poi_kind"] = "mine"
        metadata["environment_hint"] = "ruined_frontier"
        metadata["safe_rest_hint"] = False
    return metadata


def _merge_static_node_metadata(node: dict[str, Any]) -> dict[str, Any]:
    return {**node, **get_static_node_metadata(node)}


def get_static_link_metadata(link: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(link, dict):
        return {}
    link_kind = _normalized_text(link.get("link_kind"))
    route_kind = _normalized_text(link.get("route_kind"))
    from_node = get_static_node(link.get("from_node_id"))
    to_node = get_static_node(link.get("to_node_id"))
    from_zone_band = _normalized_text((from_node or {}).get("zone_band"))
    to_environment = _normalized_text((to_node or {}).get("environment_hint"))
    metadata: dict[str, Any] = {
        "traversal_kind": "road",
        "risk_band": "medium",
        "terrain_hint": "mixed",
        "travel_tags": [],
    }
    if link_kind in {"road", "shore_road"}:
        metadata.update(
            traversal_kind="road",
            risk_band="low",
            terrain_hint="open" if link_kind == "road" else "lakeshore",
            travel_tags=["settled_route"],
        )
    elif link_kind in {"approach", "return"}:
        metadata.update(
            traversal_kind="gate_approach" if route_kind == "landmark_move" else "road",
            risk_band="low" if route_kind == "landmark_move" else "medium",
            terrain_hint="fortified",
            travel_tags=["fortified"],
        )
        if from_zone_band == "danger" or to_environment in {"marsh", "ruins", "ruined_frontier", "frontier"}:
            metadata["risk_band"] = "high" if to_environment == "marsh" or from_zone_band == "danger" else "medium"
            metadata["terrain_hint"] = to_environment or metadata["terrain_hint"]
            if to_environment == "marsh":
                metadata["travel_tags"] = ["marsh", "poor_visibility"]
            elif to_environment in {"ruins", "ruined_frontier"}:
                metadata["travel_tags"] = ["ruins", "frontier"]
    elif link_kind in {"branch_road", "shore_track"}:
        metadata.update(
            traversal_kind="trail",
            risk_band="low",
            terrain_hint="open" if link_kind == "branch_road" else "lakeshore",
            travel_tags=["settled_route"],
        )
    elif link_kind == "forest_track":
        metadata.update(
            traversal_kind="trail",
            risk_band="medium",
            terrain_hint="wooded",
            travel_tags=["wooded"],
        )
    elif link_kind == "old_road":
        metadata.update(
            traversal_kind="wild",
            risk_band="medium",
            terrain_hint="ruined_frontier",
            travel_tags=["ruins", "frontier"],
        )
    elif link_kind == "ruin_path":
        metadata.update(
            traversal_kind="ruin_path",
            risk_band="high",
            terrain_hint="ruins",
            travel_tags=["ruins", "elevated_watch"],
        )
    elif link_kind == "bog_track":
        metadata.update(
            traversal_kind="marsh_path",
            risk_band="high",
            terrain_hint="marsh",
            travel_tags=["marsh", "poor_visibility"],
        )
    elif link_kind == "entrance":
        metadata.update(
            traversal_kind="entry",
            risk_band="high",
            terrain_hint="ruins",
            travel_tags=["transition", "interior_threshold"],
        )
    return metadata


def _merge_static_link_metadata(link: dict[str, Any]) -> dict[str, Any]:
    metadata = get_static_link_metadata(link)
    merged = {**link, **metadata}
    merged["travel_tags"] = list(metadata.get("travel_tags") or [])
    merged["route_id"] = build_static_route_id(
        merged.get("from_node_id"),
        merged.get("to_node_id"),
        merged.get("action_kind"),
    )
    return merged


def get_static_map_nodes() -> list[dict[str, Any]]:
    return [_merge_static_node_metadata(dict(node)) for node in STATIC_MAP_NODES]


def get_static_map_links() -> list[dict[str, Any]]:
    return [_merge_static_link_metadata(dict(link)) for link in STATIC_MAP_LINKS]


def get_static_node_scout_discoveries(
    *,
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    resolved_node_id = _normalized_text(node_id)
    if not resolved_node_id and isinstance(current_map_position, dict):
        resolved_node_id = _normalized_text(current_map_position.get("node_id"))
    if not resolved_node_id:
        return []
    discoveries: list[dict[str, Any]] = []
    for item in STATIC_MAP_SCOUT_DISCOVERIES:
        if _normalized_text(item.get("node_id")) != resolved_node_id:
            continue
        discovered_node_ids = [
            str(node_ref).strip()
            for node_ref in (item.get("discovered_node_ids") or [])
            if str(node_ref or "").strip() and get_static_node(str(node_ref)) is not None
        ]
        discoveries.append(
            {
                "node_id": resolved_node_id,
                "result_type": str(item.get("result_type") or ""),
                "discovery_scope": str(item.get("discovery_scope") or ""),
                "discovered_node_ids": discovered_node_ids,
                "discovered_route_ids": [
                    str(route_id).strip()
                    for route_id in (item.get("discovered_route_ids") or [])
                    if str(route_id or "").strip()
                ],
                "discovered_notes": [
                    str(note).strip()
                    for note in (item.get("discovered_notes") or [])
                    if str(note or "").strip()
                ],
            }
        )
    return discoveries


def get_static_node_context_action_effects(
    *,
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    resolved_node_id = _normalized_text(node_id)
    if not resolved_node_id and isinstance(current_map_position, dict):
        resolved_node_id = _normalized_text(current_map_position.get("node_id"))
    if not resolved_node_id:
        return []
    effects: list[dict[str, Any]] = []
    for item in STATIC_MAP_CONTEXT_ACTION_EFFECTS:
        if _normalized_text(item.get("node_id")) != resolved_node_id:
            continue
        effect = {
            "node_id": resolved_node_id,
            "action_id": str(item.get("action_id") or "").strip().lower(),
            "label": str(item.get("label") or "").strip(),
            "action_kind": str(item.get("action_kind") or "action").strip().lower() or "action",
            "effect_type": str(item.get("effect_type") or "").strip().lower(),
            "result_type": str(item.get("result_type") or "no_effect").strip().lower() or "no_effect",
            "summary": str(item.get("summary") or "").strip(),
            "result_summary": str(item.get("result_summary") or "").strip(),
            "source": "registry",
            "one_shot": bool(item.get("one_shot")),
            "applied_effects": [
                str(effect_note).strip()
                for effect_note in (item.get("applied_effects") or [])
                if str(effect_note or "").strip()
            ],
            "discovered_notes": [
                str(note).strip()
                for note in (item.get("discovered_notes") or [])
                if str(note or "").strip()
            ],
        }
        route_id = str(item.get("route_id") or "").strip().lower()
        if route_id:
            effect["route_id"] = route_id
        block_reason = str(item.get("block_reason") or "").strip()
        if block_reason:
            effect["block_reason"] = block_reason
        node_state_flags = [
            str(flag).strip().lower()
            for flag in (item.get("node_state_flags") or [])
            if str(flag or "").strip()
        ]
        if node_state_flags:
            effect["node_state_flags"] = node_state_flags
        node_state_summary = str(item.get("node_state_summary") or "").strip()
        if node_state_summary:
            effect["node_state_summary"] = node_state_summary
        if effect["action_id"] and effect["label"]:
            effects.append(effect)
    return effects


def get_static_node_state_overlays(
    *,
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
    state_flags: list[str] | set[str] | None = None,
) -> list[dict[str, Any]]:
    resolved_node_id = _normalized_text(node_id)
    if not resolved_node_id and isinstance(current_map_position, dict):
        resolved_node_id = _normalized_text(current_map_position.get("node_id"))
    if not resolved_node_id:
        return []
    normalized_flags = {
        _normalized_text(flag)
        for flag in (state_flags or [])
        if _normalized_text(flag)
    }
    if not normalized_flags:
        return []
    overlays: list[dict[str, Any]] = []
    for item in STATIC_MAP_NODE_STATE_OVERLAYS:
        if _normalized_text(item.get("node_id")) != resolved_node_id:
            continue
        state_flag = _normalized_text(item.get("state_flag"))
        if normalized_flags and state_flag not in normalized_flags:
            continue
        overlay: dict[str, Any] = {
            "node_id": resolved_node_id,
            "state_flag": state_flag,
        }
        context_note = str(item.get("context_note") or "").strip()
        detail_note = str(item.get("detail_note") or "").strip()
        service_note = str(item.get("service_note") or "").strip()
        if context_note:
            overlay["context_note"] = context_note
        if detail_note:
            overlay["detail_note"] = detail_note
        if service_note:
            overlay["service_note"] = service_note
        if state_flag:
            overlays.append(overlay)
    return overlays


def get_static_node_entry_overlays(
    *,
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
    state_flags: list[str] | set[str] | None = None,
) -> list[dict[str, Any]]:
    resolved_node_id = _normalized_text(node_id)
    if not resolved_node_id and isinstance(current_map_position, dict):
        resolved_node_id = _normalized_text(current_map_position.get("node_id"))
    if not resolved_node_id:
        return []
    normalized_flags = {
        _normalized_text(flag)
        for flag in (state_flags or [])
        if _normalized_text(flag)
    }
    overlays: list[dict[str, Any]] = []
    for item in STATIC_MAP_NODE_ENTRY_OVERLAYS:
        if _normalized_text(item.get("node_id")) != resolved_node_id:
            continue
        state_flag = _normalized_text(item.get("state_flag"))
        if state_flag and state_flag not in normalized_flags:
            continue
        overlay: dict[str, Any] = {"node_id": resolved_node_id}
        if state_flag:
            overlay["state_flag"] = state_flag
        for key in (
            "entry_type",
            "entry_title",
            "entry_note",
            "first_entry_type",
            "first_entry_title",
            "first_entry_note",
            "return_entry_type",
            "return_entry_title",
            "return_entry_note",
        ):
            value = str(item.get(key) or "").strip()
            if value:
                overlay[key] = value
        if len(overlay) > 1:
            overlays.append(overlay)
    return overlays


def get_static_node_destination_events(
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
    *,
    state_flags: list[str] | set[str] | None = None,
    visit_count: int | None = None,
) -> list[dict[str, Any]]:
    resolved_node_id = _normalized_text(node_id)
    if not resolved_node_id and isinstance(current_map_position, dict):
        resolved_node_id = _normalized_text(current_map_position.get("node_id"))
    if not resolved_node_id:
        return []
    normalized_state_flags = {
        str(flag).strip().lower()
        for flag in (state_flags or [])
        if str(flag or "").strip()
    }
    resolved_visit_count = max(0, int(visit_count or 0))
    events: list[dict[str, Any]] = []
    for item in STATIC_MAP_DESTINATION_EVENTS:
        if _normalized_text(item.get("node_id")) != resolved_node_id:
            continue
        required_state_flags = {
            str(flag).strip().lower()
            for flag in (item.get("required_state_flags") or [])
            if str(flag or "").strip()
        }
        if required_state_flags and not required_state_flags.issubset(normalized_state_flags):
            continue
        if bool(item.get("first_visit_only")) and resolved_visit_count not in {0, 1}:
            continue
        min_visit_count = int(item.get("min_visit_count") or 0)
        if min_visit_count > 0 and resolved_visit_count < min_visit_count:
            continue
        events.append(
            {
                **item,
                "node_id": resolved_node_id,
                "required_state_flags": sorted(required_state_flags),
            }
        )
    return events


def get_static_node_service_effects(
    *,
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    resolved_node_id = _normalized_text(node_id)
    if not resolved_node_id and isinstance(current_map_position, dict):
        resolved_node_id = _normalized_text(current_map_position.get("node_id"))
    if not resolved_node_id:
        return []
    effects: list[dict[str, Any]] = []
    for item in STATIC_MAP_SERVICE_EFFECTS:
        if _normalized_text(item.get("node_id")) != resolved_node_id:
            continue
        service_key = _normalized_text(item.get("service_key"))
        service_id = str(item.get("service_id") or f"{resolved_node_id}:{service_key}").strip().lower()
        effect: dict[str, Any] = {
            "node_id": resolved_node_id,
            "service_key": service_key,
            "service_id": service_id,
            "service_kind": str(item.get("service_kind") or service_key or "service").strip().lower(),
            "result_type": str(item.get("result_type") or "no_effect").strip().lower(),
            "summary": str(item.get("summary") or "").strip(),
            "result_summary": str(item.get("result_summary") or "").strip(),
            "source": "registry",
            "one_shot": bool(item.get("one_shot")),
            "discovered_notes": [
                str(note).strip()
                for note in (item.get("discovered_notes") or [])
                if str(note or "").strip()
            ],
            "reveal_node_ids": [
                str(node_ref).strip()
                for node_ref in (item.get("reveal_node_ids") or [])
                if str(node_ref or "").strip()
            ],
            "applied_effects": [
                str(effect_note).strip()
                for effect_note in (item.get("applied_effects") or [])
                if str(effect_note or "").strip()
            ],
            "node_state_flags": [
                str(flag).strip().lower()
                for flag in (item.get("node_state_flags") or [])
                if str(flag or "").strip()
            ],
            "node_state_summary": str(item.get("node_state_summary") or "").strip(),
        }
        if service_key and service_id:
            effects.append(effect)
    return effects


def get_static_node(node_id: str | None) -> dict[str, Any] | None:
    normalized_id = _normalized_text(node_id)
    if not normalized_id:
        return None
    for node in STATIC_MAP_NODES:
        if _normalized_text(node.get("node_id")) == normalized_id:
            return _merge_static_node_metadata(dict(node))
    return None


def resolve_static_map_node(query_text: str | None) -> dict[str, Any] | None:
    normalized_query = _normalized_text(query_text)
    if not normalized_query:
        return None
    for node in STATIC_MAP_NODES:
        values = [node.get("node_id"), node.get("label")]
        values.extend(node.get("aliases") or ())
        if any(_normalized_text(value) == normalized_query for value in values):
            return _merge_static_node_metadata(dict(node))
    for node in STATIC_MAP_NODES:
        values = [node.get("label")]
        values.extend(node.get("aliases") or ())
        if any(_normalized_text(value) in normalized_query for value in values if _normalized_text(value)):
            return _merge_static_node_metadata(dict(node))
    return None


def find_static_link(from_node_id: str | None, to_node_id: str | None, action_kind: str | None) -> dict[str, Any] | None:
    normalized_from = _normalized_text(from_node_id)
    normalized_to = _normalized_text(to_node_id)
    normalized_action = _normalized_text(action_kind)
    if not normalized_from or not normalized_to or not normalized_action:
        return None
    for link in STATIC_MAP_LINKS:
        if (
            _normalized_text(link.get("from_node_id")) == normalized_from
            and _normalized_text(link.get("to_node_id")) == normalized_to
            and _normalized_text(link.get("action_kind")) == normalized_action
        ):
            return _merge_static_link_metadata(dict(link))
    return None


def get_obvious_linked_static_node_ids(node_id: str | None, *, limit: int = 1) -> list[str]:
    normalized_id = _normalized_text(node_id)
    if not normalized_id or limit <= 0:
        return []

    def _link_priority(link: dict[str, str]) -> tuple[int, int, str]:
        target_node = get_static_node(link.get("to_node_id"))
        target_type = _normalized_text((target_node or {}).get("node_type"))
        type_priority = {
            "landmark": 0,
            "interior_entry": 1,
            "building": 1,
            "zone": 2,
        }.get(target_type, 3)
        action_priority = 0 if _normalized_text(link.get("action_kind")) == "move" else 1
        return (type_priority, action_priority, _normalized_text(link.get("to_node_id")))

    obvious_ids: list[str] = []
    candidate_links = sorted(
        [link for link in STATIC_MAP_LINKS if _normalized_text(link.get("from_node_id")) == normalized_id],
        key=_link_priority,
    )
    for link in candidate_links:
        target_node_id = str(link.get("to_node_id") or "").strip()
        if not target_node_id or target_node_id in obvious_ids:
            continue
        if get_static_node(target_node_id) is None:
            continue
        obvious_ids.append(target_node_id)
        if len(obvious_ids) >= limit:
            break
    return obvious_ids


def get_static_navigation_options(
    *,
    current_node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
    known_node_ids: list[str] | set[str] | None = None,
    revealed_node_ids: list[str] | set[str] | None = None,
) -> list[dict[str, Any]]:
    resolved_current_node_id = _normalized_text(current_node_id)
    if not resolved_current_node_id and isinstance(current_map_position, dict):
        resolved_current_node_id = _normalized_text(current_map_position.get("node_id"))
    if not resolved_current_node_id:
        return []

    normalized_known = {
        _normalized_text(node_id)
        for node_id in (known_node_ids or [])
        if _normalized_text(node_id)
    }
    normalized_revealed = {
        _normalized_text(node_id)
        for node_id in (revealed_node_ids or [])
        if _normalized_text(node_id)
    }

    options: list[dict[str, Any]] = []
    for link in get_static_map_links():
        if _normalized_text(link.get("from_node_id")) != resolved_current_node_id:
            continue
        target_node = get_static_node(str(link.get("to_node_id") or ""))
        if not target_node:
            continue
        target_node_id = _normalized_text(target_node.get("node_id"))
        is_known = target_node_id in normalized_known
        is_revealed = target_node_id in normalized_revealed
        if not is_known:
            continue
        option = {
            "route_id": str(link.get("route_id") or ""),
            "target_node_id": str(target_node.get("node_id") or ""),
            "target_label": str(target_node.get("label") or target_node.get("node_id") or ""),
            "target_node_type": str(target_node.get("node_type") or "zone"),
            "action_kind": str(link.get("action_kind") or "move"),
            "route_kind": str(link.get("route_kind") or ""),
            "traversal_kind": str(link.get("traversal_kind") or ""),
            "risk_band": str(link.get("risk_band") or ""),
            "terrain_hint": str(link.get("terrain_hint") or ""),
            "travel_tags": list(link.get("travel_tags") or []),
            "source": "registry",
            "known": is_known,
            "revealed": is_revealed,
            "visible": is_revealed,
        }
        options.append(option)

    options.sort(
        key=lambda item: (
            0 if bool(item.get("revealed")) else 1,
            str(item.get("action_kind") or ""),
            str(item.get("target_label") or ""),
        )
    )
    return options


def get_static_node_context(
    *,
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    resolved_node = get_static_node(node_id)
    if not resolved_node and isinstance(current_map_position, dict):
        resolved_node = get_static_node(current_map_position.get("node_id"))
    if resolved_node:
        summary: dict[str, Any] = {
            "node_id": str(resolved_node.get("node_id") or ""),
            "label": str(resolved_node.get("label") or resolved_node.get("node_id") or ""),
            "node_type": str(resolved_node.get("node_type") or "zone"),
            "area_label": str(resolved_node.get("area_label") or resolved_node.get("label") or ""),
            "zone_band": str(resolved_node.get("zone_band") or ""),
        }
        for key in ("settlement_kind", "poi_kind", "environment_hint", "safe_rest_hint"):
            if key in resolved_node:
                summary[key] = resolved_node.get(key)
        detail = get_static_node_detail(node_id=summary["node_id"])
        if detail and detail.get("inspect_summary"):
            summary["detail_summary"] = detail.get("inspect_summary")
        return summary
    if not isinstance(current_map_position, dict):
        return None
    return {
        "node_id": str(current_map_position.get("node_id") or ""),
        "label": str(current_map_position.get("label") or current_map_position.get("node_id") or ""),
        "node_type": str(current_map_position.get("node_type") or "zone"),
        "area_label": str(current_map_position.get("area_label") or current_map_position.get("label") or ""),
    }


def get_current_node_context_actions(
    *,
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    context = get_static_node_context(node_id=node_id, current_map_position=current_map_position)
    if not context:
        return []

    node_type = _normalized_text(context.get("node_type"))
    zone_band = _normalized_text(context.get("zone_band"))
    settlement_kind = _normalized_text(context.get("settlement_kind"))
    safe_rest_hint = bool(context.get("safe_rest_hint"))
    authored_effects = get_static_node_context_action_effects(
        node_id=node_id,
        current_map_position=current_map_position,
    )

    actions: list[dict[str, Any]] = []

    def _add(
        action_key: str,
        label: str,
        action_type: str = "action",
        *,
        action_id: str | None = None,
        action_kind: str | None = None,
    ) -> None:
        if any(existing.get("action_key") == action_key for existing in actions):
            return
        resolved_action_id = str(action_id or action_key).strip().lower() or action_key
        actions.append(
            {
                "action_id": resolved_action_id,
                "action_key": action_key,
                "label": label,
                "action_type": action_type,
                "action_kind": str(action_kind or action_type).strip().lower() or action_type,
            }
        )

    if node_type == "interior_entry":
        _add("enter", "Войти", action_kind="enter")
        _add("inspect", "Осмотреть вход", action_kind="inspect")
        _add("wait", "Подождать", action_kind="wait")
        return actions

    _add("navigate", "Продолжить путь", action_kind="navigate")
    _add("inspect", "Осмотреться", action_kind="inspect")
    _add("wait", "Подождать", action_kind="wait")

    if settlement_kind in {"town", "village", "hamlet"} or safe_rest_hint:
        _add("rest_hint", "Есть место для передышки", "hint", action_kind="rest_hint")

    if node_type in {"zone", "landmark"} and (
        settlement_kind in {"roadside", "wilds", "ruins"} or zone_band in {"border", "danger"}
    ):
        _add("camp", "Разбить лагерь", action_kind="camp")

    for effect in authored_effects:
        action_id = str(effect.get("action_id") or "").strip().lower()
        label = str(effect.get("label") or "").strip()
        if not action_id or not label:
            continue
        if any(existing.get("action_id") == action_id for existing in actions):
            continue
        actions.append(
            {
                "action_id": action_id,
                "action_key": action_id,
                "label": label,
                "action_type": "action",
                "action_kind": str(effect.get("action_kind") or "action"),
                "source": "registry",
                "one_shot": bool(effect.get("one_shot")),
            }
        )

    return actions


def get_static_node_services(
    *,
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    resolved_node = get_static_node(node_id)
    if not resolved_node and isinstance(current_map_position, dict):
        resolved_node = get_static_node(current_map_position.get("node_id"))
    if not resolved_node:
        return []
    resolved_node_id = str(resolved_node.get("node_id") or "").strip().lower()
    detail = get_static_node_detail(node_id=str(resolved_node.get("node_id") or ""))
    authored_effects = {
        str(effect.get("service_key") or "").strip().lower(): effect
        for effect in get_static_node_service_effects(node_id=resolved_node_id)
        if isinstance(effect, dict) and str(effect.get("service_key") or "").strip()
    }
    service_defs = {
        "safe_rest": {
            "label": "Безопасный отдых",
            "service_type": "rest",
            "summary": "Можно перевести дух и переждать путь в сравнительно безопасных условиях.",
        },
        "resupply": {
            "label": "Пополнение припасов",
            "service_type": "supplies",
            "summary": "Здесь можно пополнить базовые дорожные запасы перед выходом.",
        },
        "healing_aid": {
            "label": "Помощь с ранами",
            "service_type": "aid",
            "summary": "На месте можно получить перевязку, уход или базовую помощь после дороги.",
        },
        "local_guidance": {
            "label": "Местные указания",
            "service_type": "guidance",
            "summary": "Здесь можно получить ориентиры, слухи и безопасные подсказки по ближайшим дорогам.",
        },
        "shrine_aid": {
            "label": "Поддержка у святыни",
            "service_type": "shrine",
            "summary": "Здесь могут дать тихий приют, совет или скромную духовную помощь.",
        },
    }
    services: list[dict[str, Any]] = []
    for raw_key in resolved_node.get("services") or []:
        service_key = _normalized_text(raw_key)
        service_def = service_defs.get(service_key)
        if not service_def:
            continue
        service = {
            "service_id": str((authored_effects.get(service_key) or {}).get("service_id") or f"{resolved_node_id}:{service_key}"),
            "service_key": service_key,
            "label": service_def["label"],
            "service_type": service_def["service_type"],
            "service_kind": str((authored_effects.get(service_key) or {}).get("service_kind") or service_def["service_type"]),
            "summary": service_def["summary"],
            "source": "registry",
            "available": True,
            "status": "available",
        }
        if detail and detail.get("service_hints"):
            service["service_hints"] = list(detail.get("service_hints") or [])
        authored_effect = authored_effects.get(service_key)
        if authored_effect and bool(authored_effect.get("one_shot")):
            service["one_shot"] = True
        services.append(service)
    return services


def get_static_node_service_result(
    *,
    service_id: str | None = None,
    service_key: str | None = None,
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
    source: str = "registry",
) -> dict[str, Any] | None:
    normalized_service_key = _normalized_text(service_key)
    normalized_service_id = _normalized_text(service_id)
    if not normalized_service_key and not normalized_service_id:
        return None
    detail = get_static_node_detail(node_id=node_id, current_map_position=current_map_position)
    if not detail:
        return None
    available = {
        str(item.get("service_id") or item.get("service_key") or "").strip().lower(): item
        for item in get_static_node_services(node_id=node_id, current_map_position=current_map_position)
        if isinstance(item, dict)
    }
    service = available.get(normalized_service_id or normalized_service_key)
    if not service and normalized_service_key:
        service = next(
            (
                item
                for item in available.values()
                if str(item.get("service_key") or "").strip().lower() == normalized_service_key
            ),
            None,
        )
    if not service:
        return None
    resolved_service_id = str(service.get("service_id") or normalized_service_id or normalized_service_key)
    resolved_service_key = str(service.get("service_key") or normalized_service_key or resolved_service_id)
    result = {
        "service_id": resolved_service_id,
        "service_key": resolved_service_key,
        "service_label": str(service.get("label") or resolved_service_key),
        "label": str(service.get("label") or resolved_service_key),
        "service_type": str(service.get("service_type") or "service"),
        "service_kind": str(service.get("service_kind") or service.get("service_type") or "service"),
        "summary": str(service.get("summary") or ""),
        "node_id": str(detail.get("node_id") or ""),
        "node_label": str(detail.get("label") or detail.get("node_id") or ""),
        "source": str(source or "registry"),
    }
    service_result_notes = {
        "safe_rest": "Место подходит для короткой передышки без немедленной дорожной угрозы.",
        "resupply": "Здесь можно собрать базовые припасы и привести снаряжение в порядок.",
        "healing_aid": "Здесь помогут с перевязкой, тёплой водой и простым уходом после пути.",
        "local_guidance": "Местные подскажут, какая дорога сейчас спокойнее и где не стоит задерживаться.",
        "shrine_aid": "У святыни можно получить благословение, тишину и скромную помощь в дороге.",
    }
    result["result_summary"] = service_result_notes.get(resolved_service_key, result["summary"])
    if detail.get("service_hints"):
        result["service_hints"] = list(detail.get("service_hints") or [])
    return result


def get_static_node_detail(
    *,
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    resolved_node = get_static_node(node_id)
    if not resolved_node and isinstance(current_map_position, dict):
        resolved_node = get_static_node(current_map_position.get("node_id"))
    if not resolved_node:
        return None
    detail: dict[str, Any] = {
        "node_id": str(resolved_node.get("node_id") or ""),
        "label": str(resolved_node.get("label") or resolved_node.get("node_id") or ""),
        "node_type": str(resolved_node.get("node_type") or "zone"),
        "area_label": str(resolved_node.get("area_label") or resolved_node.get("label") or ""),
    }
    for key in ("short_description", "inspect_summary", "travel_note", "service_hints", "danger_note"):
        value = resolved_node.get(key)
        if isinstance(value, list):
            detail[key] = [str(item) for item in value if str(item or "").strip()]
        elif value is not None and str(value).strip():
            detail[key] = value
    return detail


def get_static_node_inspect_result(
    *,
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
    source: str = "registry",
) -> dict[str, Any] | None:
    detail = get_static_node_detail(node_id=node_id, current_map_position=current_map_position)
    if not detail:
        return None
    return {
        "node_id": detail["node_id"],
        "label": detail["label"],
        "node_type": detail["node_type"],
        "inspect_summary": str(detail.get("inspect_summary") or detail.get("short_description") or ""),
        "short_description": str(detail.get("short_description") or detail.get("inspect_summary") or ""),
        "travel_note": str(detail.get("travel_note") or "") or None,
        "service_hints": list(detail.get("service_hints") or []) or None,
        "danger_note": str(detail.get("danger_note") or "") or None,
        "source": str(source or "registry"),
    }
