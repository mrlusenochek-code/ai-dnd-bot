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
        "service_hints": ["охотничьи припасы", "ночлег под крышей", "рубежная поддержка", "готовность базы"],
        "services": ["safe_rest", "resupply", "local_guidance", "frontier_support", "frontier_readiness"],
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
    {
        "node_id": "northwatch_outpost",
        "label": "Северный рубеж",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Северный рубеж",
        "zone_band": "border",
        "short_description": "Небольшой дозорный узел с костром, навесами и сторожевой линией отмечает первый обжитой рубеж за старой дорогой.",
        "inspect_summary": "Здесь быстро становится ясно, где держится безопасная линия патруля, где выдают снабжение и куда уходит тёмный проход в зольный распадок.",
        "travel_note": "Первый устойчивый якорь за пределом стартового региона и точка сбора для дальнейших ходов по северному рубежу.",
        "service_hints": ["караульный костёр", "сводки дозора", "короткий отдых под навесом"],
        "services": ["safe_rest", "local_guidance"],
        "aliases": (
            "северный рубеж",
            "северный дозор",
            "рубежный пост",
        ),
    },
    {
        "node_id": "northwatch_quartermaster",
        "label": "Интендантский двор",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Интендантский двор",
        "zone_band": "border",
        "short_description": "Под навесами двора разбиты ящики, сушатся плащи и ведётся скромная выдача дорожного добра для тех, кого дозор уже знает.",
        "inspect_summary": "Здесь видно, что рубеж держится не героикой, а порядком: склад, вода, бинты и короткие указания по ходу патруля.",
        "travel_note": "Лучшее место региона, чтобы перевести дух, сверить маршрут и получить снабжение перед опасным вылазом.",
        "service_hints": ["паёк", "бинты", "патрульные сводки"],
        "services": ["safe_rest", "resupply", "local_guidance"],
        "aliases": (
            "интендантский двор",
            "склад рубежа",
            "двор снабжения",
        ),
    },
    {
        "node_id": "northwatch_palisade",
        "label": "Сигнальная палисада",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Северный рубеж",
        "zone_band": "border",
        "short_description": "Палисад с сигнальными щитами и старым рогом смотрит на рубеж и на дальнюю, уже не такую тихую землю.",
        "inspect_summary": "С палисады читается линия дозора, видно, где зольный проход темнеет сильнее обычного, и где на склоне стоит битый редут.",
        "travel_note": "Главная обзорная точка рубежа перед выходом на опасный фронтир.",
        "aliases": (
            "сигнальная палисада",
            "палисада",
            "дозорная палисада",
        ),
    },
    {
        "node_id": "ash_pass",
        "label": "Зольный проход",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Зольный проход",
        "zone_band": "danger",
        "short_description": "Узкий тёмный ход между серыми откосами пахнет гарью и сырой глиной, а дозор держит его как самую нервную ветку рубежа.",
        "inspect_summary": "Здесь уже нет мирного ритма поста: проход сыплется, ветер тянет пеплом, а старый редут на отлёте выглядит почти брошенным.",
        "travel_note": "Опасный frontier-ход, куда стоит идти только после короткой подготовки на рубеже.",
        "danger_note": "Плохая видимость, осыпи и риск наткнуться на тревожный след раньше, чем успеешь развернуться.",
        "aliases": (
            "зольный проход",
            "зольная тропа",
            "проход в пепле",
        ),
    },
    {
        "node_id": "broken_redoubt",
        "label": "Разбитый редут",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Зольный проход",
        "zone_band": "danger",
        "short_description": "Каменный редут на краю прохода пережил худшие годы рубежа, но теперь стоит пустой, пробитый ветром и старыми ударами.",
        "inspect_summary": "Отсюда видно, как рубеж держится на тонкой линии между дозором и заброшенным фронтиром; место даёт обзор, но не обещает покоя.",
        "travel_note": "Рискованный ориентир за пределом спокойного дозорного узла.",
        "danger_note": "Под стеной легко застрять без обзора, а у разрушенной кладки слышно каждый шаг.",
        "aliases": (
            "разбитый редут",
            "старый редут",
            "редут",
        ),
    },
    {
        "node_id": "western_road_watch",
        "label": "Западный тракт",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Западный тракт",
        "zone_band": "safe",
        "short_description": "Широкий западный тракт сразу ощущается как живая дорога: здесь ещё держится порядок, но уже заметны задержки, следы недавних обозов и спешные развороты на обочине.",
        "inspect_summary": "От входной стоянки читаются двор для возчиков, дорожная арка с отметками и более тёмный объезд, где колея уходит в неровный край тракта.",
        "travel_note": "Первый устойчивый якорь western_road перед дальнейшим дорожным ходом и локальными проверками свежих следов.",
        "aliases": (
            "западный тракт",
            "тракт за воротами",
            "западная дорога",
        ),
    },
    {
        "node_id": "waystation_yard",
        "label": "Постоялый двор у тракта",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Постоялый двор у тракта",
        "zone_band": "border",
        "short_description": "Небольшой двор у западной дороги держится на коновязях, навесах и людях, которые привыкли считать чужую задержку по сломанным осям и грязным мешкам.",
        "inspect_summary": "Здесь не стоит ждать большой безопасности, но именно сюда стекаются дорожные слухи, усталые возчики и короткая помощь для тех, кто возвращается с тракта не с пустыми руками.",
        "travel_note": "Главная roadside support-точка western_road перед повторным выходом на путь.",
        "service_hints": ["дорожный навес", "обозные припасы", "сводка возчиков"],
        "services": ["safe_rest", "resupply", "local_guidance"],
        "aliases": (
            "постоялый двор",
            "двор у тракта",
            "обозный двор",
        ),
    },
    {
        "node_id": "mile_marker_arch",
        "label": "Верстовая арка",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Западный тракт",
        "zone_band": "border",
        "short_description": "Старая каменная арка с выцветшими метками до сих пор служит дорожным ориентиром тем, кто умеет читать чужие пометки на столбах и в счётах обозов.",
        "inspect_summary": "На арке видны дорожные зарубки, свежая меловая разметка и следы наскоро переписанных грузовых знаков.",
        "travel_note": "Главный waymarker western_road, где тракт читается по следам, а не по приказу.",
        "aliases": (
            "верстовая арка",
            "дорожная арка",
            "арка тракта",
        ),
    },
    {
        "node_id": "rutted_detour",
        "label": "Разбитый объезд",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Разбитый объезд",
        "zone_band": "danger",
        "short_description": "Объезд уходит от основного тракта в колею с разбитым краем, где грязь и следы телег спорят между собой за каждую удобную линию прохода.",
        "inspect_summary": "Здесь уже нет ровного дорожного ритма: колея рвётся, следы свежих колёс уходят вбок, а дальше виден только силуэт брошенной телеги.",
        "travel_note": "Рискованный roadside node western_road, где задержка и следы недавнего прохода читаются лучше, чем сам путь.",
        "danger_note": "У разбитого объезда легко потерять темп: колея тянет в сторону, а удобный отход назад не всегда виден сразу.",
        "aliases": (
            "разбитый объезд",
            "объезд",
            "разбитая колея",
        ),
    },
    {
        "node_id": "broken_waycart",
        "label": "Брошенная повозка",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Разбитый объезд",
        "zone_band": "danger",
        "short_description": "Перекошенная повозка лежит у края объезда как немой отчёт о спешном дорожном срыве: не лагерь, не руина, а свежая поломка на живом пути.",
        "inspect_summary": "У сломанной оси видны порванные ремни, следы спешной перегрузки и короткой остановки, после которой обоз ушёл дальше налегке.",
        "travel_note": "Опасная trace-ветка western_road для короткого расследования дорожной задержки.",
        "danger_note": "Возле повозки мало укрытия и много ложных следов, если задержаться дольше нужного.",
        "aliases": (
            "брошенная повозка",
            "сломанная повозка",
            "повозка",
        ),
    },
    {
        "node_id": "deep_marsh_threshold",
        "label": "Глубокие болота",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Глубокие болота",
        "zone_band": "danger",
        "short_description": "За болотной кромкой земля почти сразу делается мягче, тише и менее честной: вода блестит под травой, а тропа живёт только пока её помнят.",
        "inspect_summary": "На пороге глубоких болот ещё держатся несколько сухих кочек и следы старых меток, но дальше путь уже ведёт по сырому наитию, а не по уверенной дороге.",
        "travel_note": "Первый якорь за знакомой болотной кромкой, где можно решить, идти ли к приюту, к старому камню или глубже в чёрную воду.",
        "danger_note": "Туман и стоячая вода быстро стирают направление, если задержаться без опорной метки.",
        "aliases": (
            "глубокие болота",
            "болотный порог",
            "порог болот",
        ),
    },
    {
        "node_id": "reed_shelter",
        "label": "Тростниковый приют",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Тростниковый приют",
        "zone_band": "border",
        "short_description": "Низкий настил под тростниковым навесом даёт редкую сухую передышку тем, кто умеет вернуться к нему до полного тумана.",
        "inspect_summary": "Приют держится на корзинах, кольях и старом болотном опыте: здесь не снабжают, а спасают от лишней сырости и дают короткий местный совет.",
        "travel_note": "Самая тихая точка deep_marsh, где можно перевести дух и получить осторожную болотную помощь.",
        "service_hints": ["сухой настил", "тихий кров", "болотные приметы"],
        "services": ["safe_rest", "shrine_aid", "local_guidance"],
        "aliases": (
            "тростниковый приют",
            "болотный приют",
            "навес в тростнике",
        ),
    },
    {
        "node_id": "drowned_waystone",
        "label": "Утопленный путевой камень",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Глубокие болота",
        "zone_band": "border",
        "short_description": "Старый камень почти ушёл в мох и воду, но на его боку ещё держатся отметки, по которым в болоте различают живую тропу и пустой круг.",
        "inspect_summary": "У камня читаются старые болотные насечки и направление к более тёмной воде, где когда-то держали переправу.",
        "travel_note": "Главный landmark deep_marsh, который помогает не потерять смысл направления.",
        "aliases": (
            "утопленный путевой камень",
            "путевой камень",
            "болотный камень",
        ),
    },
    {
        "node_id": "blackwater_run",
        "label": "Чёрная протока",
        "node_type": "zone",
        "map_level": "region",
        "area_label": "Чёрная протока",
        "zone_band": "danger",
        "short_description": "Тёмная протока режет болото узким чёрным ходом, где каждый шаг зависит от зыбкой кромки и чужих старых вешек.",
        "inspect_summary": "Здесь болото уже не шепчет, а тянет вниз: вода закрывает берега, а дальше из тумана проступает только что-то вроде старой переправы.",
        "travel_note": "Рискованный wetland-ход deep_marsh, куда лучше идти с понятной приметой и без долгой остановки.",
        "danger_note": "Кочки подмыты, обзор короткий, а ошибочный шаг быстро превращает отход в борьбу с грязью.",
        "aliases": (
            "чёрная протока",
            "тёмная протока",
            "протока",
        ),
    },
    {
        "node_id": "sunken_ferry",
        "label": "Затонувшая переправа",
        "node_type": "landmark",
        "map_level": "landmark",
        "area_label": "Чёрная протока",
        "zone_band": "danger",
        "short_description": "Остатки старой болотной переправы торчат из чёрной воды как напоминание, что когда-то здесь ходили увереннее, чем теперь.",
        "inspect_summary": "У сломанного настила заметны застрявшие верёвки, обломки лодочного борта и следы недавней поспешной остановки.",
        "travel_note": "Опасная scout-ветка deep_marsh за пределом уверенного starter slice.",
        "danger_note": "У переправы легко застрять между водой и скользкими сваями, если идти сюда без короткой цели.",
        "aliases": (
            "затонувшая переправа",
            "старая переправа",
            "переправа",
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
    {
        "from_node_id": "northwatch_outpost",
        "to_node_id": "northwatch_quartermaster",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "branch_road",
    },
    {
        "from_node_id": "northwatch_quartermaster",
        "to_node_id": "northwatch_outpost",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "branch_road",
    },
    {
        "from_node_id": "northwatch_outpost",
        "to_node_id": "northwatch_palisade",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
    },
    {
        "from_node_id": "northwatch_palisade",
        "to_node_id": "northwatch_outpost",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "northwatch_outpost",
        "to_node_id": "ash_pass",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "forest_track",
    },
    {
        "from_node_id": "ash_pass",
        "to_node_id": "northwatch_outpost",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "forest_track",
    },
    {
        "from_node_id": "northwatch_quartermaster",
        "to_node_id": "ash_pass",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "forest_track",
    },
    {
        "from_node_id": "ash_pass",
        "to_node_id": "northwatch_quartermaster",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "forest_track",
    },
    {
        "from_node_id": "ash_pass",
        "to_node_id": "broken_redoubt",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
    },
    {
        "from_node_id": "broken_redoubt",
        "to_node_id": "ash_pass",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "deep_marsh_threshold",
        "to_node_id": "reed_shelter",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "bog_track",
    },
    {
        "from_node_id": "reed_shelter",
        "to_node_id": "deep_marsh_threshold",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "bog_track",
    },
    {
        "from_node_id": "deep_marsh_threshold",
        "to_node_id": "drowned_waystone",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "bog_track",
    },
    {
        "from_node_id": "drowned_waystone",
        "to_node_id": "deep_marsh_threshold",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "deep_marsh_threshold",
        "to_node_id": "blackwater_run",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "bog_track",
    },
    {
        "from_node_id": "blackwater_run",
        "to_node_id": "deep_marsh_threshold",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "drowned_waystone",
        "to_node_id": "blackwater_run",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "bog_track",
    },
    {
        "from_node_id": "blackwater_run",
        "to_node_id": "drowned_waystone",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "bog_track",
    },
    {
        "from_node_id": "blackwater_run",
        "to_node_id": "sunken_ferry",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
    },
    {
        "from_node_id": "sunken_ferry",
        "to_node_id": "blackwater_run",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "western_road_watch",
        "to_node_id": "waystation_yard",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "waystation_yard",
        "to_node_id": "western_road_watch",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "western_road_watch",
        "to_node_id": "mile_marker_arch",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "mile_marker_arch",
        "to_node_id": "western_road_watch",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "western_road_watch",
        "to_node_id": "rutted_detour",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "branch_road",
    },
    {
        "from_node_id": "rutted_detour",
        "to_node_id": "western_road_watch",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "waystation_yard",
        "to_node_id": "rutted_detour",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "branch_road",
    },
    {
        "from_node_id": "rutted_detour",
        "to_node_id": "waystation_yard",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
    },
    {
        "from_node_id": "mile_marker_arch",
        "to_node_id": "rutted_detour",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "rutted_detour",
        "to_node_id": "mile_marker_arch",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "road",
    },
    {
        "from_node_id": "rutted_detour",
        "to_node_id": "broken_waycart",
        "action_kind": "move",
        "route_kind": "landmark_move",
        "link_kind": "approach",
    },
    {
        "from_node_id": "broken_waycart",
        "to_node_id": "rutted_detour",
        "action_kind": "move",
        "route_kind": "zone_move",
        "link_kind": "return",
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
    {
        "node_id": "northwatch_palisade",
        "result_type": "landmark_revealed",
        "discovery_scope": "frontier_overwatch",
        "discovered_node_ids": ["broken_redoubt"],
        "discovered_route_ids": ["ash_pass->broken_redoubt:move"],
        "discovered_notes": [
            "С палисады становится понятнее, где среди серых откосов стоит разбитый редут и как к нему держать короткий опасный ход."
        ],
    },
    {
        "node_id": "drowned_waystone",
        "result_type": "landmark_revealed",
        "discovery_scope": "marsh_waymark",
        "discovered_node_ids": ["sunken_ferry"],
        "discovered_route_ids": ["blackwater_run->sunken_ferry:move"],
        "discovered_notes": [
            "По болотным зарубкам у камня становится понятнее, где за чёрной протокой проступает затонувшая переправа и как к ней держать короткий рискованный ход."
        ],
    },
    {
        "node_id": "mile_marker_arch",
        "result_type": "landmark_revealed",
        "discovery_scope": "roadside_trace",
        "discovered_node_ids": ["broken_waycart"],
        "discovered_route_ids": ["rutted_detour->broken_waycart:move"],
        "discovered_notes": [
            "По дорожным пометкам на верстовой арке становится понятнее, где у разбитого объезда стоит брошенная повозка и почему след свежего обоза уходит именно туда."
        ],
    },
)


STATIC_MAP_CONTEXT_ACTION_EFFECTS: tuple[dict[str, Any], ...] = (
    {
        "node_id": "craft_town",
        "action_id": "trace_watchtower_bearing",
        "label": "Сверить береговой ориентир",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": False,
        "result_type": "local_clue_found",
        "summary": "Сверить береговую наводку с местными отметками у воды.",
        "result_summary": "Группа сопоставляет береговую наводку с местными отметками и уточняет, как держать сторожевую башню в ориентире.",
        "discovered_notes": [
            "Береговую башню лучше держать чуть севернее причала: так проще не потерять дорогу обратно к городку."
        ],
        "applied_effects": ["local_clue:watchtower_bearing"],
    },
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
    {
        "node_id": "northwatch_palisade",
        "action_id": "review_signal_chalk",
        "label": "Сверить сигнальные метки",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": True,
        "result_type": "local_clue_found",
        "summary": "Сверить свежие сигнальные метки на палисаде с последней сводкой дозора.",
        "result_summary": "Группа разбирает свежие метки на палисаде и подтверждает, что тревога на рубеже чаще всего срывается не в сам проход, а к разбитому редуту над ним.",
        "discovered_notes": [
            "По свежим меткам видно: дозор чаще всего смотрит не в сам проход, а чуть западнее, к разбитому редуту на склоне.",
            "Старые пометки на досках совпадают с недавней сводкой у костра: если идти по следу, то проверять стоит именно редут, а не пустую осыпь у входа."
        ],
        "applied_effects": ["local_clue:northwatch_signals"],
        "node_state_flags": ["northwatch_signal_report_taken"],
        "node_state_summary": "На палисаде уже сверяли сигнальные метки и отмечали, откуда на рубеже чаще всего приходит тревога.",
    },
    {
        "node_id": "northwatch_palisade",
        "action_id": "set_relay_watch",
        "label": "Развернуть relay-дозор",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "С первой базовой поддержкой разметить короткий relay-порядок на палисаде.",
        "result_summary": "Группа помогает дозору разложить первый relay-порядок у палисады: свежие chalk marks и запасной рог делают редутный ход чуть менее слепым, даже если рубеж всё ещё держится на коротких решениях.",
        "discovered_notes": [
            "С первой поддержкой с базы на палисаде уже можно держать не только тревогу, но и короткий relay-порядок на случай нового сигнала с редута."
        ],
        "applied_effects": ["support_deployment:northwatch_relay", "readiness:northwatch_prepared"],
        "node_state_flags": ["northwatch_relay_watch_prepared"],
        "node_state_summary": "На палисаде уже развернули первый relay-порядок под базовую поддержку с лесного посёлка.",
        "reveal_node_ids": ["broken_redoubt"],
        "requires_any_group_node_state_flags": ["frontier_support_prepared"],
    },
    {
        "node_id": "northwatch_palisade",
        "action_id": "set_relay_watch",
        "label": "Развернуть relay-дозор",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "При ready-stage поддержке закрепить более надёжный relay-порядок на палисаде.",
        "result_summary": "С готовой support-линией группа переводит палисаду в более собранный relay-mode: сигнальные щиты читаются быстрее, запасной вызов к двору держится увереннее, а ход к редуту уже проще прикрывать короткой перекличкой.",
        "discovered_notes": [
            "Ready-stage support позволяет держать палисаду как настоящую relay-точку, а не как одиночный наблюдательный забор."
        ],
        "applied_effects": ["support_deployment:northwatch_relay", "readiness:northwatch_ready"],
        "node_state_flags": ["northwatch_relay_watch_ready"],
        "node_state_summary": "На палисаде уже закрепили более надёжный relay-порядок под готовую линию поддержки.",
        "reveal_node_ids": ["broken_redoubt"],
        "requires_any_group_node_state_flags": ["frontier_support_ready"],
    },
    {
        "node_id": "northwatch_palisade",
        "action_id": "set_relay_watch",
        "label": "Развернуть relay-дозор",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "При полной поддержке довести палисаду до лучшего relay-порядка рубежа.",
        "result_summary": "При committed-stage backing палисада получает лучшую полевую версию своей readiness-цепочки: relay line до двора держится ровно, сигналы с редута больше не тонут в аврале, а сам северный край ощущается организованнее, чем раньше.",
        "discovered_notes": [
            "Полный support tier превращает палисаду в настоящую relay strongpoint, а не только в место тревожных пометок."
        ],
        "applied_effects": ["support_deployment:northwatch_relay", "readiness:northwatch_committed"],
        "node_state_flags": ["northwatch_relay_watch_committed"],
        "node_state_summary": "На палисаде уже держат лучший relay-порядок северного рубежа под полной поддержкой базы.",
        "reveal_node_ids": ["broken_redoubt"],
        "requires_any_group_node_state_flags": ["frontier_support_committed"],
    },
    {
        "node_id": "drowned_waystone",
        "action_id": "read_moss_waymarks",
        "label": "Считать мшистые метки",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": True,
        "result_type": "local_clue_found",
        "summary": "Разобрать старые болотные зарубки и мшистые насечки на путевом камне.",
        "result_summary": "Группа сверяет болотные насечки на камне и понимает, что надёжный ход идёт не вдоль открытой воды, а в сторону старой затонувшей переправы.",
        "discovered_notes": [
            "Сырые зарубки на камне подсказывают: в глубоком болоте нужно держаться не широкого зеркала воды, а линии старой переправы за чёрной протокой."
        ],
        "applied_effects": ["local_clue:deep_marsh_waymarks"],
        "node_state_flags": ["deep_marsh_waymarks_read"],
        "node_state_summary": "Утопленный путевой камень уже читали как рабочую болотную метку, а не как пустую развалину.",
    },
    {
        "node_id": "reed_shelter",
        "action_id": "braid_reed_wayline",
        "label": "Сплести тростниковую wayline",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "На первой поддержке с базы сплести короткую refuge-wayline от приюта.",
        "result_summary": "Группа вместе с хозяйкой приюта натягивает первую тихую reed wayline: возврат к сухому настилу теперь читается увереннее, а болотный ход уже не выглядит полностью одиноким.",
        "discovered_notes": [
            "Даже первый support stage позволяет приюту держать короткую reed wayline, по которой проще возвращаться к сухому настилу до полной темноты."
        ],
        "applied_effects": ["support_deployment:deep_marsh_wayline", "survival:deep_marsh_prepared"],
        "node_state_flags": ["deep_marsh_wayline_prepared"],
        "node_state_summary": "У тростникового приюта уже сплели первую короткую wayline под осторожную поддержку с базы.",
        "reveal_node_ids": ["sunken_ferry"],
        "route_access_updates": [
            {
                "route_id": "blackwater_run->sunken_ferry:move",
                "access_state": "cleared",
                "summary": "Тростниковая wayline делает короткий ход к затонувшей переправе заметно читаемее.",
            },
            {
                "route_id": "sunken_ferry->blackwater_run:move",
                "access_state": "cleared",
                "summary": "Тростниковая wayline помогает увереннее держать обратный ход от затонувшей переправы.",
            },
        ],
        "requires_any_group_node_state_flags": ["frontier_support_prepared"],
    },
    {
        "node_id": "reed_shelter",
        "action_id": "braid_reed_wayline",
        "label": "Сплести тростниковую wayline",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "При ready-stage поддержке протянуть более надёжную marsh-wayline от приюта.",
        "result_summary": "С готовой support-линией приют уже может держать более надёжную marsh-wayline: возвратный ход через сырой край читается спокойнее, а refuge работает не только как укрытие, но и как осторожный wayfinding point.",
        "discovered_notes": [
            "Ready-stage support делает болотную wayline длиннее и надёжнее: приют начинает помогать не только переждать сырость, но и не потерять короткий обратный ход."
        ],
        "applied_effects": ["support_deployment:deep_marsh_wayline", "survival:deep_marsh_ready"],
        "node_state_flags": ["deep_marsh_wayline_ready"],
        "node_state_summary": "У приюта уже держат более надёжную marsh-wayline благодаря готовой поддержке с базы.",
        "reveal_node_ids": ["sunken_ferry"],
        "route_access_updates": [
            {
                "route_id": "blackwater_run->sunken_ferry:move",
                "access_state": "cleared",
                "summary": "Готовая marsh-wayline делает путь к затонувшей переправе заметно надёжнее.",
            },
            {
                "route_id": "sunken_ferry->blackwater_run:move",
                "access_state": "cleared",
                "summary": "Готовая marsh-wayline держит уверенный возврат от затонувшей переправы к чёрной протоке.",
            },
        ],
        "requires_any_group_node_state_flags": ["frontier_support_ready"],
    },
    {
        "node_id": "reed_shelter",
        "action_id": "braid_reed_wayline",
        "label": "Сплести тростниковую wayline",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "При полной поддержке закрепить лучший refuge-wayline ход deep_marsh.",
        "result_summary": "При committed-stage backing тростниковый приют закрепляет лучшую версию своей quiet wayline: болотный возврат идёт увереннее, refuge перестаёт быть хрупкой случайной остановкой и становится настоящей внешней survival-опорой.",
        "discovered_notes": [
            "Полный support tier позволяет deep_marsh держать лучшую quiet wayline к приюту и заметно снижает хаос на возвращении."
        ],
        "applied_effects": ["support_deployment:deep_marsh_wayline", "survival:deep_marsh_committed"],
        "node_state_flags": ["deep_marsh_wayline_committed"],
        "node_state_summary": "У приюта уже закрепили лучшую болотную wayline под полной поддержкой с базы.",
        "reveal_node_ids": ["sunken_ferry"],
        "route_access_updates": [
            {
                "route_id": "blackwater_run->sunken_ferry:move",
                "access_state": "cleared",
                "summary": "Лучшая quiet wayline делает ferry branch самым читаемым болотным ходом этого участка.",
            },
            {
                "route_id": "sunken_ferry->blackwater_run:move",
                "access_state": "cleared",
                "summary": "Лучшая quiet wayline держит самый уверенный возвратный ход от ferry branch обратно к протоке.",
            },
        ],
        "requires_any_group_node_state_flags": ["frontier_support_committed"],
    },
    {
        "node_id": "mile_marker_arch",
        "action_id": "read_waybill_marks",
        "label": "Сверить дорожные отметки",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": True,
        "result_type": "local_clue_found",
        "summary": "Разобрать свежие меловые знаки и грузовые пометки на верстовой арке.",
        "result_summary": "Группа сверяет дорожные отметки на арке и понимает, что задержка прошедшего обоза связана не с основным трактом, а с уходом в разбитый объезд к брошенной повозке.",
        "discovered_notes": [
            "На камне видно: обоз ушёл с главной дороги в объезд, быстро разгрузился и уже после поломки продолжил путь налегке."
        ],
        "applied_effects": ["local_clue:western_road_waybill"],
        "node_state_flags": ["western_road_waybill_read"],
        "node_state_summary": "На верстовой арке уже сверяли дорожные отметки и читали по ним свежий след обозной задержки.",
    },
    {
        "node_id": "mile_marker_arch",
        "action_id": "reset_detour_markers",
        "label": "Обновить detour-маркеры",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "С первой поддержкой с базы вернуть на объезд базовые marker posts.",
        "result_summary": "Группа обновляет первые detour markers у арки: разбитый объезд по-прежнему неудобен, но corridor уже держится на понятных отметках, а не только на чужой памяти возчиков.",
        "discovered_notes": [
            "Первый support stage позволяет снова отметить разбитый объезд так, чтобы дорожный возврат держался не только на свежем следе, но и на marker posts."
        ],
        "applied_effects": ["support_deployment:western_road_markers", "corridor:western_road_prepared"],
        "node_state_flags": ["western_road_detour_markers_prepared"],
        "node_state_summary": "У верстовой арки уже обновили первые detour markers под начальную поддержку с базы.",
        "route_access_updates": [
            {
                "route_id": "rutted_detour->broken_waycart:move",
                "access_state": "cleared",
                "summary": "Первые detour markers делают короткий подход к брошенной повозке понятнее прямо с объезда.",
            },
            {
                "route_id": "broken_waycart->rutted_detour:move",
                "access_state": "cleared",
                "summary": "Первые detour markers помогают не потерять обратный corridor line от брошенной повозки.",
            },
        ],
        "requires_any_group_node_state_flags": ["frontier_support_prepared"],
    },
    {
        "node_id": "mile_marker_arch",
        "action_id": "reset_detour_markers",
        "label": "Обновить detour-маркеры",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "При ready-stage поддержке собрать более надёжную marker-line для объезда.",
        "result_summary": "С готовой линией поддержки арка снова работает как настоящий corridor marker: detour line читается ровнее, yard легче сводит задержки с реальным следом, а дорожный риск уже проще пережить без лишней путаницы.",
        "discovered_notes": [
            "Ready-stage support делает detour markers не случайной подмогой, а рабочей линией corridor guidance."
        ],
        "applied_effects": ["support_deployment:western_road_markers", "corridor:western_road_ready"],
        "node_state_flags": ["western_road_detour_markers_ready"],
        "node_state_summary": "У верстовой арки уже собрали более надёжную marker-line под готовую поддержку с базы.",
        "route_access_updates": [
            {
                "route_id": "rutted_detour->broken_waycart:move",
                "access_state": "cleared",
                "summary": "Готовая marker-line делает ход к повозке ровнее и читабельнее даже на разбитом объезде.",
            },
            {
                "route_id": "broken_waycart->rutted_detour:move",
                "access_state": "cleared",
                "summary": "Готовая marker-line удерживает уверенный обратный ход от повозки к объезду.",
            },
        ],
        "requires_any_group_node_state_flags": ["frontier_support_ready"],
    },
    {
        "node_id": "mile_marker_arch",
        "action_id": "reset_detour_markers",
        "label": "Обновить detour-маркеры",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "При полной поддержке закрепить лучший corridor-marker response на западном тракте.",
        "result_summary": "При committed-stage backing группа доводит detour markers до лучшей версии: объезд всё ещё rough, но western_road наконец держит явную corridor line, по которой легче и проверять свежий след, и возвращаться без лишней потери темпа.",
        "discovered_notes": [
            "Полный support tier превращает дорожные marker posts в настоящую corridor support-line для western_road."
        ],
        "applied_effects": ["support_deployment:western_road_markers", "corridor:western_road_committed"],
        "node_state_flags": ["western_road_detour_markers_committed"],
        "node_state_summary": "У верстовой арки уже закрепили лучшую corridor marker-line под полной поддержкой базы.",
        "route_access_updates": [
            {
                "route_id": "rutted_detour->broken_waycart:move",
                "access_state": "cleared",
                "summary": "Лучшая corridor marker-line делает detour branch к повозке самым читаемым дорожным следом на этом участке.",
            },
            {
                "route_id": "broken_waycart->rutted_detour:move",
                "access_state": "cleared",
                "summary": "Лучшая corridor marker-line удерживает самый надёжный возвратный ход от broken_waycart обратно в detour corridor.",
            },
        ],
        "requires_any_group_node_state_flags": ["frontier_support_committed"],
    },
    {
        "node_id": "broken_redoubt",
        "action_id": "log_redoubt_signal_cache",
        "label": "Сверить сигнальный тайник редута",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": True,
        "result_type": "local_clue_found",
        "summary": "Разобрать уцелевшие сигнальные бирки и остатки тайника у разбитой кладки.",
        "result_summary": "У разбитого редута группа находит не просто брошенный ящик, а аккуратно собранный сигнальный тайник: обрывок watch-rotation slate и складская бирка показывают, что рубеж пытались держать организованно до самого последнего короткого отхода. Такой след уже стоит нести назад на пост.",
        "discovered_notes": [
            "В тайнике редута сохранились сигнальная бирка и короткая watch-rotation slate: это уже не случайный мусор, а организованный след, который стоит унести обратно к северному двору."
        ],
        "applied_effects": ["local_clue:northwatch_signal_cache", "intel:return_worthy:northwatch"],
        "node_state_flags": ["northwatch_redoubt_cache_logged"],
        "node_state_summary": "У разбитого редута уже сверили сигнальный тайник и собрали организованный след последнего дозорного отхода.",
    },
    {
        "node_id": "sunken_ferry",
        "action_id": "trace_ferry_moorings",
        "label": "Проверить швартовые метки",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": True,
        "result_type": "local_clue_found",
        "summary": "Сверить уцелевшие швартовые метки и понять, как переправа держала короткий болотный ход.",
        "result_summary": "У затонувшей переправы группа находит не только свежий след, но и рабочую память перехода: на сваях сохранились тихие швартовые метки и срез тростника, по которым видно, где здесь держали осторожный возврат через чёрную воду.",
        "discovered_notes": [
            "На старых сваях ещё читаются тихие швартовые метки: deep_marsh помнит эту переправу не как легенду, а как осторожный рабочий crossing-memory."
        ],
        "applied_effects": ["local_clue:deep_marsh_moorings", "intel:return_worthy:deep_marsh"],
        "node_state_flags": ["deep_marsh_ferry_moorings_logged"],
        "node_state_summary": "У затонувшей переправы уже сверили швартовые метки и подтвердили старую crossing-memory болота.",
    },
    {
        "node_id": "broken_waycart",
        "action_id": "sort_waycart_manifest",
        "label": "Разобрать обозную ведомость",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": True,
        "result_type": "local_clue_found",
        "summary": "Собрать уцелевшие грузовые бирки и понять, что именно сорвало дорожный ритм на объезде.",
        "result_summary": "У брошенной повозки группа находит не просто поломку, а понятный дорожный срыв: обрывок waybill и мел на мешочном крюке показывают, что обоз разгружали по спешке, чтобы любой ценой вернуть ход на тракт. Такой след уже стоит нести назад во двор у дороги.",
        "discovered_notes": [
            "У повозки сохранился обрывок waybill с пометкой о срочной перегрузке: западный тракт получил не слух, а настоящий corridor-proof того, как именно сорвался обоз."
        ],
        "applied_effects": ["local_clue:western_road_manifest", "intel:return_worthy:western_road"],
        "node_state_flags": ["western_road_waycart_manifest_logged"],
        "node_state_summary": "У брошенной повозки уже разобрали обрывок обозной ведомости и закрепили понятный след дорожного срыва.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "arrange_frontier_evidence",
        "label": "Разложить frontier evidence",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": False,
        "result_type": "local_clue_found",
        "summary": "Свести первый возвращённый field proof в конкретную evidence-сводку для посёлка.",
        "result_summary": "В лесном посёлке впервые раскладывают не общую frontier тревогу, а настоящий возвращённый field proof: один конкретный след с внешней activated branch уже показывает, что рубеж можно читать не только по слухам и сводкам, но и по принесённым остаткам реального хода.",
        "discovered_notes": [
            "Первый возвращённый field proof меняет тон посёлка: frontier теперь обсуждают не только как общее давление, а как систему реальных следов, которые можно собирать и сверять дома."
        ],
        "applied_effects": ["frontier_evidence:started", "intel:frontier_evidence"],
        "node_state_flags": ["frontier_evidence_started"],
        "node_state_summary": "В лесном посёлке уже начали собирать конкретную frontier evidence-сводку по возвращённым proof signals.",
        "requires_min_group_node_state_flags": 1,
        "group_node_state_flag_pool": [
            "northwatch_redoubt_cache_logged",
            "deep_marsh_ferry_moorings_logged",
            "western_road_waycart_manifest_logged",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "arrange_frontier_evidence",
        "label": "Разложить frontier evidence",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": False,
        "result_type": "local_clue_found",
        "summary": "Сопоставить два разных returned proofs и увидеть comparative evidence picture.",
        "result_summary": "Когда в посёлок возвращают уже два разных field proofs, здесь появляется comparative evidence picture: северный organized trace, болотная crossing-memory или дорожный corridor-proof уже можно сравнивать как части одной frontier system, а не как изолированные находки.",
        "discovered_notes": [
            "Два разных returned proofs позволяют посёлку сравнивать не только pressure, но и сами типы следа: рубеж начинает читаться через конкретные evidence patterns, а не через одну тревогу на всех."
        ],
        "applied_effects": ["frontier_evidence:compared", "intel:frontier_evidence_comparison"],
        "node_state_flags": ["frontier_evidence_compared"],
        "node_state_summary": "В лесном посёлке уже сравнивают два разных returned proofs как части одной frontier evidence picture.",
        "requires_min_group_node_state_flags": 2,
        "group_node_state_flag_pool": [
            "northwatch_redoubt_cache_logged",
            "deep_marsh_ferry_moorings_logged",
            "western_road_waycart_manifest_logged",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "arrange_frontier_evidence",
        "label": "Разложить frontier evidence",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": False,
        "result_type": "local_clue_found",
        "summary": "Собрать полную returned frontier evidence picture по всем трём activated branches.",
        "result_summary": "После трёх возвращённых field proofs лесной посёлок получает полную returned frontier evidence picture: северный signal cache, болотные швартовые метки и дорожный waybill scrap складываются в concrete home-base reading того, как frontier держится и срывается на разных краях одной системы.",
        "discovered_notes": [
            "Три returned proofs дают посёлку уже не только pattern, а полную evidence picture frontier system: разные края приносят разные следы, но теперь все они лежат дома как одна проверяемая картина."
        ],
        "applied_effects": ["frontier_evidence:compiled", "intel:frontier_evidence_full"],
        "node_state_flags": ["frontier_evidence_compiled"],
        "node_state_summary": "В лесном посёлке уже собрали полную returned frontier evidence picture по всем трём activated branches.",
        "requires_min_group_node_state_flags": 3,
        "group_node_state_flag_pool": [
            "northwatch_redoubt_cache_logged",
            "deep_marsh_ferry_moorings_logged",
            "western_road_waycart_manifest_logged",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "issue_frontier_directives",
        "label": "Выдать рубежное предписание",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Выдать первое направленное предписание по северному рубежу на основе возвращённого signal cache.",
        "result_summary": "Лесной посёлок впервые переходит от evidence к координации и отправляет назад northwatch directive: signal cache у редута требует держать organised redoubt watch, а не ждать новой общей тревоги.",
        "discovered_notes": [
            "Первое frontier directive уходит на северный рубеж: теперь база не только собирает evidence, но и возвращает его в поле как конкретное coordinated order."
        ],
        "applied_effects": ["frontier_directive:northwatch", "coordination:started"],
        "node_state_flags": ["frontier_directive_started", "northwatch_field_directive_issued"],
        "node_state_summary": "В лесном посёлке уже выдали первое рубежное предписание по северному evidence trace.",
        "required_state_flags": ["frontier_evidence_started"],
        "requires_all_group_node_state_flags": ["northwatch_redoubt_cache_logged"],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "issue_frontier_directives",
        "label": "Выдать рубежное предписание",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Выдать первое направленное предписание по болотному evidence trace.",
        "result_summary": "Лесной посёлок впервые переводит returned marsh evidence в directive: quiet crossing-memory у затонувшей переправы требует осторожного route-aware ответа и нового порядка возвратов в deep_marsh.",
        "discovered_notes": [
            "Первое frontier directive уходит в deep_marsh: база начинает координировать не общую тревогу, а конкретный marsh follow-up по возвращённому evidence."
        ],
        "applied_effects": ["frontier_directive:deep_marsh", "coordination:started"],
        "node_state_flags": ["frontier_directive_started", "deep_marsh_field_directive_issued"],
        "node_state_summary": "В лесном посёлке уже выдали первое рубежное предписание по болотному evidence trace.",
        "required_state_flags": ["frontier_evidence_started"],
        "requires_all_group_node_state_flags": ["deep_marsh_ferry_moorings_logged"],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "issue_frontier_directives",
        "label": "Выдать рубежное предписание",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Выдать первое направленное предписание по западному corridor-proof.",
        "result_summary": "Лесной посёлок впервые отправляет назад western_road directive: waybill scrap и сорванный ритм объезда требуют удержать corridor order на тракте, а не просто ждать следующего возврата с дороги.",
        "discovered_notes": [
            "Первое frontier directive уходит на западный тракт: база начинает возвращать evidence в поле как конкретный corridor order."
        ],
        "applied_effects": ["frontier_directive:western_road", "coordination:started"],
        "node_state_flags": ["frontier_directive_started", "western_road_field_directive_issued"],
        "node_state_summary": "В лесном посёлке уже выдали первое рубежное предписание по западному corridor-proof.",
        "required_state_flags": ["frontier_evidence_started"],
        "requires_all_group_node_state_flags": ["western_road_waycart_manifest_logged"],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "issue_frontier_directives",
        "label": "Выдать рубежное предписание",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Свести северный и болотный evidence traces в comparative dispatch.",
        "result_summary": "После двух returned proofs лесной посёлок расширяет dispatch: northwatch и deep_marsh получают уже не одиночный ответ, а comparative directive picture, где organised redoubt watch и cautious marsh return line держатся как части одного coordinated frontier response.",
        "discovered_notes": [
            "Два evidence traces позволяют базе выдать не одно локальное распоряжение, а comparative dispatch для двух разных краёв frontier."
        ],
        "applied_effects": ["frontier_directive:northwatch", "frontier_directive:deep_marsh", "coordination:expanded"],
        "node_state_flags": ["frontier_directive_expanded", "northwatch_field_directive_issued", "deep_marsh_field_directive_issued"],
        "node_state_summary": "В лесном посёлке уже расширили рубежный dispatch на северный и болотный края.",
        "required_state_flags": ["frontier_evidence_compared"],
        "requires_all_group_node_state_flags": ["northwatch_redoubt_cache_logged", "deep_marsh_ferry_moorings_logged"],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "issue_frontier_directives",
        "label": "Выдать рубежное предписание",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Свести северный и дорожный evidence traces в comparative dispatch.",
        "result_summary": "После двух returned proofs лесной посёлок расширяет dispatch: northwatch и western_road получают coordinated directive picture, где redoubt watch и corridor order уже держатся как связанные ответы на одну frontier system.",
        "discovered_notes": [
            "Два evidence traces позволяют базе координировать северный рубеж и тракт уже не порознь, а как части одного frontier response."
        ],
        "applied_effects": ["frontier_directive:northwatch", "frontier_directive:western_road", "coordination:expanded"],
        "node_state_flags": ["frontier_directive_expanded", "northwatch_field_directive_issued", "western_road_field_directive_issued"],
        "node_state_summary": "В лесном посёлке уже расширили рубежный dispatch на северный рубеж и западный тракт.",
        "required_state_flags": ["frontier_evidence_compared"],
        "requires_all_group_node_state_flags": ["northwatch_redoubt_cache_logged", "western_road_waycart_manifest_logged"],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "issue_frontier_directives",
        "label": "Выдать рубежное предписание",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Свести болотный и дорожный evidence traces в comparative dispatch.",
        "result_summary": "После двух returned proofs лесной посёлок расширяет dispatch: deep_marsh и western_road получают comparative directive picture, где marsh return line и corridor order уже читаются как coordinated field response, а не как случайные local fixes.",
        "discovered_notes": [
            "Два evidence traces позволяют базе координировать болота и тракт как разные, но связанные внешние направления frontier."
        ],
        "applied_effects": ["frontier_directive:deep_marsh", "frontier_directive:western_road", "coordination:expanded"],
        "node_state_flags": ["frontier_directive_expanded", "deep_marsh_field_directive_issued", "western_road_field_directive_issued"],
        "node_state_summary": "В лесном посёлке уже расширили рубежный dispatch на болотный край и западный тракт.",
        "required_state_flags": ["frontier_evidence_compared"],
        "requires_all_group_node_state_flags": ["deep_marsh_ferry_moorings_logged", "western_road_waycart_manifest_logged"],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "issue_frontier_directives",
        "label": "Выдать рубежное предписание",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Собрать полный coordinated dispatch по всем трём внешним evidence traces.",
        "result_summary": "После полной returned frontier evidence picture лесной посёлок выдаёт coordinated directives сразу на все три края: northwatch получает redoubt watch order, deep_marsh получает cautious crossing order, а western_road получает corridor control order. База теперь не только понимает frontier system, но и действительно отправляет назад coordinated response.",
        "discovered_notes": [
            "Полный frontier directive picture делает лесной посёлок реальным coordinating base: evidence возвращается домой и сразу уходит обратно в поле как набор region-aware orders."
        ],
        "applied_effects": ["frontier_directive:northwatch", "frontier_directive:deep_marsh", "frontier_directive:western_road", "coordination:full"],
        "node_state_flags": ["frontier_directive_coordinated", "northwatch_field_directive_issued", "deep_marsh_field_directive_issued", "western_road_field_directive_issued"],
        "node_state_summary": "В лесном посёлке уже выдали полный coordinated frontier dispatch по всем трём внешним evidence traces.",
        "required_state_flags": ["frontier_evidence_compiled"],
        "requires_all_group_node_state_flags": ["northwatch_redoubt_cache_logged", "deep_marsh_ferry_moorings_logged", "western_road_waycart_manifest_logged"],
    },
    {
        "node_id": "northwatch_quartermaster",
        "action_id": "post_redoubt_orders",
        "label": "Разложить redoubt orders",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Разложить присланное с базы предписание по redoubt watch и relay response.",
        "result_summary": "На интендантском дворе раскладывают пришедшее с базы redoubt order: северный рубеж теперь держит coordinated watch response не только на привычке дозора, но и по прямому домашнему предписанию.",
        "discovered_notes": [
            "Northwatch впервые выглядит не как одинокий край, а как рубеж, которому база уже вернула назад конкретное coordinated order."
        ],
        "applied_effects": ["frontier_directive:northwatch_field", "coordination:northwatch"],
        "node_state_flags": ["northwatch_directive_posted"],
        "node_state_summary": "На интендантском дворе уже разложили пришедшее с базы redoubt directive.",
    },
    {
        "node_id": "reed_shelter",
        "action_id": "tie_crossing_orders",
        "label": "Связать crossing orders",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Связать тихое болотное предписание по wayline и возвратному crossing order.",
        "result_summary": "У тростникового приюта связывают присланный с базы crossing order: болотный край получает не просто помощь, а coordinated return-aware instruction по тихому ходу через сырую воду.",
        "discovered_notes": [
            "Deep_marsh впервые ощущает не только поддержку, но и прямое домашнее предписание о том, как держать осторожный возвратный crossing line."
        ],
        "applied_effects": ["frontier_directive:deep_marsh_field", "coordination:deep_marsh"],
        "node_state_flags": ["deep_marsh_directive_posted"],
        "node_state_summary": "У тростникового приюта уже связали присланное с базы crossing directive.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "chalk_corridor_orders",
        "label": "Отметить corridor orders",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Отметить присланное с базы corridor order по detour line и возврату с тракта.",
        "result_summary": "На постоялом дворе отмечают присланный с базы corridor order: western_road теперь держит detour response уже не только на следе и marker-line, а по прямому домашнему предписанию о ритме возврата и контроля линии.",
        "discovered_notes": [
            "Западный тракт впервые получает не только поддержку, но и прямое corridor order с базы, привязанное к возвращённому evidence."
        ],
        "applied_effects": ["frontier_directive:western_road_field", "coordination:western_road"],
        "node_state_flags": ["western_road_directive_posted"],
        "node_state_summary": "На постоялом дворе уже отметили присланное с базы corridor directive.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "action_id": "confirm_redoubt_watch",
        "label": "Подтвердить redoubt watch",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "route_cleared",
        "summary": "Провести директиву до реального redoubt watch и закрепить ход к редуту как координируемую линию дозора.",
        "result_summary": "Северный двор не просто раскладывает приказ, а реально проводит его в поле: redoubt watch подтверждён, ash_pass к редуту читается как удерживаемый дозорный ход, а не как одинокий рискованный выход.",
        "discovered_notes": [
            "Northwatch выполняет домашнюю директиву в поле: теперь путь к broken_redoubt держится как подтверждённая watch-line, а не только как найденная опасная ветка."
        ],
        "applied_effects": ["frontier_directive:northwatch_fulfilled", "route:ash_pass_redoubt:secured"],
        "node_state_flags": ["northwatch_directive_fulfilled"],
        "node_state_summary": "На северном рубеже уже подтвердили redoubt watch и закрепили ash_pass как рабочую линию дозора.",
        "route_access_updates": [
            {
                "route_id": "ash_pass->broken_redoubt:move",
                "access_state": "cleared",
                "summary": "Под redoubt watch ash_pass к редуту теперь держится как подтверждённый дозорный ход.",
            },
            {
                "route_id": "broken_redoubt->ash_pass:move",
                "access_state": "cleared",
                "summary": "Обратный ход от редута к ash_pass теперь закреплён как подтверждённая линия дозора.",
            },
        ],
    },
    {
        "node_id": "reed_shelter",
        "action_id": "secure_crossing_line",
        "label": "Закрепить crossing line",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Провести болотную директиву до реальной secured crossing line у quiet water.",
        "result_summary": "Тростниковый приют доводит присланное предписание до дела: crossing line у сырой воды закреплена, возврат через переправу читается осторожнее и надёжнее, чем прежде.",
        "discovered_notes": [
            "Deep_marsh не только получил crossing order, но и действительно закрепил его как тихую working line для осторожного возврата."
        ],
        "applied_effects": ["frontier_directive:deep_marsh_fulfilled", "crossing:secured"],
        "node_state_flags": ["deep_marsh_directive_fulfilled"],
        "node_state_summary": "У тростникового приюта уже закрепили quiet crossing line по присланной директиве.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "stabilize_corridor_handling",
        "label": "Упорядочить corridor handling",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Провести corridor order до реального detour handling на дворе.",
        "result_summary": "На постоялом дворе доводят corridor directive до дела: detour handling больше не держится на случайной спешке, а закрепляется как понятный возвратный порядок для тракта.",
        "discovered_notes": [
            "Western_road теперь не только получил corridor order, но и действительно закрепил его как рабочий порядок двора и detour line."
        ],
        "applied_effects": ["frontier_directive:western_road_fulfilled", "corridor:stabilized"],
        "node_state_flags": ["western_road_directive_fulfilled"],
        "node_state_summary": "На постоялом дворе уже закрепили detour handling по присланной corridor directive.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "action_id": "check_watchroad_courier_slate",
        "label": "Сверить courier slate",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": True,
        "result_type": "local_clue_found",
        "summary": "Сверить courier slate по reopened watch-road line между северным двором и западным трактом.",
        "result_summary": "На интендантском дворе сверяют courier slate по прямой боковой линии к western_road: reopened watch-road link теперь оставляет не только путь на карте, но и рабочий ритм коротких связных выходов между двором и трактом.",
        "discovered_notes": [
            "У северного двора появился настоящий watch-road courier trace: боковая линия к western_road теперь читается как рабочий relay line, а не как редкий случайный проход."
        ],
        "applied_effects": ["frontier_mesh_line:northwatch_western", "intel:watchroad_line"],
        "node_state_flags": ["northwatch_watchroad_slate_logged"],
        "node_state_summary": "На северном дворе уже сверили courier slate по reopened боковой линии к western_road.",
        "requires_any_region_link_ids": ["region-link:northwatch_frontier::western_road"],
    },
    {
        "node_id": "blackwater_run",
        "action_id": "mark_marshroad_sidepass",
        "label": "Отметить side-pass reeds",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": True,
        "result_type": "local_clue_found",
        "summary": "Отметить cautious reeds по reopened marsh-road side-pass к western_road.",
        "result_summary": "У чёрной протоки снова плетут side-pass reeds для прямой линии к western_road: болотный край отмечает не общую надежду на возврат, а конкретный осторожный проход, который теперь держится как remembered marsh-road pass.",
        "discovered_notes": [
            "На blackwater_run закрепили новый marsh-road side-pass sign: reopened линия к western_road теперь оставляет у протоки рабочую память о том, как держать осторожный прямой выход."
        ],
        "applied_effects": ["frontier_mesh_line:deep_marsh_western", "intel:marshroad_sidepass"],
        "node_state_flags": ["deep_marsh_sidepass_marked"],
        "node_state_summary": "У чёрной протоки уже отметили reeds по reopened marsh-road side-pass к western_road.",
        "requires_any_region_link_ids": ["region-link:deep_marsh::western_road"],
    },
    {
        "node_id": "ash_pass",
        "action_id": "trace_marsh_watch_sign",
        "label": "Сверить marsh-watch sign",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": True,
        "result_type": "local_clue_found",
        "summary": "Сверить sign по reopened watch-marsh line между ash_pass и deep_marsh.",
        "result_summary": "На ash_pass находят свежий marsh-watch sign по reopened линии к deep_marsh: край редута и сырая протока теперь связаны не только travel option, а понятной пограничной меткой о том, как держать мокрый боковой watch-line.",
        "discovered_notes": [
            "У ash_pass отмечен реальный watch-marsh trace: reopened линия к deep_marsh теперь оставляет собственный edge-sign, достойный дальнейшей frontier memory."
        ],
        "applied_effects": ["frontier_mesh_line:northwatch_deep_marsh", "intel:marsh_watch_edge"],
        "node_state_flags": ["northwatch_marsh_watch_sign_logged"],
        "node_state_summary": "На ash_pass уже сверили sign по reopened watch-marsh line к deep_marsh.",
        "requires_any_region_link_ids": ["region-link:deep_marsh::northwatch_frontier"],
    },
    {
        "node_id": "northwatch_quartermaster",
        "action_id": "acknowledge_watchroad_dispatch",
        "label": "Отметить relay receipt",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Отметить, что домашняя dispatch-board memory по watch-road line дошла обратно до северного двора.",
        "result_summary": "На интендантском дворе оставляют relay receipt по watch-road line: домашняя dispatch-board memory уже не висит только в лесном посёлке, а возвращается сюда как рабочая отметка о том, что courier slate принят и готов держать следующий короткий outward relay.",
        "discovered_notes": [
            "Northwatch теперь не только помнит боковую линию к western_road, но и держит полевой receipt того, что домашняя dispatch-board память дошла обратно до двора."
        ],
        "applied_effects": ["frontier_mesh_dispatch_receipt:northwatch_western", "intel:watchroad_dispatch_receipt"],
        "node_state_flags": ["northwatch_watchroad_dispatch_received"],
        "node_state_summary": "На северном дворе уже отметили relay receipt по watch-road line после домашнего dispatch-board review.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "acknowledge_sidepass_dispatch",
        "label": "Отметить side-pass receipt",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Отметить, что домашняя dispatch-board memory по marsh-road side-pass дошла обратно до чёрной протоки.",
        "result_summary": "У чёрной протоки тихо отмечают side-pass receipt: домашняя dispatch-board память по осторожной линии к western_road возвращается сюда не как абстрактная сводка, а как подтверждение, что reeds-side pass уже действительно держат в outward frontier routine.",
        "discovered_notes": [
            "Blackwater_run теперь держит не только reeds mark, но и receipt того, что домашняя dispatch-board память по marsh-road line дошла обратно в поле."
        ],
        "applied_effects": ["frontier_mesh_dispatch_receipt:deep_marsh_western", "intel:marshroad_dispatch_receipt"],
        "node_state_flags": ["deep_marsh_sidepass_dispatch_received"],
        "node_state_summary": "У чёрной протоки уже отметили side-pass receipt после домашнего dispatch-board review.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "acknowledge_marsh_watch_dispatch",
        "label": "Отметить wet-line receipt",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Отметить, что домашняя dispatch-board memory по watch-marsh line дошла обратно до ash_pass.",
        "result_summary": "На ash_pass оставляют wet-line receipt по боковой линии к deep_marsh: домашняя dispatch-board память уже не живёт только у домашнего костра, а возвращается к краю прохода как working acknowledgement того, что boundary watch line вошла в outward routine.",
        "discovered_notes": [
            "Ash_pass теперь держит не только свежий marsh-watch sign, но и receipt того, что домашняя dispatch-board память по мокрой boundary line дошла обратно в поле."
        ],
        "applied_effects": ["frontier_mesh_dispatch_receipt:northwatch_deep_marsh", "intel:marsh_watch_dispatch_receipt"],
        "node_state_flags": ["northwatch_marsh_watch_dispatch_received"],
        "node_state_summary": "На ash_pass уже отметили wet-line receipt после домашнего dispatch-board review.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "mark_watchroad_relay_turn",
        "label": "Отметить relay turn",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Отметить у двора, что watch-road line к northwatch вошла в remembered relay routine после полного closed-loop review.",
        "result_summary": "На постоялом дворе ставят короткую relay turn mark по линии к northwatch: после полного returned receipt review watch-road courier habit держится здесь уже не как единичный отклик, а как remembered turn rhythm между yard и северным двором.",
        "discovered_notes": [
            "На waystation_yard держат remembered relay turn mark по линии к northwatch: watch-road courier habit вошёл в местный routine rhythm и годится как живая frontier note, а не только как receipt из прошлой сверки."
        ],
        "applied_effects": ["frontier_routine:northwatch_western", "intel:watchroad_relay_turn"],
        "node_state_flags": ["western_road_watchroad_relay_turn_marked"],
        "node_state_summary": "На постоялом дворе уже отметили remembered relay turn по watch-road line к northwatch.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "keep_sidepass_reed_turn",
        "label": "Закрепить side-pass turn",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Закрепить у чёрной протоки cautious reeds-turn как рабочую привычку после полного closed-loop review.",
        "result_summary": "У чёрной протоки quietly закрепляют reeds-turn по side-pass к western_road: после полного returned receipt review осторожный detour через мокрый ход держится уже не как недавнее подтверждение, а как remembered safe-use habit на самой кромке воды.",
        "discovered_notes": [
            "У blackwater_run закреплён remembered reeds-turn по side-pass к western_road: осторожный marsh-road detour вошёл в local habit и теперь читается как проверенный safe-use trace."
        ],
        "applied_effects": ["frontier_routine:deep_marsh_western", "intel:sidepass_reed_turn"],
        "node_state_flags": ["deep_marsh_sidepass_reed_turn_kept"],
        "node_state_summary": "У чёрной протоки уже закрепили remembered reeds-turn по side-pass к western_road.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "keep_marsh_edge_watch_turn",
        "label": "Закрепить edge-watch turn",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Закрепить у ash_pass wet-edge watch turn как рабочий boundary rhythm после полного closed-loop review.",
        "result_summary": "На ash_pass оставляют короткую edge-watch turn mark по линии к deep_marsh: после полного returned receipt review мокрая boundary watch line держится здесь уже не как разовый sign и receipt, а как remembered marsh-edge rhythm у самого прохода.",
        "discovered_notes": [
            "На ash_pass держат remembered edge-watch turn по линии к deep_marsh: wet boundary routine вошёл в местную практику и больше не выглядит разовым полевым подтверждением."
        ],
        "applied_effects": ["frontier_routine:northwatch_deep_marsh", "intel:marsh_edge_watch_turn"],
        "node_state_flags": ["northwatch_marsh_edge_watch_turn_kept"],
        "node_state_summary": "На ash_pass уже закрепили remembered edge-watch turn по линии к deep_marsh.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "set_watchroad_post_turn",
        "label": "Удерживать watch-road post",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Закрепить у двора trusted watch-road line как held relay post после home-base routine review.",
        "result_summary": "На постоялом дворе доводят северную боковую линию до held standing-post practice: relay turn по watch-road к northwatch теперь держится не только как remembered courier habit, а как собранный road-post rhythm с понятным постовым чередованием.",
        "discovered_notes": [
            "На waystation_yard уже держат watch-road standing post по линии к northwatch: trusted courier rhythm закреплён как рабочий road-post turn, который стоит помнить дальше."
        ],
        "applied_effects": ["frontier_standing_post:northwatch_western", "intel:watchroad_standing_post"],
        "node_state_flags": ["western_road_watchroad_post_turn_set"],
        "node_state_summary": "На постоялом дворе уже закрепили held watch-road standing post по линии к northwatch.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "set_sidepass_reed_post",
        "label": "Удерживать reeds post",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Закрепить у чёрной протоки cautious side-pass как held reeds-side standing post после home-base routine review.",
        "result_summary": "У чёрной протоки side-pass к western_road доводят до held reeds-side post: осторожный detour теперь держится не только как remembered safe-use habit, а как guarded crossing watch с понятной standing mark у воды.",
        "discovered_notes": [
            "У blackwater_run уже держат reeds-side standing post по side-pass к western_road: cautious crossing habit закреплён как рабочая постовая практика у чёрной воды."
        ],
        "applied_effects": ["frontier_standing_post:deep_marsh_western", "intel:sidepass_standing_post"],
        "node_state_flags": ["deep_marsh_sidepass_reed_post_set"],
        "node_state_summary": "У чёрной протоки уже закрепили held reeds-side standing post по side-pass к western_road.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "set_marsh_edge_post_watch",
        "label": "Удерживать edge post",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Закрепить у ash_pass wet boundary line как held marsh-edge standing watch после home-base routine review.",
        "result_summary": "На ash_pass мокрую линию к deep_marsh доводят до held edge-post practice: boundary watch теперь держится не только как remembered edge rhythm, а как собранный standing watch на самой сырой кромке прохода.",
        "discovered_notes": [
            "На ash_pass уже держат marsh-edge standing watch по линии к deep_marsh: wet boundary habit закреплён как рабочий edge-post rhythm, который база и поле теперь помнят одинаково."
        ],
        "applied_effects": ["frontier_standing_post:northwatch_deep_marsh", "intel:marsh_edge_standing_post"],
        "node_state_flags": ["northwatch_marsh_edge_post_watch_set"],
        "node_state_summary": "На ash_pass уже закрепили held marsh-edge standing watch по линии к deep_marsh.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "refresh_watchroad_post_board",
        "label": "Обновить watch-road board",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Обновить relay-post turnover на watch-road line после home-base standing-post review.",
        "result_summary": "На постоялом дворе освежают courier board по линии к northwatch: held watch-road post теперь живёт не только как выставленный пост, а как maintained relief rhythm с понятной сменой turn-mark и свежей постовой доской.",
        "discovered_notes": [
            "На waystation_yard уже держат refreshed watch-road upkeep board по линии к northwatch: relay post вошёл в поддерживаемый relief cycle, который стоит помнить дальше."
        ],
        "applied_effects": ["frontier_post_upkeep:northwatch_western", "intel:watchroad_post_upkeep"],
        "node_state_flags": ["western_road_watchroad_post_board_refreshed"],
        "node_state_summary": "На постоялом дворе уже обновили upkeep board по held watch-road post к northwatch.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "refresh_sidepass_reed_watch",
        "label": "Обновить reeds watch",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Обновить reeds-side upkeep на cautious side-pass после home-base standing-post review.",
        "result_summary": "У чёрной протоки осторожный side-pass к western_road доводят до maintained reeds-watch cycle: held crossing post теперь держится не только как выставленная стоянка, а как refreshed guarded pass с понятной relief mark у воды.",
        "discovered_notes": [
            "У blackwater_run уже держат refreshed reeds-side upkeep по side-pass к western_road: guarded crossing вошёл в поддерживаемый post cycle у чёрной воды."
        ],
        "applied_effects": ["frontier_post_upkeep:deep_marsh_western", "intel:sidepass_post_upkeep"],
        "node_state_flags": ["deep_marsh_sidepass_reed_watch_refreshed"],
        "node_state_summary": "У чёрной протоки уже обновили upkeep mark по held reeds-side post к western_road.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "refresh_marsh_edge_watch_relief",
        "label": "Обновить edge relief",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Обновить marsh-edge watch relief на мокрой boundary line после home-base standing-post review.",
        "result_summary": "На ash_pass мокрую линию к deep_marsh доводят до maintained watch-relief cycle: held edge-post теперь держится не только как выставленный boundary watch, а как refreshed wet-line relief с заметной сменой стражи у кромки прохода.",
        "discovered_notes": [
            "На ash_pass уже держат refreshed marsh-edge relief по линии к deep_marsh: wet boundary watch вошёл в поддерживаемый upkeep cycle, одинаково заметный полю и базе."
        ],
        "applied_effects": ["frontier_post_upkeep:northwatch_deep_marsh", "intel:marsh_edge_post_upkeep"],
        "node_state_flags": ["northwatch_marsh_edge_watch_relief_refreshed"],
        "node_state_summary": "На ash_pass уже обновили upkeep relief по held marsh-edge watch к deep_marsh.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "close_watchroad_circuit_handoff",
        "label": "Свести relay circuit handoff",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Свести watch-road leg в circuit handoff после признания reclaimed triangle как stable local loop.",
        "result_summary": "На постоялом дворе watch-road leg к northwatch читают уже не только как maintained board, а как relay handoff в одном reclaimed circuit order. Двор держит северную линию как короткое road-side звено общего loop: courier board, yard turn и домашняя circuit memory сходятся здесь в один рабочий relay leg, который уже не выпадает из целого треугольника.",
        "discovered_notes": [
            "На waystation_yard watch-road line к northwatch уже держат как relay leg общего reclaimed circuit, а не только как отдельно обслуженный maintained post."
        ],
        "applied_effects": ["frontier_circuit_leg:northwatch_western", "intel:watchroad_circuit_handoff"],
        "node_state_flags": ["western_road_watchroad_circuit_handoff_closed"],
        "node_state_summary": "На постоялом дворе уже свели watch-road leg к northwatch в relay handoff общего reclaimed circuit.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "tie_sidepass_circuit_handoff",
        "label": "Связать side-pass circuit handoff",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Связать marsh-road leg в cautious circuit handoff после домашнего reclaimed-circuit review.",
        "result_summary": "У чёрной протоки cautious side-pass к western_road держат уже не только как maintained reeds-watch, а как reeds-side handoff в общем circuit rhythm. У воды видно, что marsh leg живёт не сам по себе: guarded pass, yard-side relay и boundary watch уже читаются как один loop, где этот side-pass держит осторожную мокрую передачу между звеньями.",
        "discovered_notes": [
            "У blackwater_run cautious side-pass к western_road уже remembered как marsh leg общего reclaimed circuit, а не только как отдельно поддержанный reeds-side post."
        ],
        "applied_effects": ["frontier_circuit_leg:deep_marsh_western", "intel:sidepass_circuit_handoff"],
        "node_state_flags": ["deep_marsh_sidepass_circuit_handoff_tied"],
        "node_state_summary": "У чёрной протоки уже связали cautious side-pass к western_road в marsh-leg handoff общего reclaimed circuit.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "mark_marsh_edge_circuit_handoff",
        "label": "Отметить edge circuit handoff",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Отметить wet boundary leg как edge-watch handoff в общем reclaimed circuit order.",
        "result_summary": "На ash_pass мокрую линию к deep_marsh отмечают уже не только как maintained relief watch, а как edge-watch handoff в одном reclaimed circuit. У кромки прохода boundary смена, болотный pass и road relay теперь читаются как части одной working loop memory, а сама мокрая граница держит понятную передачу между северным рубежом и чёрной водой.",
        "discovered_notes": [
            "На ash_pass wet boundary line к deep_marsh уже remembered как edge leg общего reclaimed circuit, а не только как отдельно обновляемый marsh-edge watch."
        ],
        "applied_effects": ["frontier_circuit_leg:northwatch_deep_marsh", "intel:marsh_edge_circuit_handoff"],
        "node_state_flags": ["northwatch_marsh_edge_circuit_handoff_marked"],
        "node_state_summary": "На ash_pass уже отметили wet boundary line к deep_marsh как edge-watch handoff общего reclaimed circuit.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "send_watchroad_loop_traffic",
        "label": "Пустить relay traffic",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Отметить, что watch-road leg уже несёт живой relay traffic внутри working reclaimed loop.",
        "result_summary": "На постоялом дворе watch-road line к northwatch читают уже не только как closed handoff, а как живой relay traffic leg в working loop. Короткий courier pass теперь идёт через двор как повторяющаяся loop circulation: северная линия уже не просто держит передачу, а реально пропускает through-traffic между остальными звеньями reclaimed triangle.",
        "discovered_notes": [
            "На waystation_yard watch-road line к northwatch уже remembered как relay traffic leg working reclaimed loop, а не только как handoff closure."
        ],
        "applied_effects": ["frontier_loop_traffic:northwatch_western", "intel:watchroad_loop_traffic"],
        "node_state_flags": ["western_road_watchroad_loop_traffic_started"],
        "node_state_summary": "На постоялом дворе уже отметили живой relay traffic по watch-road leg working reclaimed loop.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "trace_sidepass_loop_traffic",
        "label": "Проследить side-pass traffic",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Отметить cautious marsh traffic на side-pass leg working reclaimed loop.",
        "result_summary": "У чёрной протоки cautious side-pass к western_road читают уже не только как tied handoff, а как живой marsh-road traffic leg внутри working loop. Reeds-side pass теперь держит не просто передачу между звеньями, а осторожное loop movement: по мокрой линии реально идёт circulation memory, связывающая yard relay и boundary watch.",
        "discovered_notes": [
            "У blackwater_run cautious side-pass к western_road уже remembered как moving marsh traffic leg working reclaimed loop, а не только как handoff tie."
        ],
        "applied_effects": ["frontier_loop_traffic:deep_marsh_western", "intel:sidepass_loop_traffic"],
        "node_state_flags": ["deep_marsh_sidepass_loop_traffic_traced"],
        "node_state_summary": "У чёрной протоки уже проследили loop traffic по cautious side-pass к western_road.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "mark_marsh_edge_loop_traffic",
        "label": "Отметить edge traffic",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Отметить wet boundary traffic как edge-leg circulation working reclaimed loop.",
        "result_summary": "На ash_pass мокрую линию к deep_marsh читают уже не только как edge handoff, а как живой boundary traffic leg working loop. Wet boundary watch теперь держит не только closure memory, а реальное движение loop circulation: мокрая кромка пропускает edge-leg motion между северным рубежом и чёрной водой как часть одной moving frontier practice.",
        "discovered_notes": [
            "На ash_pass wet boundary line к deep_marsh уже remembered как moving edge traffic leg working reclaimed loop, а не только как handoff mark."
        ],
        "applied_effects": ["frontier_loop_traffic:northwatch_deep_marsh", "intel:marsh_edge_loop_traffic"],
        "node_state_flags": ["northwatch_marsh_edge_loop_traffic_marked"],
        "node_state_summary": "На ash_pass уже отметили живой edge traffic по мокрой линии working reclaimed loop.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "stage_watchroad_circulation_support",
        "label": "Подготовить relay aid",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Подготовить на watch-road leg первую practical aid mark, которую уже несёт active reclaimed circulation.",
        "result_summary": "На постоялом дворе watch-road line к northwatch читают уже не только как moving relay traffic, а как leg, который несёт practical relay aid. Короткий courier круг теперь приносит не просто движение, а рабочую yard-side support mark: на северную линию уже можно опереться как на маленькую, но реальную road-leg help inside reclaimed circulation.",
        "discovered_notes": [
            "На waystation_yard watch-road line к northwatch уже держат не только как traffic leg, а как relay-road support trace, который active circulation реально приносит в поле."
        ],
        "applied_effects": ["frontier_circulation_support:northwatch_western", "intel:watchroad_circulation_support"],
        "node_state_flags": ["western_road_watchroad_circulation_support_ready"],
        "node_state_summary": "На постоялом дворе уже подготовили relay-road support mark по watch-road leg active reclaimed circulation.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "set_sidepass_circulation_support",
        "label": "Подготовить side-pass aid",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Подготовить на cautious side-pass первую practical marsh aid mark active reclaimed circulation.",
        "result_summary": "У чёрной протоки cautious side-pass к western_road читают уже не только как moving marsh traffic, а как leg, который несёт practical crossing help. Reeds-side circulation теперь приносит не только движение по pass, а маленькую, но реальную marsh-leg support trace: мокрый ход уже помогает держать осторожный проход, а не просто помнить его в loop motion.",
        "discovered_notes": [
            "У blackwater_run cautious side-pass к western_road уже держат не только как traffic leg, а как marsh-pass support trace, который active circulation реально приносит в поле."
        ],
        "applied_effects": ["frontier_circulation_support:deep_marsh_western", "intel:sidepass_circulation_support"],
        "node_state_flags": ["deep_marsh_sidepass_circulation_support_set"],
        "node_state_summary": "У чёрной протоки уже подготовили cautious marsh-pass support trace по active reclaimed circulation.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "carry_marsh_edge_circulation_support",
        "label": "Подготовить edge aid",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Подготовить на wet boundary leg первую practical edge-watch aid mark active reclaimed circulation.",
        "result_summary": "На ash_pass мокрую линию к deep_marsh читают уже не только как moving edge traffic, а как leg, который несёт practical watch aid. Wet-boundary circulation теперь приносит не только движение по кромке, а маленькую, но реальную edge-leg help: boundary watch уже поддерживает проход живой carried aid mark, а не только closure or traffic memory.",
        "discovered_notes": [
            "На ash_pass wet boundary line к deep_marsh уже держат не только как traffic leg, а как marsh-edge support trace, который active circulation реально приносит в поле."
        ],
        "applied_effects": ["frontier_circulation_support:northwatch_deep_marsh", "intel:marsh_edge_circulation_support"],
        "node_state_flags": ["northwatch_marsh_edge_circulation_support_carried"],
        "node_state_summary": "На ash_pass уже подготовили wet-boundary support trace по active reclaimed circulation.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "deliver_watchroad_support_aid",
        "label": "Передать relay aid",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Передать на watch-road leg первую реально delivered relay aid mark признанного support fabric.",
        "result_summary": "На постоялом дворе watch-road line к northwatch читают уже не только как support leg active circulation, а как место, куда practical help действительно доходит и раскладывается по линии. Reclaimed support fabric приносит сюда courier aid не в виде ожидания, а как delivered road-leg help: relay-side support уже handed in на месте и реально поддерживает короткий северный ход.",
        "discovered_notes": [
            "На waystation_yard watch-road line к northwatch уже держат не только как support leg, а как delivered relay-aid trace признанного reclaimed support fabric."
        ],
        "applied_effects": ["frontier_support_delivery:northwatch_western", "intel:watchroad_support_delivery"],
        "node_state_flags": ["western_road_watchroad_support_delivered"],
        "node_state_summary": "На постоялом дворе уже передали delivered relay aid по watch-road leg признанного reclaimed support fabric.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "deliver_sidepass_support_aid",
        "label": "Передать crossing aid",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Передать на cautious side-pass первую реально delivered crossing aid mark признанного support fabric.",
        "result_summary": "У чёрной протоки cautious side-pass к western_road читают уже не только как marsh-pass support leg, а как место, куда practical crossing help действительно доходит через reclaimed support fabric. Reeds-side aid здесь уже не staged memory, а delivered marsh-leg help: помощь handed in на самой сырой связке и реально поддерживает осторожный проход.",
        "discovered_notes": [
            "У blackwater_run cautious side-pass к western_road уже держат не только как support leg, а как delivered crossing-aid trace признанного reclaimed support fabric."
        ],
        "applied_effects": ["frontier_support_delivery:deep_marsh_western", "intel:sidepass_support_delivery"],
        "node_state_flags": ["deep_marsh_sidepass_support_delivered"],
        "node_state_summary": "У чёрной протоки уже передали delivered crossing aid по cautious side-pass признанного reclaimed support fabric.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "deliver_marsh_edge_support_aid",
        "label": "Передать edge aid",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Передать на wet boundary leg первую реально delivered edge-watch aid mark признанного support fabric.",
        "result_summary": "На ash_pass мокрую линию к deep_marsh читают уже не только как edge-support leg active circulation, а как место, куда practical watch help действительно доходит через reclaimed support fabric. Wet-boundary aid здесь уже не carried trace, а delivered edge-leg help: помощь handed in на сырой кромке и реально поддерживает boundary watch в поле.",
        "discovered_notes": [
            "На ash_pass wet boundary line к deep_marsh уже держат не только как support leg, а как delivered edge-aid trace признанного reclaimed support fabric."
        ],
        "applied_effects": ["frontier_support_delivery:northwatch_deep_marsh", "intel:marsh_edge_support_delivery"],
        "node_state_flags": ["northwatch_marsh_edge_support_delivered"],
        "node_state_summary": "На ash_pass уже передали delivered edge aid по wet boundary leg признанного reclaimed support fabric.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "use_watchroad_relay_aid",
        "label": "Пустить relay aid в ход",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Пустить delivered relay aid в реальный road-leg use на watch-road line working delivered-help network.",
        "result_summary": "На постоялом дворе watch-road line к northwatch читают уже не только как место, куда помощь дошла, а как leg, где её реально пустили в ход. Delivered relay aid здесь работает уже не как handed-in trace, а как practical courier-side help in use: yard держит короткий северный relay с готовым handoff rhythm, и поддержка уже помогает вести этот road leg в живой практике.",
        "discovered_notes": [
            "На waystation_yard delivered relay aid по watch-road leg уже не просто лежит на месте, а реально работает как road-side support in use внутри reclaimed help-network."
        ],
        "applied_effects": ["frontier_support_use:northwatch_western", "intel:watchroad_support_use"],
        "node_state_flags": ["western_road_watchroad_support_in_use"],
        "node_state_summary": "На постоялом дворе уже пустили delivered relay aid в практический use по watch-road leg reclaimed help-network.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "use_sidepass_crossing_aid",
        "label": "Пустить crossing aid в ход",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Пустить delivered crossing aid в реальный marsh-leg use на cautious side-pass working delivered-help network.",
        "result_summary": "У чёрной протоки cautious side-pass к western_road читают уже не только как место, куда crossing help дошла, а как leg, где её реально применили. Delivered reeds-side aid здесь работает уже не как field handoff memory, а как cautious marsh-pass support in use: сырой проход держат по более честному crossing rhythm, а сам delivered help даёт usable pacing note, которую стоит нести дальше по этой боковой линии.",
        "discovered_notes": [
            "У blackwater_run delivered crossing aid по cautious side-pass уже не просто delivered trace, а usable reeds-side support note: по сырому leg теперь держат более честный crossing rhythm."
        ],
        "applied_effects": ["frontier_support_use:deep_marsh_western", "intel:sidepass_support_use"],
        "node_state_flags": ["deep_marsh_sidepass_support_in_use"],
        "node_state_summary": "У чёрной протоки уже пустили delivered crossing aid в практический use по cautious side-pass reclaimed help-network.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "use_marsh_edge_watch_aid",
        "label": "Пустить edge aid в ход",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Пустить delivered edge aid в реальный boundary-leg use на wet watch line working delivered-help network.",
        "result_summary": "На ash_pass мокрую линию к deep_marsh читают уже не только как место, куда edge aid дошла, а как leg, где её реально ввели в boundary watch. Delivered wet-boundary help здесь работает уже не как handed-in mark, а как practical edge-watch support in use: помощь идёт в сам watch turn у сырой кромки и делает мокрую передачу между northwatch и deep_marsh не только обслуженной, но и реально используемой в поле.",
        "discovered_notes": [
            "На ash_pass delivered edge aid по wet boundary leg уже не просто delivered trace, а реально введённая в watch turn edge-support practice reclaimed help-network."
        ],
        "applied_effects": ["frontier_support_use:northwatch_deep_marsh", "intel:marsh_edge_support_use"],
        "node_state_flags": ["northwatch_marsh_edge_support_in_use"],
        "node_state_summary": "На ash_pass уже пустили delivered edge aid в практический use по wet boundary leg reclaimed help-network.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "shelter_watchroad_wayfarers",
        "label": "Подхватить дорожных путников",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Пустить watch-road leg в первый practical roadside refuge uptake для измотанных путников reclaimed triangle.",
        "result_summary": "На постоялом дворе watch-road line к northwatch читают уже не только как road-leg help in use, а как leg, на который реально можно опереться в трудный возврат. Yard теперь подхватывает измотанных дорожных wayfarers не только aid mark, а как practical roadside fallback: delivered support уже не просто работает по линии, а даёт короткое shelter uptake для тех, кто выходит с reclaimed road leg на пределе.",
        "discovered_notes": [
            "На waystation_yard watch-road leg уже работает не только как support in use, а как practical roadside fallback: тут реально подхватывают измотанных wayfarers на reclaimed line."
        ],
        "applied_effects": ["frontier_refuge_uptake:northwatch_western", "intel:watchroad_refuge_uptake"],
        "node_state_flags": ["western_road_watchroad_wayfarers_sheltered"],
        "node_state_summary": "На постоялом дворе уже подхватывают измотанных путников как practical roadside fallback по watch-road leg reclaimed fabric.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "receive_sidepass_stragglers",
        "label": "Принять отбившихся",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Пустить cautious side-pass в первый practical refuge uptake для отбившихся frontier stragglers reclaimed triangle.",
        "result_summary": "У чёрной протоки cautious side-pass к western_road читают уже не только как marsh-support leg in use, а как место, куда реально принимают тех, кто отстал или вымотался на сыром ходе. Reclaimed line здесь работает уже не только как applied crossing help, а как cautious marsh fallback: blackwater_run принимает stragglers, собирает их в workable receiving point и оставляет honest receiving note, которую стоит помнить дальше по мокрой линии.",
        "discovered_notes": [
            "У blackwater_run cautious side-pass уже работает не только как support in use, а как marsh fallback receiving point: сюда реально стягиваются отбившиеся и вымотанные stragglers."
        ],
        "applied_effects": ["frontier_refuge_uptake:deep_marsh_western", "intel:sidepass_refuge_uptake"],
        "node_state_flags": ["deep_marsh_sidepass_stragglers_received"],
        "node_state_summary": "У чёрной протоки уже принимают отбившихся stragglers как practical marsh fallback по cautious side-pass reclaimed fabric.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "steady_marsh_edge_recoveries",
        "label": "Собрать recovery stop",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Пустить wet boundary leg в первый practical recovery uptake для уставших frontier recoveries reclaimed triangle.",
        "result_summary": "На ash_pass мокрую линию к deep_marsh читают уже не только как edge-support leg in use, а как place of recovery where people are steadied before the next push. Wet boundary watch теперь даёт не только applied help, а practical recovery stop: на сырой кромке переводят дух, приводят людей в порядок и возвращают им устойчивость так, что reclaimed edge leg начинает работать как честная recovery shelter внутри общей support fabric.",
        "discovered_notes": [
            "На ash_pass wet boundary leg уже работает не только как support in use, а как recovery stop: здесь реально steadied recoveries на самой сырой кромке reclaimed triangle."
        ],
        "applied_effects": ["frontier_refuge_uptake:northwatch_deep_marsh", "intel:marsh_edge_refuge_uptake"],
        "node_state_flags": ["northwatch_marsh_edge_recoveries_steadied"],
        "node_state_summary": "На ash_pass уже собирают recovery stop и steadied recoveries как practical wet-edge fallback по reclaimed fabric.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "send_watchroad_wayfarers_onward",
        "label": "Пустить путников дальше",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Пустить watch-road fallback в первый practical return-to-line release для sheltered wayfarers reclaimed triangle.",
        "result_summary": "На постоялом дворе watch-road line к northwatch читают уже не только как roadside fallback, а как место, откуда людей реально снова выпускают в линию. Sheltered wayfarers здесь не просто пережидают тяжёлый return, а получают practical onward release: yard превращает reclaimed road leg в honest re-entry point, через который измотанные путники снова входят в движение по frontier line.",
        "discovered_notes": [
            "На waystation_yard watch-road leg уже работает не только как fallback, а как re-entry point: sheltered wayfarers отсюда реально пускают дальше по reclaimed line."
        ],
        "applied_effects": ["frontier_return_to_line:northwatch_western", "intel:watchroad_return_to_line"],
        "node_state_flags": ["western_road_watchroad_wayfarers_sent_onward"],
        "node_state_summary": "На постоялом дворе уже пускают sheltered wayfarers дальше как practical re-entry release по watch-road leg reclaimed fabric.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "guide_sidepass_stragglers_forward",
        "label": "Повести отбившихся вперёд",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Пустить cautious side-pass fallback в первый practical return-to-line guidance для received stragglers reclaimed triangle.",
        "result_summary": "У чёрной протоки cautious side-pass к western_road читают уже не только как receiving point, а как место, где отбившихся реально выводят обратно вперёд. Received stragglers здесь получают не просто тихий приём, а cautious onward guidance: blackwater_run превращает reeds-side fallback в honest forward-routing point и оставляет guidance note, которую стоит нести дальше по мокрому leg.",
        "discovered_notes": [
            "У blackwater_run cautious side-pass уже работает не только как receiving point, а как forward-routing point: принятых stragglers отсюда реально ведут дальше по reclaimed marsh leg."
        ],
        "applied_effects": ["frontier_return_to_line:deep_marsh_western", "intel:sidepass_return_to_line"],
        "node_state_flags": ["deep_marsh_sidepass_stragglers_guided_forward"],
        "node_state_summary": "У чёрной протоки уже ведут received stragglers дальше как practical forward-routing release по cautious side-pass reclaimed fabric.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "return_marsh_edge_recoveries_to_line",
        "label": "Вернуть recoveries в линию",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Пустить wet-edge recovery stop в первый practical return-to-line handoff для steadied recoveries reclaimed triangle.",
        "result_summary": "На ash_pass мокрую линию к deep_marsh читают уже не только как recovery stop, а как место, откуда steadied recoveries реально возвращаются в boundary movement. Wet-edge recovery здесь уже не просто держит людей на месте, а даёт practical return-to-line handoff: после короткого восстановления их снова вводят в watch-side line, и reclaimed boundary leg начинает работать как honest edge-return point.",
        "discovered_notes": [
            "На ash_pass wet boundary leg уже работает не только как recovery stop, а как edge-return point: steadied recoveries отсюда реально возвращают в line movement."
        ],
        "applied_effects": ["frontier_return_to_line:northwatch_deep_marsh", "intel:marsh_edge_return_to_line"],
        "node_state_flags": ["northwatch_marsh_edge_recoveries_returned_to_line"],
        "node_state_summary": "На ash_pass уже возвращают steadied recoveries в line movement как practical wet-edge re-entry по reclaimed fabric.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "post_watchroad_reentry_referral",
        "label": "Вывесить reentry referral",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Пустить watch-road re-entry point в первый practical onward-referral cue для resumed wayfarers reclaimed triangle.",
        "result_summary": "На постоялом дворе watch-road line к northwatch читают уже не только как point of onward release, а как место, где resumed traffic получает понятный referral дальше по линии. Yard теперь не просто выпускает sheltered wayfarers обратно в движение, а даёт им honest continuation cue: watch-road leg работает как roadside reentry referral point, который указывает dependable onward continuation reclaimed triangle.",
        "discovered_notes": [
            "На waystation_yard watch-road leg уже работает не только как onward release point, а как roadside reentry referral: resumed wayfarers отсюда получают явный continuation cue по reclaimed line."
        ],
        "applied_effects": ["frontier_onward_referral:northwatch_western", "intel:watchroad_onward_referral"],
        "node_state_flags": ["western_road_watchroad_reentry_referral_posted"],
        "node_state_summary": "На постоялом дворе уже вывесили reentry referral для resumed wayfarers как dependable onward cue по watch-road leg reclaimed fabric.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "mark_sidepass_forward_referral",
        "label": "Отметить forward referral",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Пустить cautious side-pass forward point в первый practical onward-referral mark для guided stragglers reclaimed triangle.",
        "result_summary": "У чёрной протоки cautious side-pass к western_road читают уже не только как point of forward guidance, а как место, где resumed stragglers получают чёткий referral дальше по safer continuation. Blackwater_run теперь не просто ведёт их вперёд, а отмечает honest forward-referral point: reeds-side leg даёт clear continuation note, которую стоит нести дальше по мокрому ходу.",
        "discovered_notes": [
            "У blackwater_run cautious side-pass уже работает не только как forward-routing point, а как clear forward referral: guided stragglers отсюда получают safer continuation note по reclaimed marsh leg."
        ],
        "applied_effects": ["frontier_onward_referral:deep_marsh_western", "intel:sidepass_onward_referral"],
        "node_state_flags": ["deep_marsh_sidepass_forward_referral_marked"],
        "node_state_summary": "У чёрной протоки уже отметили forward referral для guided stragglers как dependable continuation cue по cautious side-pass reclaimed fabric.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "set_marsh_edge_return_referral",
        "label": "Задать return referral",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Пустить wet-edge re-entry point в первый practical onward-referral handoff для returned recoveries reclaimed triangle.",
        "result_summary": "На ash_pass мокрую линию к deep_marsh читают уже не только как edge-return point, а как место, где returned recoveries получают явный referral обратно в boundary/watch continuity. Wet-edge handoff здесь уже не просто возвращает людей в line movement, а задаёт honest return-line referral: marsh-edge leg становится recognised continuation point для следующего dependable хода по сырой границе.",
        "discovered_notes": [
            "На ash_pass wet boundary leg уже работает не только как edge-return point, а как return-line referral: returned recoveries отсюда получают явный continuation cue обратно в watch-side movement."
        ],
        "applied_effects": ["frontier_onward_referral:northwatch_deep_marsh", "intel:marsh_edge_onward_referral"],
        "node_state_flags": ["northwatch_marsh_edge_return_referral_set"],
        "node_state_summary": "На ash_pass уже задали return referral для returned recoveries как dependable continuation cue по wet boundary leg reclaimed fabric.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_frontier_stabilization",
        "label": "Сверить frontier stabilization",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Зафиксировать первую подтверждённую stabilization measure на одном краю frontier.",
        "result_summary": "Лесной посёлок впервые читает frontier не только по reports, evidence и directives, но и по реально выполненной stabilization measure: один край уже держится на подтверждённой полевой работе, а не только на обещании ответа.",
        "discovered_notes": [
            "Первое confirmed stabilization review меняет тон базы: теперь сюда возвращают не только следы и приказы, но и подтверждение того, что на краю frontier уже реально сработала field measure."
        ],
        "applied_effects": ["frontier_stabilization:started", "intel:frontier_stabilization"],
        "node_state_flags": ["frontier_stabilization_started"],
        "node_state_summary": "В лесном посёлке уже зафиксировали первую подтверждённую stabilization measure с одного края frontier.",
        "requires_min_group_node_state_flags": 1,
        "group_node_state_flag_pool": [
            "northwatch_directive_fulfilled",
            "deep_marsh_directive_fulfilled",
            "western_road_directive_fulfilled",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_frontier_stabilization",
        "label": "Сверить frontier stabilization",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Сравнить две разные подтверждённые stabilization measures по разным краям frontier.",
        "result_summary": "Когда база видит уже две подтверждённые field measures, в посёлке появляется comparative stabilization reading: разные края удерживаются по-разному, но теперь видно, где coordinated response уже действительно начал работать.",
        "discovered_notes": [
            "Две fulfilled directives дают базе не только чувство движения, а сравнительное понимание того, как frontier начинает стабилизироваться на разных внешних краях."
        ],
        "applied_effects": ["frontier_stabilization:compared", "intel:frontier_stabilization_comparison"],
        "node_state_flags": ["frontier_stabilization_compared"],
        "node_state_summary": "В лесном посёлке уже сравнили две подтверждённые stabilization measures по разным frontier edges.",
        "requires_min_group_node_state_flags": 2,
        "group_node_state_flag_pool": [
            "northwatch_directive_fulfilled",
            "deep_marsh_directive_fulfilled",
            "western_road_directive_fulfilled",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_frontier_stabilization",
        "label": "Сверить frontier stabilization",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Свести полную stabilization picture по всем трём подтверждённым field measures.",
        "result_summary": "После трёх fulfilled directives лесной посёлок получает полную frontier stabilization picture: северная watch-line, quiet crossing line и corridor handling уже читаются как подтверждённая внешняя работа, а не только как серия намерений.",
        "discovered_notes": [
            "Полный stabilization review замыкает цикл frontier: база уже видит не только pressure, evidence и directives, но и подтверждённую картину реально выполненной полевой стабилизации."
        ],
        "applied_effects": ["frontier_stabilization:compiled", "intel:frontier_stabilization_full"],
        "node_state_flags": ["frontier_stabilization_compiled"],
        "node_state_summary": "В лесном посёлке уже собрали полную frontier stabilization picture по всем трём подтверждённым field measures.",
        "requires_min_group_node_state_flags": 3,
        "group_node_state_flag_pool": [
            "northwatch_directive_fulfilled",
            "deep_marsh_directive_fulfilled",
            "western_road_directive_fulfilled",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_frontier_mesh",
        "label": "Сверить frontier mesh",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": False,
        "result_type": "local_clue_found",
        "summary": "Зафиксировать первый реально открытый lateral side-line между соседними frontier regions.",
        "result_summary": "Лесной посёлок впервые видит, что frontier уже держится не только spoke-like ходами через домашний край: один настоящий боковой переход между соседними регионами подтверждает, что рубеж начал срастаться в небольшую side-network.",
        "discovered_notes": [
            "Первый discovered lateral link меняет взгляд на frontier: теперь это не только набор возвратов к базе, а уже начинающаяся сеть боковых ходов между внешними краями."
        ],
        "applied_effects": ["frontier_mesh:started", "intel:frontier_mesh"],
        "node_state_flags": ["frontier_mesh_started"],
        "node_state_summary": "В лесном посёлке уже зафиксировали первый реально открытый lateral side-line между соседними frontier regions.",
        "requires_min_region_link_count": 1,
        "region_link_id_pool": [
            "region-link:northwatch_frontier::western_road",
            "region-link:deep_marsh::western_road",
            "region-link:deep_marsh::northwatch_frontier",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_frontier_mesh",
        "label": "Сверить frontier mesh",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": False,
        "result_type": "local_clue_found",
        "summary": "Сопоставить два discovered side-lines и увидеть spanning frontier side-network.",
        "result_summary": "Когда по краям frontier уже открыты два разных lateral links, в лесном посёлке видят не случайное исключение, а настоящую spanning side-network: соседние регионы начинают держаться между собой напрямую, а не только через домашний узел.",
        "discovered_notes": [
            "Два discovered lateral links позволяют базе читать frontier уже не как один боковой проход, а как растущую сеть прямых внешних связей между соседними краями."
        ],
        "applied_effects": ["frontier_mesh:spanning", "intel:frontier_mesh_spanning"],
        "node_state_flags": ["frontier_mesh_spanning"],
        "node_state_summary": "В лесном посёлке уже сверили два discovered side-lines и увидели spanning frontier side-network.",
        "requires_min_region_link_count": 2,
        "region_link_id_pool": [
            "region-link:northwatch_frontier::western_road",
            "region-link:deep_marsh::western_road",
            "region-link:deep_marsh::northwatch_frontier",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_frontier_mesh",
        "label": "Сверить frontier mesh",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": False,
        "result_type": "local_clue_found",
        "summary": "Собрать полную local frontier mesh picture по всем трём discovered side-lines.",
        "result_summary": "После трёх реальных lateral crossings лесной посёлок получает первую closed frontier mesh picture: northwatch, deep_marsh и western_road уже связаны между собой прямыми боковыми линиями, а starter frontier видит вокруг себя не spokes, а замкнутый внешний треугольник.",
        "discovered_notes": [
            "Полная frontier mesh picture меняет структурное понимание рубежа: три соседних внешних края теперь держатся не только на возвратах в базу, а на реально открытой local mesh topology."
        ],
        "applied_effects": ["frontier_mesh:closed", "intel:frontier_mesh_closed"],
        "node_state_flags": ["frontier_mesh_closed"],
        "node_state_summary": "В лесном посёлке уже собрали полную local frontier mesh picture по всем трём discovered lateral links.",
        "requires_min_region_link_count": 3,
        "region_link_id_pool": [
            "region-link:northwatch_frontier::western_road",
            "region-link:deep_marsh::western_road",
            "region-link:deep_marsh::northwatch_frontier",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_frontier_mesh",
        "label": "Сверить serviced mesh lines",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Зафиксировать первую боковую линию frontier, которую уже не только reopened, но и реально checked в поле.",
        "result_summary": "Лесной посёлок впервые отмечает, что одна reclaimed side-line уже не просто открыта на карте, а реально вошла в рабочую память frontier: relay slate, side-pass reeds или marsh-watch sign подтверждают, что боковой ход начали обслуживать и читать в деле.",
        "discovered_notes": [
            "Первый serviced side-line меняет тон базы: reclaimed mesh теперь живёт не только как topology, а как рабочая линия, которую в поле уже проверили и пометили."
        ],
        "applied_effects": ["frontier_mesh_service:started", "intel:serviced_frontier_mesh"],
        "node_state_flags": ["frontier_serviced_mesh_started"],
        "node_state_summary": "В лесном посёлке уже зафиксировали первую serviced side-line среди reclaimed frontier links.",
        "requires_min_group_node_state_flags": 1,
        "group_node_state_flag_pool": [
            "northwatch_watchroad_slate_logged",
            "deep_marsh_sidepass_marked",
            "northwatch_marsh_watch_sign_logged",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_frontier_mesh",
        "label": "Сверить serviced mesh lines",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Сопоставить две serviced side-lines и увидеть spanning maintained mesh fabric.",
        "result_summary": "Когда в посёлке уже помнят две разные checked side-lines, reclaimed mesh начинает читаться как spanning maintained side-network: frontier держится не только на открытых переходах, а на линиях, которые уже сверили, отметили и научились читать на практике.",
        "discovered_notes": [
            "Две serviced side-lines дают базе уже не единичную память о боковом ходе, а первые признаки maintained frontier fabric между внешними краями."
        ],
        "applied_effects": ["frontier_mesh_service:spanning", "intel:serviced_frontier_mesh_spanning"],
        "node_state_flags": ["frontier_serviced_mesh_spanning"],
        "node_state_summary": "В лесном посёлке уже сверили две serviced side-lines и увидели spanning maintained mesh fabric.",
        "requires_min_group_node_state_flags": 2,
        "group_node_state_flag_pool": [
            "northwatch_watchroad_slate_logged",
            "deep_marsh_sidepass_marked",
            "northwatch_marsh_watch_sign_logged",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_frontier_mesh",
        "label": "Сверить serviced mesh lines",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Собрать полную serviced mesh picture по всему reclaimed local triangle.",
        "result_summary": "После трёх checked side-lines лесной посёлок получает полную serviced frontier mesh picture: watch-road relay, marsh-road side-pass и watch-marsh edge уже помнятся здесь как рабочая ткань reclaimed frontier, а не просто как набор однажды открытых рёбер.",
        "discovered_notes": [
            "Полная serviced mesh picture показывает, что reclaimed triangle вокруг базы уже не только открыт, но и operationally remembered как working frontier fabric."
        ],
        "applied_effects": ["frontier_mesh_service:closed", "intel:serviced_frontier_mesh_closed"],
        "node_state_flags": ["frontier_serviced_mesh_closed"],
        "node_state_summary": "В лесном посёлке уже собрали полную serviced mesh picture по всем трём checked side-lines.",
        "requires_min_group_node_state_flags": 3,
        "group_node_state_flag_pool": [
            "northwatch_watchroad_slate_logged",
            "deep_marsh_sidepass_marked",
            "northwatch_marsh_watch_sign_logged",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_route_guidance",
        "label": "Сверить serviced route guidance",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Собрать первую compact route-guidance memory по одной реально serviced боковой линии.",
        "result_summary": "Лесной посёлок впервые может выдать не просто память о checked side-line, а рабочую route-guidance memory: по courier slate, side-pass reeds или marsh-watch sign здесь уже умеют коротко объяснить, как читать один reclaimed боковой ход в привычном frontier routine.",
        "discovered_notes": [
            "Первая serviced route-guidance memory меняет базу с наблюдателя на практическую точку чтения reclaimed side-line: checked ход теперь можно не только помнить, но и кратко вести по нему."
        ],
        "applied_effects": ["frontier_mesh_guidance:started", "intel:serviced_route_guidance"],
        "node_state_flags": ["frontier_serviced_guidance_started"],
        "node_state_summary": "В лесном посёлке уже собрали первую compact route-guidance memory по одной serviced боковой линии.",
        "requires_min_group_node_state_flags": 1,
        "group_node_state_flag_pool": [
            "northwatch_watchroad_slate_logged",
            "deep_marsh_sidepass_marked",
            "northwatch_marsh_watch_sign_logged",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_route_guidance",
        "label": "Сверить serviced route guidance",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Свести две serviced линии в spanning route-guidance memory по reclaimed mesh.",
        "result_summary": "Когда база уже держит две разные serviced боковые линии, route-guidance становится spanning: courier rhythm, cautious side-pass и wet edge reading начинают складываться в более уверенную рабочую память о том, как вести через reclaimed outer mesh.",
        "discovered_notes": [
            "Две serviced линии дают базе уже не одну local hint, а spanning route-guidance memory по растущей рабочей ткани reclaimed frontier."
        ],
        "applied_effects": ["frontier_mesh_guidance:spanning", "intel:serviced_route_guidance_spanning"],
        "node_state_flags": ["frontier_serviced_guidance_spanning"],
        "node_state_summary": "В лесном посёлке уже свели две serviced линии в spanning route-guidance memory по reclaimed mesh.",
        "requires_min_group_node_state_flags": 2,
        "group_node_state_flag_pool": [
            "northwatch_watchroad_slate_logged",
            "deep_marsh_sidepass_marked",
            "northwatch_marsh_watch_sign_logged",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_route_guidance",
        "label": "Сверить serviced route guidance",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Собрать полную route-guidance memory по всему serviced reclaimed triangle.",
        "result_summary": "После трёх serviced боковых линий лесной посёлок получает full reclaimed triangle guidance memory: watch-road cadence, marsh-road side-pass habit и watch-marsh edge reading уже можно выдавать как одну compact operational fabric, а не как разрозненные крайние приметы.",
        "discovered_notes": [
            "Полная serviced route-guidance memory делает reclaimed mesh operationally legible: база уже не только помнит checked линии, но и умеет кратко сводить их в working frontier guidance."
        ],
        "applied_effects": ["frontier_mesh_guidance:closed", "intel:serviced_route_guidance_closed"],
        "node_state_flags": ["frontier_serviced_guidance_closed"],
        "node_state_summary": "В лесном посёлке уже собрали полную route-guidance memory по всему serviced reclaimed triangle.",
        "requires_min_group_node_state_flags": 3,
        "group_node_state_flag_pool": [
            "northwatch_watchroad_slate_logged",
            "deep_marsh_sidepass_marked",
            "northwatch_marsh_watch_sign_logged",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_departure_readiness",
        "label": "Сверить departure readiness",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Собрать первую compact departure-readiness memory по одной serviced боковой линии.",
        "result_summary": "Лесной посёлок впервые может держать не только serviced memory и route guidance, а настоящую departure-readiness memory по одному checked side-line: один внешний ход уже считается не просто понятным, а достаточно собранным, чтобы на него можно было опираться при коротком выходе.",
        "discovered_notes": [
            "Первая departure-readiness memory делает reclaimed side-line не только читаемым, но и practically trusted для следующего короткого frontier departure."
        ],
        "applied_effects": ["frontier_mesh_departure:started", "intel:serviced_departure_readiness"],
        "node_state_flags": ["frontier_serviced_departure_started"],
        "node_state_summary": "В лесном посёлке уже собрали первую departure-readiness memory по одной serviced боковой линии.",
        "requires_min_group_node_state_flags": 1,
        "group_node_state_flag_pool": [
            "northwatch_watchroad_slate_logged",
            "deep_marsh_sidepass_marked",
            "northwatch_marsh_watch_sign_logged",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_departure_readiness",
        "label": "Сверить departure readiness",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Свести две serviced линии в spanning departure-readiness memory по reclaimed mesh.",
        "result_summary": "Когда база уже держит две разные serviced линии, departure-readiness становится spanning: courier cadence, cautious side-pass и boundary watch reading теперь складываются в более надёжную память о том, с каких боковых ходов можно реально собирать следующий short departure.",
        "discovered_notes": [
            "Две serviced линии дают базе уже не одну departure hint, а spanning readiness memory по нескольким рабочим боковым ходам reclaimed frontier."
        ],
        "applied_effects": ["frontier_mesh_departure:spanning", "intel:serviced_departure_readiness_spanning"],
        "node_state_flags": ["frontier_serviced_departure_spanning"],
        "node_state_summary": "В лесном посёлке уже свели две serviced линии в spanning departure-readiness memory.",
        "requires_min_group_node_state_flags": 2,
        "group_node_state_flag_pool": [
            "northwatch_watchroad_slate_logged",
            "deep_marsh_sidepass_marked",
            "northwatch_marsh_watch_sign_logged",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_departure_readiness",
        "label": "Сверить departure readiness",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Собрать полную departure-readiness memory по всему serviced reclaimed triangle.",
        "result_summary": "После трёх serviced боковых линий лесной посёлок получает полную departure-ready memory по reclaimed local triangle: watch-road cadence, marsh-road pass и watch-marsh edge уже держатся здесь как compact fabric, на которую можно опираться при следующем frontier departure, а не только вспоминать постфактум.",
        "discovered_notes": [
            "Полная departure-readiness memory делает reclaimed mesh не только operationally legible, но и compactly departure-ready в домашней памяти базы."
        ],
        "applied_effects": ["frontier_mesh_departure:closed", "intel:serviced_departure_readiness_closed"],
        "node_state_flags": ["frontier_serviced_departure_closed"],
        "node_state_summary": "В лесном посёлке уже собрали полную departure-readiness memory по всему serviced reclaimed triangle.",
        "requires_min_group_node_state_flags": 3,
        "group_node_state_flag_pool": [
            "northwatch_watchroad_slate_logged",
            "deep_marsh_sidepass_marked",
            "northwatch_marsh_watch_sign_logged",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_dispatch_board",
        "label": "Сверить dispatch board",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Выставить первую compact outbound dispatch memory по одной departure-ready serviced линии.",
        "result_summary": "Лесной посёлок впервые может держать не только departure-readiness memory, но и compact outbound dispatch-board memory: один checked и уже trusted боковой ход здесь считают достаточно собранным, чтобы по нему можно было коротко выставлять следующий outward dispatch без долгой пересборки всей frontier picture.",
        "discovered_notes": [
            "Первая outbound dispatch memory показывает, что reclaimed side-line уже не только помнят для выхода, но и держат как рабочую строку на домашней dispatch board."
        ],
        "applied_effects": ["frontier_mesh_dispatch:started", "intel:serviced_dispatch_board"],
        "node_state_flags": ["frontier_serviced_dispatch_started"],
        "node_state_summary": "В лесном посёлке уже держат первую compact outbound dispatch-board memory по одной serviced линии.",
        "requires_min_group_node_state_flags": 1,
        "group_node_state_flag_pool": [
            "frontier_serviced_departure_started",
            "frontier_serviced_departure_spanning",
            "frontier_serviced_departure_closed",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_dispatch_board",
        "label": "Сверить dispatch board",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Свести две ready линии в spanning dispatch-board memory по reclaimed mesh.",
        "result_summary": "Когда база уже держит две разные departure-ready линии, dispatch-board memory становится spanning: watch-road cadence и cautious side-pass уже читаются здесь как рабочие outbound строки, по которым можно собирать следующий dispatch не в одну сторону, а по нескольким боковым ходам reclaimed triangle.",
        "discovered_notes": [
            "Две covered линии дают базе уже не одну outbound строку, а spanning dispatch-board memory по нескольким рабочим боковым ходам reclaimed frontier."
        ],
        "applied_effects": ["frontier_mesh_dispatch:spanning", "intel:serviced_dispatch_board_spanning"],
        "node_state_flags": ["frontier_serviced_dispatch_spanning"],
        "node_state_summary": "В лесном посёлке уже свели две ready линии в spanning dispatch-board memory.",
        "requires_min_group_node_state_flags": 2,
        "group_node_state_flag_pool": [
            "frontier_serviced_departure_started",
            "frontier_serviced_departure_spanning",
            "frontier_serviced_departure_closed",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_dispatch_board",
        "label": "Сверить dispatch board",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Собрать полную outbound dispatch-board memory по всему serviced reclaimed triangle.",
        "result_summary": "После полной departure-ready памяти лесной посёлок может держать цельную dispatch-board picture по всему reclaimed local triangle: watch-road line, marsh-road pass и marsh-edge watch line уже висят здесь не как отдельные напоминания, а как compact outward-facing frontier fabric для следующего dispatch.",
        "discovered_notes": [
            "Полная dispatch-board memory делает reclaimed mesh не только departure-ready, но и posted как usable outbound frontier fabric."
        ],
        "applied_effects": ["frontier_mesh_dispatch:closed", "intel:serviced_dispatch_board_closed"],
        "node_state_flags": ["frontier_serviced_dispatch_closed"],
        "node_state_summary": "В лесном посёлке уже собрали полную outbound dispatch-board memory по всему serviced reclaimed triangle.",
        "requires_min_group_node_state_flags": 3,
        "group_node_state_flag_pool": [
            "frontier_serviced_departure_started",
            "frontier_serviced_departure_spanning",
            "frontier_serviced_departure_closed",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_returned_field_receipts",
        "label": "Сверить returned receipts",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Зафиксировать первый returned field receipt по уже posted dispatch-board памяти.",
        "result_summary": "Лесной посёлок впервые видит, что одна reopened side-line не только выставлена на домашней dispatch board, но и уже вернула honest field receipt: posted outward память дошла до края и вернулась обратно как осторожная acknowledgement mark в домашнюю сводку.",
        "discovered_notes": [
            "Первый returned courier receipt меняет тон базы: теперь один reclaimed side-line уже живёт не только как posted dispatch memory, а как реально acknowledged field loop."
        ],
        "applied_effects": ["frontier_mesh_dispatch_receipts:started", "intel:dispatch_receipt_review"],
        "node_state_flags": ["frontier_dispatch_receipt_review_started"],
        "node_state_summary": "В лесном посёлке уже зафиксировали первый returned field receipt по posted reclaimed dispatch line.",
        "requires_min_group_node_state_flags": 1,
        "group_node_state_flag_pool": [
            "northwatch_watchroad_dispatch_received",
            "deep_marsh_sidepass_dispatch_received",
            "northwatch_marsh_watch_dispatch_received",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_returned_field_receipts",
        "label": "Сверить returned receipts",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Сопоставить два distinct returned field receipts по разным reopened side-lines.",
        "result_summary": "Когда база получает уже два distinct returned receipts, dispatch-board память перестаёт быть одиночной строкой и читается как spanning returned picture: больше одной reopened side-line уже не только posted outward, но и acknowledged обратно в settlement memory как working frontier fabric.",
        "discovered_notes": [
            "Два разных returned receipts позволяют базе увидеть не один удачный отклик, а уже spanning field-acknowledged picture по нескольким reclaimed side-lines."
        ],
        "applied_effects": ["frontier_mesh_dispatch_receipts:spanning", "intel:dispatch_receipt_review_spanning"],
        "node_state_flags": ["frontier_dispatch_receipt_review_spanning"],
        "node_state_summary": "В лесном посёлке уже свели два distinct returned field receipts в spanning dispatch review picture.",
        "requires_min_group_node_state_flags": 2,
        "group_node_state_flag_pool": [
            "northwatch_watchroad_dispatch_received",
            "deep_marsh_sidepass_dispatch_received",
            "northwatch_marsh_watch_dispatch_received",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_returned_field_receipts",
        "label": "Сверить returned receipts",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Собрать полную returned dispatch receipt picture по всему reclaimed local triangle.",
        "result_summary": "После трёх distinct returned field receipts лесной посёлок замыкает первый honest base -> field -> base loop: весь reclaimed local triangle теперь читается не только как outward-posted dispatch fabric, а как полевая dispatch memory, которую реально acknowledged обратно watch-road line, cautious marsh side-pass и marsh-edge watch line.",
        "discovered_notes": [
            "Полный returned receipt review показывает базе, что весь reclaimed triangle уже держится как outward-posted и field-acknowledged frontier fabric, а не просто как отправленная память без ответа."
        ],
        "applied_effects": ["frontier_mesh_dispatch_receipts:closed", "intel:dispatch_receipt_review_closed"],
        "node_state_flags": ["frontier_dispatch_receipt_review_closed"],
        "node_state_summary": "В лесном посёлке уже собрали полную returned dispatch receipt picture по всему reclaimed local triangle.",
        "requires_min_group_node_state_flags": 3,
        "group_node_state_flag_pool": [
            "northwatch_watchroad_dispatch_received",
            "deep_marsh_sidepass_dispatch_received",
            "northwatch_marsh_watch_dispatch_received",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_trusted_frontier_routines",
        "label": "Сверить trusted routines",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Признать первую returned trusted routine mark по reopened side-line.",
        "result_summary": "Лесной посёлок впервые видит, что одна reopened side-line уже не просто reopened, serviced и acknowledged, а реально вошла в trusted frontier routine: локальный field habit вернулся домой как stable practice, а не как разовая удача.",
        "discovered_notes": [
            "Первый trusted routine review меняет тон базы: одна reclaimed side-line теперь remembered дома уже не только по receipt loop, а как реальная working frontier habit."
        ],
        "applied_effects": ["frontier_trusted_routines:started", "intel:trusted_frontier_routines"],
        "node_state_flags": ["frontier_trusted_routines_started"],
        "node_state_summary": "В лесном посёлке уже признали первую returned trusted routine mark по reclaimed side-line.",
        "requires_min_group_node_state_flags": 1,
        "group_node_state_flag_pool": [
            "western_road_watchroad_relay_turn_marked",
            "deep_marsh_sidepass_reed_turn_kept",
            "northwatch_marsh_edge_watch_turn_kept",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_trusted_frontier_routines",
        "label": "Сверить trusted routines",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Свести две distinct returned routine marks в spanning trusted routine picture.",
        "result_summary": "Когда домой возвращаются уже две разные trusted routine marks, посёлок видит spanning routine picture: больше одной reopened side-line держится не просто как acknowledged fabric, а как несколько working habits, которые реально удерживаются в поле и remembered на базе.",
        "discovered_notes": [
            "Две distinct routine marks дают базе уже не одну local habit memory, а spanning trusted routine picture по нескольким reclaimed side-lines."
        ],
        "applied_effects": ["frontier_trusted_routines:spanning", "intel:trusted_frontier_routines_spanning"],
        "node_state_flags": ["frontier_trusted_routines_spanning"],
        "node_state_summary": "В лесном посёлке уже свели две distinct returned routine marks в spanning trusted routine picture.",
        "requires_min_group_node_state_flags": 2,
        "group_node_state_flag_pool": [
            "western_road_watchroad_relay_turn_marked",
            "deep_marsh_sidepass_reed_turn_kept",
            "northwatch_marsh_edge_watch_turn_kept",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_trusted_frontier_routines",
        "label": "Сверить trusted routines",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Собрать полную trusted frontier routine picture по всему reclaimed local triangle.",
        "result_summary": "После трёх distinct returned routine marks лесной посёлок замыкает первый routine-level base -> field -> base loop: весь reclaimed local triangle теперь читается не только как dispatched, acknowledged и checked fabric, а как trusted frontier routine, который реально держится в local practice по watch-road, cautious side-pass и marsh-edge watch line.",
        "discovered_notes": [
            "Полный trusted routine review показывает базе, что весь reclaimed triangle уже remembered дома как trusted frontier routine fabric, а не только как dispatch-and-receipt memory."
        ],
        "applied_effects": ["frontier_trusted_routines:closed", "intel:trusted_frontier_routines_closed"],
        "node_state_flags": ["frontier_trusted_routines_closed"],
        "node_state_summary": "В лесном посёлке уже собрали полную trusted frontier routine picture по всему reclaimed local triangle.",
        "requires_min_group_node_state_flags": 3,
        "group_node_state_flag_pool": [
            "western_road_watchroad_relay_turn_marked",
            "deep_marsh_sidepass_reed_turn_kept",
            "northwatch_marsh_edge_watch_turn_kept",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_frontier_standing_posts",
        "label": "Сверить standing posts",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Признать первый returned standing-post signal по reopened side-line.",
        "result_summary": "Лесной посёлок впервые видит, что одна reopened side-line уже не просто routinized, а реально удерживается как standing frontier post: local post turn возвращается домой не как частная полевая привычка, а как stable holding practice.",
        "discovered_notes": [
            "Первый standing-post review меняет тон базы: одна reclaimed side-line теперь remembered дома уже не только как trusted routine, а как held frontier post."
        ],
        "applied_effects": ["frontier_standing_posts:started", "intel:frontier_standing_posts"],
        "node_state_flags": ["frontier_standing_posts_started"],
        "node_state_summary": "В лесном посёлке уже признали первый returned standing-post signal по reclaimed side-line.",
        "requires_min_group_node_state_flags": 1,
        "group_node_state_flag_pool": [
            "western_road_watchroad_post_turn_set",
            "deep_marsh_sidepass_reed_post_set",
            "northwatch_marsh_edge_post_watch_set",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_frontier_standing_posts",
        "label": "Сверить standing posts",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Свести два distinct standing-post signals в spanning standing-post picture.",
        "result_summary": "Когда домой возвращаются уже два разных standing-post signals, посёлок видит spanning standing-post picture: больше одной reopened side-line удерживается не только как local routine, а как несколько stable holdings, которые реально держат frontier fabric в поле.",
        "discovered_notes": [
            "Два distinct standing-post signals дают базе уже не один held post, а spanning standing-post picture по нескольким reclaimed side-lines."
        ],
        "applied_effects": ["frontier_standing_posts:spanning", "intel:frontier_standing_posts_spanning"],
        "node_state_flags": ["frontier_standing_posts_spanning"],
        "node_state_summary": "В лесном посёлке уже свели два distinct standing-post signals в spanning standing-post picture.",
        "requires_min_group_node_state_flags": 2,
        "group_node_state_flag_pool": [
            "western_road_watchroad_post_turn_set",
            "deep_marsh_sidepass_reed_post_set",
            "northwatch_marsh_edge_post_watch_set",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_frontier_standing_posts",
        "label": "Сверить standing posts",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Собрать полную standing-post frontier picture по всему reclaimed local triangle.",
        "result_summary": "После трёх distinct standing-post signals лесной посёлок замыкает первый standing-post-level base -> field -> base loop: весь reclaimed local triangle теперь читается не только как routinized fabric, а как stable standing-post holding по watch-road line, reeds-side pass и marsh-edge boundary watch.",
        "discovered_notes": [
            "Полный standing-post review показывает базе, что весь reclaimed triangle уже remembered дома как standing-post frontier fabric, а не только как trusted routine memory."
        ],
        "applied_effects": ["frontier_standing_posts:closed", "intel:frontier_standing_posts_closed"],
        "node_state_flags": ["frontier_standing_posts_closed"],
        "node_state_summary": "В лесном посёлке уже собрали полную standing-post frontier picture по всему reclaimed local triangle.",
        "requires_min_group_node_state_flags": 3,
        "group_node_state_flag_pool": [
            "western_road_watchroad_post_turn_set",
            "deep_marsh_sidepass_reed_post_set",
            "northwatch_marsh_edge_post_watch_set",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_maintained_frontier_posts",
        "label": "Сверить maintained posts",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Признать первый returned maintained-post signal по reopened side-line.",
        "result_summary": "Лесной посёлок впервые видит, что одна reopened side-line уже не просто удерживается как standing post, а реально поддерживается в рабочем frontier cycle: maintained relay board, reeds-watch или marsh-edge relief возвращаются домой как stable upkeep practice, а не только как выставленный пост.",
        "discovered_notes": [
            "Первый maintained-post review меняет тон базы: одна reclaimed side-line теперь remembered дома уже не только как held post, а как actively maintained frontier holding."
        ],
        "applied_effects": ["frontier_maintained_posts:started", "intel:frontier_maintained_posts"],
        "node_state_flags": ["frontier_maintained_posts_started"],
        "node_state_summary": "В лесном посёлке уже признали первый returned maintained-post signal по reclaimed side-line.",
        "requires_min_group_node_state_flags": 1,
        "group_node_state_flag_pool": [
            "western_road_watchroad_post_board_refreshed",
            "deep_marsh_sidepass_reed_watch_refreshed",
            "northwatch_marsh_edge_watch_relief_refreshed",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_maintained_frontier_posts",
        "label": "Сверить maintained posts",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Свести два distinct maintained-post signals в spanning maintained-post picture.",
        "result_summary": "Когда домой возвращаются уже два разных maintained-post signals, посёлок видит spanning maintained-post picture: больше одной reopened side-line не просто держится в поле, а активно поддерживается как working post fabric с courier-board refresh, reeds-side upkeep или wet-line relief rhythm.",
        "discovered_notes": [
            "Два distinct maintained-post signals дают базе уже не один maintained post, а spanning maintained-post picture по нескольким reclaimed side-lines."
        ],
        "applied_effects": ["frontier_maintained_posts:spanning", "intel:frontier_maintained_posts_spanning"],
        "node_state_flags": ["frontier_maintained_posts_spanning"],
        "node_state_summary": "В лесном посёлке уже свели два distinct maintained-post signals в spanning maintained-post picture.",
        "requires_min_group_node_state_flags": 2,
        "group_node_state_flag_pool": [
            "western_road_watchroad_post_board_refreshed",
            "deep_marsh_sidepass_reed_watch_refreshed",
            "northwatch_marsh_edge_watch_relief_refreshed",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_maintained_frontier_posts",
        "label": "Сверить maintained posts",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": False,
        "result_type": "local_support_applied",
        "summary": "Собрать полную maintained-post frontier picture по всему reclaimed local triangle.",
        "result_summary": "После трёх distinct maintained-post signals лесной посёлок замыкает первый maintained-post-level base -> field -> base loop: весь reclaimed local triangle теперь читается не только как held standing-post fabric, а как stable maintained frontier holding по watch-road board, reeds-side crossing upkeep и marsh-edge relief rhythm.",
        "discovered_notes": [
            "Полный maintained-post review показывает базе, что весь reclaimed triangle уже remembered дома как maintained frontier post fabric, а не только как held standing-post memory."
        ],
        "applied_effects": ["frontier_maintained_posts:closed", "intel:frontier_maintained_posts_closed"],
        "node_state_flags": ["frontier_maintained_posts_closed"],
        "node_state_summary": "В лесном посёлке уже собрали полную maintained-post frontier picture по всему reclaimed local triangle.",
        "requires_min_group_node_state_flags": 3,
        "group_node_state_flag_pool": [
            "western_road_watchroad_post_board_refreshed",
            "deep_marsh_sidepass_reed_watch_refreshed",
            "northwatch_marsh_edge_watch_relief_refreshed",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_frontier_circuit",
        "label": "Признать reclaimed circuit",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Признать reclaimed triangle как первый stable local frontier circuit.",
        "result_summary": "После полного maintained-post review лесной посёлок наконец сводит watch-road relay, reeds-side pass и marsh-edge relief не в три upkeep traces, а в один reclaimed local circuit. База помнит этот треугольник уже как stable working loop: короткий road relay, осторожный reeds crossing и boundary watch держатся вместе как один local frontier circuit, который реально живёт между домом и полем.",
        "discovered_notes": [
            "Reclaimed triangle впервые remembered в лесном посёлке уже не только как набор maintained posts, а как один stable local circuit, где relay road, reeds pass и marsh edge держатся вместе."
        ],
        "applied_effects": ["frontier_reclaimed_circuit:closed", "intel:frontier_reclaimed_circuit_closed"],
        "node_state_flags": ["frontier_reclaimed_circuit_closed"],
        "node_state_summary": "В лесном посёлке уже признали reclaimed triangle как stable local frontier circuit.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_working_loop",
        "label": "Свести reclaimed working loop",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Признать reclaimed triangle как working local loop, который реально handed through the field.",
        "result_summary": "Когда watch-road relay, reeds-side pass и marsh-edge handoff возвращаются домой уже как три согласованных field transfers, лесной посёлок видит reclaimed triangle не только как stable circuit, а как working local loop. Relay road, cautious marsh pass и wet boundary watch теперь hand through one another как один closed frontier motion: база помнит не просто maintained fabric и circuit memory, а loop, который действительно прошёл через поле и вернулся собранным.",
        "discovered_notes": [
            "Reclaimed triangle впервые remembered дома уже не только как stable circuit, а как working local loop: три leg handoff signals показывают, что motion реально closes through the field."
        ],
        "applied_effects": ["frontier_reclaimed_working_loop:closed", "intel:frontier_reclaimed_working_loop_closed"],
        "node_state_flags": ["frontier_reclaimed_working_loop_closed"],
        "node_state_summary": "В лесном посёлке уже признали reclaimed triangle как working local loop, который реально closes through the field.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_loop_circulation",
        "label": "Свести loop circulation",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Признать reclaimed triangle как active local circulation, которая реально идёт через все три legs.",
        "result_summary": "Когда watch-road relay traffic, reeds-side circulation и marsh-edge movement возвращаются домой уже как три живых field motions, лесной посёлок видит reclaimed triangle не только как working loop, а как active local circulation. Relay road, cautious reeds pass и wet boundary watch теперь circulate through one another как одна ongoing frontier fabric: база помнит уже не только closed motion, а живую circulation practice, которая реально ходит по всему reclaimed triangle.",
        "discovered_notes": [
            "Reclaimed triangle впервые remembered дома уже не только как working loop, а как active local circulation: три field traffic signals показывают, что loop реально движется по всему треугольнику."
        ],
        "applied_effects": ["frontier_reclaimed_circulation:closed", "intel:frontier_reclaimed_circulation_closed"],
        "node_state_flags": ["frontier_reclaimed_circulation_closed"],
        "node_state_summary": "В лесном посёлке уже признали reclaimed triangle как active local circulation по всем трём reclaimed legs.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_circulation_support",
        "label": "Сверить circulation support",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Признать reclaimed triangle как useful local support fabric, которая реально несёт практическую помощь по всем трём legs.",
        "result_summary": "Когда watch-road relay aid, reeds-side crossing help и marsh-edge carried watch support возвращаются домой уже как три согласованных practical traces, лесной посёлок видит reclaimed triangle не только как active local circulation, а как useful local support fabric. Relay road, cautious reeds pass и wet boundary watch теперь несут help through one another как один circulating frontier help-network: база помнит уже не только движение по треугольнику, а loop, который реально помогает frontier across the field.",
        "discovered_notes": [
            "Reclaimed triangle впервые remembered дома уже не только как active local circulation, а как practical circulating support fabric: три field support signals показывают, что loop реально несёт полезную помощь по всему треугольнику."
        ],
        "applied_effects": ["frontier_reclaimed_circulation_support:closed", "intel:frontier_reclaimed_circulation_support_closed"],
        "node_state_flags": ["frontier_reclaimed_circulation_support_closed"],
        "node_state_summary": "В лесном посёлке уже признали reclaimed triangle как useful local support fabric, которая реально несёт практическую помощь по всем трём reclaimed legs.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_support_delivery",
        "label": "Сверить delivered support",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Признать reclaimed triangle как working delivered-help fabric, которая реально доставляет practical support по всем трём legs.",
        "result_summary": "Когда watch-road relay aid, reeds-side crossing help и marsh-edge watch help возвращаются домой уже как три delivered field traces, лесной посёлок видит reclaimed triangle не только как useful local support fabric, а как working delivered-help network. Relay road, cautious reeds pass и wet boundary watch теперь не просто несут support, а реально placing help where it is needed across the loop: база помнит reclaimed triangle уже как delivered frontier help-network, который надёжно доводит practical aid through the field.",
        "discovered_notes": [
            "Reclaimed triangle впервые remembered дома уже не только как support fabric, а как delivered-help network: три field delivery signals показывают, что loop реально доводит practical aid по всему треугольнику."
        ],
        "applied_effects": ["frontier_reclaimed_support_delivery:closed", "intel:frontier_reclaimed_support_delivery_closed"],
        "node_state_flags": ["frontier_reclaimed_support_delivery_closed"],
        "node_state_summary": "В лесном посёлке уже признали reclaimed triangle как working delivered-help fabric, которая реально доводит practical support по всем трём reclaimed legs.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_support_use",
        "label": "Сверить support use",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Признать reclaimed triangle как actively used support fabric, где delivered help уже реально работает по всем трём legs.",
        "result_summary": "Когда watch-road relay aid, reeds-side crossing help и marsh-edge watch aid возвращаются домой уже не только как delivered traces, а как три field-use signals, лесной посёлок видит reclaimed triangle не только как working delivered-help network, а как actively used support fabric. Relay road, cautious reeds pass и wet boundary watch теперь не просто доводят practical help, а реально вводят её в local practice across the loop: база помнит уже не только доставленную помощь, а operational shift, где весь reclaimed triangle действительно пользуется этой поддержкой в поле.",
        "discovered_notes": [
            "Reclaimed triangle впервые remembered дома уже не только как delivered-help network, а как actively used support fabric: три field use signals показывают, что practical aid уже реально вошёл в работу по всем legs."
        ],
        "applied_effects": ["frontier_reclaimed_support_use:closed", "intel:frontier_reclaimed_support_use_closed"],
        "node_state_flags": ["frontier_reclaimed_support_use_closed"],
        "node_state_summary": "В лесном посёлке уже признали reclaimed triangle как actively used support fabric, где delivered help реально работает по всем трём reclaimed legs.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_refuge_uptake",
        "label": "Сверить refuge uptake",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Признать reclaimed triangle как working refuge-facing fabric, на которую frontier реально опирается для shelter, receiving и recovery.",
        "result_summary": "Когда watch-road shelter uptake, reeds-side receiving point и marsh-edge recovery stop возвращаются домой уже как три refuge-facing field proofs, лесной посёлок видит reclaimed triangle не только как actively used support fabric, а как practical refuge / recovery infrastructure. Relay road, cautious marsh pass и wet boundary watch теперь не просто несут помощь через loop, а реально подхватывают, принимают и восстанавливают людей в поле: база помнит весь reclaimed triangle уже как working refuge-facing frontier fabric, на которую frontier действительно опирается.",
        "discovered_notes": [
            "Reclaimed triangle впервые remembered дома уже не только как actively used support fabric, а как practical refuge / recovery infrastructure: три refuge-facing field proofs показывают, что на этот loop реально опираются для shelter, receiving и recovery."
        ],
        "applied_effects": ["frontier_reclaimed_refuge_uptake:closed", "intel:frontier_reclaimed_refuge_uptake_closed"],
        "node_state_flags": ["frontier_reclaimed_refuge_uptake_closed"],
        "node_state_summary": "В лесном посёлке уже признали reclaimed triangle как working refuge-facing fabric, на которую frontier реально опирается по всем трём reclaimed legs.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_return_to_line",
        "label": "Сверить return to line",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Признать reclaimed triangle как working return-to-line frontier fabric, которая реально возвращает людей в движение по всем трём legs.",
        "result_summary": "Когда watch-road onward release, reeds-side forward guidance и marsh-edge return handoff возвращаются домой уже как три return-to-line field proofs, лесной посёлок видит reclaimed triangle не только как refuge-facing fabric, а как working return-flow infrastructure. Relay road, cautious marsh pass и wet boundary watch теперь не просто подхватывают и восстанавливают людей, а реально вводят их обратно в движение: база помнит весь reclaimed triangle уже как practical return-to-line / onward-continuity fabric, на которую frontier действительно опирается.",
        "discovered_notes": [
            "Reclaimed triangle впервые remembered дома уже не только как refuge-facing fabric, а как practical return-to-line / onward-continuity infrastructure: три field return proofs показывают, что этот loop реально возвращает людей в движение."
        ],
        "applied_effects": ["frontier_reclaimed_return_to_line:closed", "intel:frontier_reclaimed_return_to_line_closed"],
        "node_state_flags": ["frontier_reclaimed_return_to_line_closed"],
        "node_state_summary": "В лесном посёлке уже признали reclaimed triangle как working return-to-line frontier fabric, которая реально возвращает людей в движение по всем трём reclaimed legs.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_onward_referral",
        "label": "Сверить onward referral",
        "action_kind": "support",
        "effect_type": "support",
        "one_shot": True,
        "result_type": "local_support_applied",
        "summary": "Признать reclaimed triangle как working onward-referral frontier fabric, которая реально направляет resumed traffic по надёжному продолжению линии на всех трёх legs.",
        "result_summary": "Когда watch-road reentry referral, reeds-side forward referral и marsh-edge return referral возвращаются домой уже как три onward-referral field proofs, лесной посёлок видит reclaimed triangle не только как return-to-line fabric, а как working onward-guidance / continuation infrastructure. Relay road, cautious marsh pass и wet boundary watch теперь не просто возвращают людей в движение, а реально указывают resumed traffic надёжное продолжение линии: база помнит весь reclaimed triangle уже как practical onward-referral frontier fabric, на которую frontier действительно опирается.",
        "discovered_notes": [
            "Reclaimed triangle впервые remembered дома уже не только как return-to-line fabric, а как practical onward-referral / continuation infrastructure: три field referral proofs показывают, что этот loop реально направляет resumed traffic по надёжному продолжению линии."
        ],
        "applied_effects": ["frontier_reclaimed_onward_referral:closed", "intel:frontier_reclaimed_onward_referral_closed"],
        "node_state_flags": ["frontier_reclaimed_onward_referral_closed"],
        "node_state_summary": "В лесном посёлке уже признали reclaimed triangle как working onward-referral frontier fabric, которая реально направляет resumed traffic по всем трём reclaimed legs.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "compile_frontier_report",
        "label": "Сверить frontier сводки",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": False,
        "result_type": "local_clue_found",
        "summary": "Сопоставить первый подтверждённый внешний доклад с местными лесными тревогами.",
        "result_summary": "В лесном посёлке впервые сводят дальний доклад с местной тревогой и понимают: проблема на рубеже не локальна, а уже выходит за пределы одной дороги.",
        "discovered_notes": [
            "Даже одного подтверждённого возврата с внешнего рубежа хватает, чтобы в посёлке перестали считать тревогу случайной и начали смотреть на frontier шире."
        ],
        "applied_effects": ["frontier_report:started", "intel:frontier_report"],
        "node_state_flags": ["frontier_report_started"],
        "node_state_summary": "В лесном посёлке уже собрали первый внешний frontier report и начали смотреть на соседние рубежи как на связанную проблему.",
        "requires_min_group_node_state_flags": 1,
        "group_node_state_flag_pool": [
            "northwatch_redoubt_return_logged",
            "deep_marsh_shelter_aid_received",
            "western_road_waystation_aid_received",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "compile_frontier_report",
        "label": "Сверить frontier сводки",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": False,
        "result_type": "local_clue_found",
        "summary": "Свести два подтверждённых внешних доклада и увидеть повторяющийся frontier pattern.",
        "result_summary": "Когда в посёлке сходятся уже два независимых дальних доклада, охотники видят не отдельные беды, а повторяющийся frontier pattern: короткие задержки, нервные отходы и спешные возвраты на безопасную линию.",
        "discovered_notes": [
            "Два разных рубежа уже складываются в одну картину: дальние узлы давят не одинаково по виду, но одинаково по ритму тревоги и вынужденных коротких отходов."
        ],
        "applied_effects": ["frontier_report:pattern_seen", "intel:frontier_pattern"],
        "node_state_flags": ["frontier_pattern_seen"],
        "node_state_summary": "В лесном посёлке уже видят повторяющийся frontier pattern по двум разным внешним рубежам.",
        "requires_min_group_node_state_flags": 2,
        "group_node_state_flag_pool": [
            "northwatch_redoubt_return_logged",
            "deep_marsh_shelter_aid_received",
            "western_road_waystation_aid_received",
        ],
    },
    {
        "node_id": "forest_settlement",
        "action_id": "compile_frontier_report",
        "label": "Сверить frontier сводки",
        "action_kind": "clue",
        "effect_type": "clue",
        "one_shot": False,
        "result_type": "local_clue_found",
        "summary": "Свести все три внешних доклада в полную frontier summary.",
        "result_summary": "После докладов с северного рубежа, болот и западного тракта посёлок наконец видит полную frontier summary: разные края давят по-разному, но вся линия рубежа живёт в одном режиме задержек, коротких проверок и спешных возвратов с подтверждённым следом.",
        "discovered_notes": [
            "Три разных внешних возврата складываются в одну связную картину: frontier держится не отдельными случайностями, а общей полосой нарастающего давления по всем соседним выходам."
        ],
        "applied_effects": ["frontier_report:full_pattern", "intel:frontier_summary"],
        "node_state_flags": ["frontier_full_pattern_logged"],
        "node_state_summary": "В лесном посёлке уже собрали полную frontier summary по всем трём соседним регионам.",
        "requires_min_group_node_state_flags": 3,
        "group_node_state_flag_pool": [
            "northwatch_redoubt_return_logged",
            "deep_marsh_shelter_aid_received",
            "western_road_waystation_aid_received",
        ],
    },
)


STATIC_MAP_CONTEXT_ACTION_REQUIREMENTS: tuple[dict[str, Any], ...] = (
    {
        "node_id": "craft_town",
        "action_id": "trace_watchtower_bearing",
        "requires_node_state_flag": "craft_arrival_notice_taken",
        "first_visit_only": True,
        "unlock_hint": "Сначала получить береговую наводку при первом прибытии в городок.",
    },
    {
        "node_id": "chapel_village",
        "action_id": "listen_chapel_watch",
        "return_visit_only": True,
        "unlock_hint": "Дозорные разговорчивее при повторном визите, когда группа уже знакома селу.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "compile_frontier_report",
        "requires_any_group_node_state_flags": [
            "northwatch_redoubt_return_logged",
            "deep_marsh_shelter_aid_received",
            "western_road_waystation_aid_received",
        ],
        "unlock_hint": "Сначала вернуться хотя бы с одного подтверждённого дальнего доклада с соседнего рубежа.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "arrange_frontier_evidence",
        "requires_any_group_node_state_flags": [
            "northwatch_redoubt_cache_logged",
            "deep_marsh_ferry_moorings_logged",
            "western_road_waycart_manifest_logged",
        ],
        "unlock_hint": "Сначала вернуть домой хотя бы один конкретный field proof с activated frontier branch.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "issue_frontier_directives",
        "requires_node_state_flag": "frontier_evidence_started",
        "requires_any_group_node_state_flags": [
            "northwatch_redoubt_cache_logged",
            "deep_marsh_ferry_moorings_logged",
            "western_road_waycart_manifest_logged",
        ],
        "unlock_hint": "Сначала собрать хотя бы первую returned frontier evidence picture по activated field proofs.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_frontier_stabilization",
        "requires_any_group_node_state_flags": [
            "northwatch_directive_fulfilled",
            "deep_marsh_directive_fulfilled",
            "western_road_directive_fulfilled",
        ],
        "unlock_hint": "Сначала получить хотя бы одно подтверждение, что field directive уже реально выполнен на внешнем краю.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_frontier_mesh",
        "requires_any_region_link_ids": [
            "region-link:northwatch_frontier::western_road",
            "region-link:deep_marsh::western_road",
            "region-link:deep_marsh::northwatch_frontier",
        ],
        "unlock_hint": "Сначала реально открыть хотя бы один боковой переход между соседними frontier regions, а не только знать о готовом gateway.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_frontier_mesh",
        "requires_any_group_node_state_flags": [
            "northwatch_watchroad_slate_logged",
            "deep_marsh_sidepass_marked",
            "northwatch_marsh_watch_sign_logged",
        ],
        "unlock_hint": "Сначала реально сверить хотя бы одну reclaimed side-line в поле, чтобы база увидела не только topology, а уже checked mesh memory.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_route_guidance",
        "requires_any_group_node_state_flags": [
            "northwatch_watchroad_slate_logged",
            "deep_marsh_sidepass_marked",
            "northwatch_marsh_watch_sign_logged",
        ],
        "unlock_hint": "Сначала реально проверить хотя бы одну reclaimed side-line в поле, чтобы база могла выдать не только memory, а уже compact route-guidance reading.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_departure_readiness",
        "requires_any_group_node_state_flags": [
            "northwatch_watchroad_slate_logged",
            "deep_marsh_sidepass_marked",
            "northwatch_marsh_watch_sign_logged",
        ],
        "unlock_hint": "Сначала реально проверить хотя бы одну serviced боковую линию, чтобы база могла держать не только guidance, а уже compact departure-readiness memory.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_serviced_dispatch_board",
        "requires_any_group_node_state_flags": [
            "frontier_serviced_departure_started",
            "frontier_serviced_departure_spanning",
            "frontier_serviced_departure_closed",
        ],
        "unlock_hint": "Сначала реально довести хотя бы одну serviced линию до departure-readiness memory, чтобы база могла вывесить compact outbound dispatch-board memory.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "action_id": "check_watchroad_courier_slate",
        "requires_any_region_link_ids": ["region-link:northwatch_frontier::western_road"],
        "unlock_hint": "Сначала реально пройти боковую линию между northwatch и western_road, чтобы на дворе появился настоящий courier slate по watch-road line.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "action_id": "acknowledge_watchroad_dispatch",
        "requires_node_state_flag": "northwatch_watchroad_slate_logged",
        "requires_any_group_node_state_flags": [
            "frontier_serviced_dispatch_started",
            "frontier_serviced_dispatch_spanning",
            "frontier_serviced_dispatch_closed",
        ],
        "unlock_hint": "Сначала реально сверить watch-road courier slate и дождаться домашней dispatch-board memory, чтобы на дворе появился настоящий relay receipt.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "mark_marshroad_sidepass",
        "requires_any_region_link_ids": ["region-link:deep_marsh::western_road"],
        "unlock_hint": "Сначала реально открыть marsh-road боковую линию к western_road, а уже потом отмечать cautious reeds у чёрной протоки.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "acknowledge_sidepass_dispatch",
        "requires_node_state_flag": "deep_marsh_sidepass_marked",
        "requires_any_group_node_state_flags": [
            "frontier_serviced_dispatch_started",
            "frontier_serviced_dispatch_spanning",
            "frontier_serviced_dispatch_closed",
        ],
        "unlock_hint": "Сначала реально отметить reeds-side pass и дождаться домашней dispatch-board memory, чтобы у протоки появился настоящий side-pass receipt.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "trace_marsh_watch_sign",
        "requires_any_region_link_ids": ["region-link:deep_marsh::northwatch_frontier"],
        "unlock_hint": "Сначала реально пройти боковую watch-marsh линию между northwatch и deep_marsh, чтобы на ash_pass появился свежий edge-sign.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "acknowledge_marsh_watch_dispatch",
        "requires_node_state_flag": "northwatch_marsh_watch_sign_logged",
        "requires_any_group_node_state_flags": [
            "frontier_serviced_dispatch_started",
            "frontier_serviced_dispatch_spanning",
            "frontier_serviced_dispatch_closed",
        ],
        "unlock_hint": "Сначала реально сверить marsh-watch sign и дождаться домашней dispatch-board memory, чтобы на ash_pass появился wet-line receipt.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_returned_field_receipts",
        "requires_any_group_node_state_flags": [
            "northwatch_watchroad_dispatch_received",
            "deep_marsh_sidepass_dispatch_received",
            "northwatch_marsh_watch_dispatch_received",
        ],
        "unlock_hint": "Сначала дождаться хотя бы одного real field receipt с reopened side-line, чтобы база сверяла не только posted dispatch board, а уже вернувшееся acknowledgement.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_trusted_frontier_routines",
        "requires_any_group_node_state_flags": [
            "western_road_watchroad_relay_turn_marked",
            "deep_marsh_sidepass_reed_turn_kept",
            "northwatch_marsh_edge_watch_turn_kept",
        ],
        "unlock_hint": "Сначала довести хотя бы одну reopened side-line до реального trusted routine в поле, чтобы база увидела не только receipt loop, а уже working frontier habit.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_frontier_standing_posts",
        "requires_any_group_node_state_flags": [
            "western_road_watchroad_post_turn_set",
            "deep_marsh_sidepass_reed_post_set",
            "northwatch_marsh_edge_post_watch_set",
        ],
        "unlock_hint": "Сначала довести хотя бы одну reopened side-line до реального standing post в поле, чтобы база увидела не только trusted routine, а уже stable frontier holding.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_maintained_frontier_posts",
        "requires_any_group_node_state_flags": [
            "western_road_watchroad_post_board_refreshed",
            "deep_marsh_sidepass_reed_watch_refreshed",
            "northwatch_marsh_edge_watch_relief_refreshed",
        ],
        "unlock_hint": "Сначала довести хотя бы одну reopened side-line до реального field upkeep, чтобы база увидела не только held standing post, а уже maintained frontier holding.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_frontier_circuit",
        "requires_node_state_flag": "frontier_maintained_posts_closed",
        "requires_all_group_node_state_flags": [
            "western_road_watchroad_post_board_refreshed",
            "deep_marsh_sidepass_reed_watch_refreshed",
            "northwatch_marsh_edge_watch_relief_refreshed",
        ],
        "unlock_hint": "Сначала полностью замкнуть maintained-post review по всему reclaimed triangle, чтобы база могла признать не три upkeep traces, а один stable local frontier circuit.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_working_loop",
        "requires_node_state_flag": "frontier_reclaimed_circuit_closed",
        "requires_all_group_node_state_flags": [
            "western_road_watchroad_circuit_handoff_closed",
            "deep_marsh_sidepass_circuit_handoff_tied",
            "northwatch_marsh_edge_circuit_handoff_marked",
        ],
        "unlock_hint": "Сначала замкнуть весь reclaimed circuit through the field, чтобы база могла признать не только stable circuit, а уже working local loop.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_loop_circulation",
        "requires_node_state_flag": "frontier_reclaimed_working_loop_closed",
        "requires_all_group_node_state_flags": [
            "western_road_watchroad_loop_traffic_started",
            "deep_marsh_sidepass_loop_traffic_traced",
            "northwatch_marsh_edge_loop_traffic_marked",
        ],
        "unlock_hint": "Сначала замкнуть весь reclaimed loop traffic в поле, чтобы база могла признать не только working loop, а уже active local circulation.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_circulation_support",
        "requires_node_state_flag": "frontier_reclaimed_circulation_closed",
        "requires_all_group_node_state_flags": [
            "western_road_watchroad_circulation_support_ready",
            "deep_marsh_sidepass_circulation_support_set",
            "northwatch_marsh_edge_circulation_support_carried",
        ],
        "unlock_hint": "Сначала замкнуть весь reclaimed circulation support в поле, чтобы база могла признать не только active local circulation, а уже useful local support fabric.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_support_delivery",
        "requires_node_state_flag": "frontier_reclaimed_circulation_support_closed",
        "requires_all_group_node_state_flags": [
            "western_road_watchroad_support_delivered",
            "deep_marsh_sidepass_support_delivered",
            "northwatch_marsh_edge_support_delivered",
        ],
        "unlock_hint": "Сначала замкнуть весь reclaimed support delivery в поле, чтобы база могла признать не только useful local support fabric, а уже working delivered-help network.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_support_use",
        "requires_node_state_flag": "frontier_reclaimed_support_delivery_closed",
        "requires_all_group_node_state_flags": [
            "western_road_watchroad_support_in_use",
            "deep_marsh_sidepass_support_in_use",
            "northwatch_marsh_edge_support_in_use",
        ],
        "unlock_hint": "Сначала замкнуть весь reclaimed support use в поле, чтобы база могла признать не только working delivered-help network, а уже actively used support fabric.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_refuge_uptake",
        "requires_node_state_flag": "frontier_reclaimed_support_use_closed",
        "requires_all_group_node_state_flags": [
            "western_road_watchroad_wayfarers_sheltered",
            "deep_marsh_sidepass_stragglers_received",
            "northwatch_marsh_edge_recoveries_steadied",
        ],
        "unlock_hint": "Сначала замкнуть весь reclaimed refuge uptake в поле, чтобы база могла признать не только actively used support fabric, а уже working refuge-facing frontier fabric.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_return_to_line",
        "requires_node_state_flag": "frontier_reclaimed_refuge_uptake_closed",
        "requires_all_group_node_state_flags": [
            "western_road_watchroad_wayfarers_sent_onward",
            "deep_marsh_sidepass_stragglers_guided_forward",
            "northwatch_marsh_edge_recoveries_returned_to_line",
        ],
        "unlock_hint": "Сначала замкнуть весь reclaimed return-to-line в поле, чтобы база могла признать не только refuge-facing fabric, а уже working return-to-line frontier fabric.",
    },
    {
        "node_id": "forest_settlement",
        "action_id": "review_reclaimed_onward_referral",
        "requires_node_state_flag": "frontier_reclaimed_return_to_line_closed",
        "requires_all_group_node_state_flags": [
            "western_road_watchroad_reentry_referral_posted",
            "deep_marsh_sidepass_forward_referral_marked",
            "northwatch_marsh_edge_return_referral_set",
        ],
        "unlock_hint": "Сначала замкнуть весь reclaimed onward referral в поле, чтобы база могла признать не только working return-to-line frontier fabric, а уже practical onward-referral / continuation infrastructure.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "mark_watchroad_relay_turn",
        "requires_node_state_flag": "northwatch_watchroad_dispatch_received",
        "requires_any_group_node_state_flags": ["frontier_dispatch_receipt_review_closed"],
        "unlock_hint": "Сначала замкнуть полный returned receipt review дома и дождаться watch-road receipt, чтобы на дворе появился настоящий remembered relay turn.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "keep_sidepass_reed_turn",
        "requires_node_state_flag": "deep_marsh_sidepass_dispatch_received",
        "requires_any_group_node_state_flags": ["frontier_dispatch_receipt_review_closed"],
        "unlock_hint": "Сначала замкнуть полный returned receipt review дома и дождаться side-pass receipt, чтобы у чёрной протоки осторожный detour стал lived-in reeds turn.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "keep_marsh_edge_watch_turn",
        "requires_node_state_flag": "northwatch_marsh_watch_dispatch_received",
        "requires_any_group_node_state_flags": ["frontier_dispatch_receipt_review_closed"],
        "unlock_hint": "Сначала замкнуть полный returned receipt review дома и дождаться wet-line receipt, чтобы на ash_pass boundary watch вошёл в remembered edge rhythm.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "set_watchroad_post_turn",
        "requires_node_state_flag": "western_road_watchroad_relay_turn_marked",
        "requires_any_group_node_state_flags": [
            "frontier_trusted_routines_started",
            "frontier_trusted_routines_spanning",
            "frontier_trusted_routines_closed",
        ],
        "unlock_hint": "Сначала дождаться trusted routine review дома и уже после него удерживать watch-road line как standing relay post.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "set_sidepass_reed_post",
        "requires_node_state_flag": "deep_marsh_sidepass_reed_turn_kept",
        "requires_any_group_node_state_flags": [
            "frontier_trusted_routines_started",
            "frontier_trusted_routines_spanning",
            "frontier_trusted_routines_closed",
        ],
        "unlock_hint": "Сначала дождаться trusted routine review дома и уже после него удерживать cautious side-pass как reeds-side standing post.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "set_marsh_edge_post_watch",
        "requires_node_state_flag": "northwatch_marsh_edge_watch_turn_kept",
        "requires_any_group_node_state_flags": [
            "frontier_trusted_routines_started",
            "frontier_trusted_routines_spanning",
            "frontier_trusted_routines_closed",
        ],
        "unlock_hint": "Сначала дождаться trusted routine review дома и уже после него удерживать мокрую boundary line как marsh-edge standing watch.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "refresh_watchroad_post_board",
        "requires_node_state_flag": "western_road_watchroad_post_turn_set",
        "requires_any_group_node_state_flags": [
            "frontier_standing_posts_started",
            "frontier_standing_posts_spanning",
            "frontier_standing_posts_closed",
        ],
        "unlock_hint": "Сначала дождаться standing-post review дома и уже после него обновлять watch-road post как maintained relief board.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "refresh_sidepass_reed_watch",
        "requires_node_state_flag": "deep_marsh_sidepass_reed_post_set",
        "requires_any_group_node_state_flags": [
            "frontier_standing_posts_started",
            "frontier_standing_posts_spanning",
            "frontier_standing_posts_closed",
        ],
        "unlock_hint": "Сначала дождаться standing-post review дома и уже после него обновлять cautious side-pass как maintained reeds watch.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "refresh_marsh_edge_watch_relief",
        "requires_node_state_flag": "northwatch_marsh_edge_post_watch_set",
        "requires_any_group_node_state_flags": [
            "frontier_standing_posts_started",
            "frontier_standing_posts_spanning",
            "frontier_standing_posts_closed",
        ],
        "unlock_hint": "Сначала дождаться standing-post review дома и уже после него обновлять мокрую boundary line как maintained marsh-edge relief watch.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "close_watchroad_circuit_handoff",
        "requires_node_state_flag": "western_road_watchroad_post_board_refreshed",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_circuit_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как stable circuit дома и уже после этого сводить watch-road line в relay handoff общего loop.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "tie_sidepass_circuit_handoff",
        "requires_node_state_flag": "deep_marsh_sidepass_reed_watch_refreshed",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_circuit_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как stable circuit дома и уже после этого связывать cautious side-pass в marsh-leg handoff общего loop.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "mark_marsh_edge_circuit_handoff",
        "requires_node_state_flag": "northwatch_marsh_edge_watch_relief_refreshed",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_circuit_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как stable circuit дома и уже после этого отмечать мокрую boundary line как edge handoff общего loop.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "send_watchroad_loop_traffic",
        "requires_node_state_flag": "western_road_watchroad_circuit_handoff_closed",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_working_loop_closed"],
        "unlock_hint": "Сначала реально замкнуть reclaimed working loop дома и уже после этого отмечать живой relay traffic по watch-road leg.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "trace_sidepass_loop_traffic",
        "requires_node_state_flag": "deep_marsh_sidepass_circuit_handoff_tied",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_working_loop_closed"],
        "unlock_hint": "Сначала реально замкнуть reclaimed working loop дома и уже после этого прослеживать cautious traffic по marsh side-pass leg.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "mark_marsh_edge_loop_traffic",
        "requires_node_state_flag": "northwatch_marsh_edge_circuit_handoff_marked",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_working_loop_closed"],
        "unlock_hint": "Сначала реально замкнуть reclaimed working loop дома и уже после этого отмечать живой traffic по мокрой boundary leg.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "stage_watchroad_circulation_support",
        "requires_node_state_flag": "western_road_watchroad_loop_traffic_started",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_circulation_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как active circulation дома и уже после этого готовить relay-road support на watch-road leg.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "set_sidepass_circulation_support",
        "requires_node_state_flag": "deep_marsh_sidepass_loop_traffic_traced",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_circulation_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как active circulation дома и уже после этого готовить marsh-pass support на cautious side-pass leg.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "carry_marsh_edge_circulation_support",
        "requires_node_state_flag": "northwatch_marsh_edge_loop_traffic_marked",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_circulation_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как active circulation дома и уже после этого готовить edge-watch support на мокрой boundary leg.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "deliver_watchroad_support_aid",
        "requires_node_state_flag": "western_road_watchroad_circulation_support_ready",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_circulation_support_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как useful local support fabric дома и уже после этого передавать delivered relay aid на watch-road leg.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "deliver_sidepass_support_aid",
        "requires_node_state_flag": "deep_marsh_sidepass_circulation_support_set",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_circulation_support_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как useful local support fabric дома и уже после этого передавать delivered crossing aid на cautious side-pass leg.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "deliver_marsh_edge_support_aid",
        "requires_node_state_flag": "northwatch_marsh_edge_circulation_support_carried",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_circulation_support_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как useful local support fabric дома и уже после этого передавать delivered edge aid на мокрой boundary leg.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "use_watchroad_relay_aid",
        "requires_node_state_flag": "western_road_watchroad_support_delivered",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_support_delivery_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как working delivered-help network дома и уже после этого пускать delivered relay aid в практический ход на watch-road leg.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "use_sidepass_crossing_aid",
        "requires_node_state_flag": "deep_marsh_sidepass_support_delivered",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_support_delivery_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как working delivered-help network дома и уже после этого пускать delivered crossing aid в практический ход на cautious side-pass leg.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "use_marsh_edge_watch_aid",
        "requires_node_state_flag": "northwatch_marsh_edge_support_delivered",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_support_delivery_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как working delivered-help network дома и уже после этого пускать delivered edge aid в практический ход на мокрой boundary leg.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "shelter_watchroad_wayfarers",
        "requires_node_state_flag": "western_road_watchroad_support_in_use",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_support_use_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как actively used support fabric дома и уже после этого подхватывать измотанных путников на watch-road leg.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "receive_sidepass_stragglers",
        "requires_node_state_flag": "deep_marsh_sidepass_support_in_use",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_support_use_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как actively used support fabric дома и уже после этого принимать отбившихся на cautious side-pass leg.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "steady_marsh_edge_recoveries",
        "requires_node_state_flag": "northwatch_marsh_edge_support_in_use",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_support_use_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как actively used support fabric дома и уже после этого собирать recovery stop на мокрой boundary leg.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "send_watchroad_wayfarers_onward",
        "requires_node_state_flag": "western_road_watchroad_wayfarers_sheltered",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_refuge_uptake_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как working refuge-facing frontier fabric дома и уже после этого пускать sheltered wayfarers дальше по watch-road leg.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "guide_sidepass_stragglers_forward",
        "requires_node_state_flag": "deep_marsh_sidepass_stragglers_received",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_refuge_uptake_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как working refuge-facing frontier fabric дома и уже после этого вести received stragglers дальше по cautious side-pass leg.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "return_marsh_edge_recoveries_to_line",
        "requires_node_state_flag": "northwatch_marsh_edge_recoveries_steadied",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_refuge_uptake_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как working refuge-facing frontier fabric дома и уже после этого возвращать steadied recoveries в line movement на мокрой boundary leg.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "post_watchroad_reentry_referral",
        "requires_node_state_flag": "western_road_watchroad_wayfarers_sent_onward",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_return_to_line_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как working return-to-line frontier fabric дома и уже после этого вывешивать reentry referral на watch-road leg.",
    },
    {
        "node_id": "blackwater_run",
        "action_id": "mark_sidepass_forward_referral",
        "requires_node_state_flag": "deep_marsh_sidepass_stragglers_guided_forward",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_return_to_line_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как working return-to-line frontier fabric дома и уже после этого отмечать forward referral на cautious side-pass leg.",
    },
    {
        "node_id": "ash_pass",
        "action_id": "set_marsh_edge_return_referral",
        "requires_node_state_flag": "northwatch_marsh_edge_recoveries_returned_to_line",
        "requires_any_group_node_state_flags": ["frontier_reclaimed_return_to_line_closed"],
        "unlock_hint": "Сначала реально признать reclaimed triangle как working return-to-line frontier fabric дома и уже после этого задавать return referral на мокрой boundary leg.",
    },
    {
        "node_id": "northwatch_palisade",
        "action_id": "set_relay_watch",
        "requires_any_group_node_state_flags": [
            "frontier_support_prepared",
            "frontier_support_ready",
            "frontier_support_committed",
        ],
        "unlock_hint": "Палисада разворачивает relay-дозор только когда база уже начала тянуть наружу практическую рубежную поддержку.",
    },
    {
        "node_id": "reed_shelter",
        "action_id": "braid_reed_wayline",
        "requires_any_group_node_state_flags": [
            "frontier_support_prepared",
            "frontier_support_ready",
            "frontier_support_committed",
        ],
        "unlock_hint": "Тростниковую wayline имеет смысл плести только после того, как база реально начала поддерживать дальние возвраты.",
    },
    {
        "node_id": "mile_marker_arch",
        "action_id": "reset_detour_markers",
        "requires_any_group_node_state_flags": [
            "frontier_support_prepared",
            "frontier_support_ready",
            "frontier_support_committed",
        ],
        "unlock_hint": "Detour-маркеры обновляют только когда с базы уже дошёл хотя бы первый practical support tier для дальних выходов.",
    },
    {
        "node_id": "broken_redoubt",
        "action_id": "log_redoubt_signal_cache",
        "requires_any_group_node_state_flags": [
            "northwatch_relay_watch_prepared",
            "northwatch_relay_watch_ready",
            "northwatch_relay_watch_committed",
        ],
        "requires_destination_event_id": "broken_redoubt_supply_trace",
        "requires_destination_event_result_type": "first_discovery",
        "unlock_hint": "Сначала активировать relay-дозор на палисаде и уже на месте увидеть свежий след у редута.",
    },
    {
        "node_id": "sunken_ferry",
        "action_id": "trace_ferry_moorings",
        "requires_any_group_node_state_flags": [
            "deep_marsh_wayline_prepared",
            "deep_marsh_wayline_ready",
            "deep_marsh_wayline_committed",
        ],
        "requires_destination_event_id": "sunken_ferry_trace",
        "requires_destination_event_result_type": "first_discovery",
        "unlock_hint": "Сначала протянуть wayline от приюта и уже на переправе увидеть свежий болотный след.",
    },
    {
        "node_id": "broken_waycart",
        "action_id": "sort_waycart_manifest",
        "requires_any_group_node_state_flags": [
            "western_road_detour_markers_prepared",
            "western_road_detour_markers_ready",
            "western_road_detour_markers_committed",
        ],
        "requires_destination_event_id": "broken_waycart_trace",
        "requires_destination_event_result_type": "first_discovery",
        "unlock_hint": "Сначала обновить detour-маркеры у арки и уже у повозки найти свежий дорожный след.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "action_id": "post_redoubt_orders",
        "requires_any_group_node_state_flags": ["northwatch_field_directive_issued"],
        "unlock_hint": "Сначала вернуть evidence домой и дождаться, пока база отправит назад redoubt directive на северный рубеж.",
    },
    {
        "node_id": "reed_shelter",
        "action_id": "tie_crossing_orders",
        "requires_any_group_node_state_flags": ["deep_marsh_field_directive_issued"],
        "unlock_hint": "Сначала вернуть болотный evidence домой и дождаться, пока база отправит назад crossing directive.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "chalk_corridor_orders",
        "requires_any_group_node_state_flags": ["western_road_field_directive_issued"],
        "unlock_hint": "Сначала вернуть дорожный evidence домой и дождаться, пока база отправит назад corridor directive.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "action_id": "confirm_redoubt_watch",
        "requires_node_state_flag": "northwatch_directive_posted",
        "unlock_hint": "Сначала разложить присланный redoubt order на интендантском дворе и только потом закреплять watch-line в поле.",
    },
    {
        "node_id": "reed_shelter",
        "action_id": "secure_crossing_line",
        "requires_node_state_flag": "deep_marsh_directive_posted",
        "unlock_hint": "Сначала связать присланный crossing order у приюта и только потом закреплять quiet crossing line.",
    },
    {
        "node_id": "waystation_yard",
        "action_id": "stabilize_corridor_handling",
        "requires_node_state_flag": "western_road_directive_posted",
        "unlock_hint": "Сначала отметить corridor order на дворе и только потом закреплять detour handling как рабочий порядок.",
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
    {
        "node_id": "forest_settlement",
        "state_flag": "forest_hunters_warning_taken",
        "context_note": "В лесном посёлке уже предупреждали группу о старой дороге, руинах и тревожном следе у шахтного направления.",
        "detail_note": "У сараев и у костра уже помнят, что этой группе объясняли, почему старую дорогу к руинам не стоит считать обычной прогулкой.",
        "service_note": "Основное предупреждение о старой дороге уже выдано; дальше охотники скорее уточняют детали, чем начинают рассказ заново.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "forest_return_report_logged",
        "context_note": "В посёлке уже приняли обратный рассказ о старой дороге и руинах, так что на группу смотрят как на тех, кто действительно проверил дальний ход.",
        "detail_note": "У охотничьих навесов лежит свежая пометка о возвращении группы с линии старой дороги, и разговор здесь уже идёт не на слухах, а на подтверждённом обходе.",
        "service_note": "После обратного доклада посёлок выдаёт помощь уже как знакомому составу, который сходил к руинам и вернулся с полезным наблюдением.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_report_started",
        "context_note": "В посёлке уже начали сводить внешние доклады в одну frontier-сводку, и местная тревога звучит шире, чем раньше.",
        "detail_note": "У охотничьего костра уже помечен первый внешний доклад с соседнего рубежа: теперь разговор идёт не только о лесной дороге, но и о том, как тревога расходится по всей линии frontier.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_pattern_seen",
        "context_note": "В лесном посёлке уже видят повторяющийся frontier pattern по разным соседним рубежам.",
        "detail_note": "По двум независимым внешним возвратам в посёлке уже различают общий рисунок: разные края страдают по-разному, но давят на людей одним и тем же нервным ритмом коротких вылазок и спешных отходов.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_full_pattern_logged",
        "context_note": "В посёлке уже собрали полную frontier summary по северному рубежу, болотам и западному тракту.",
        "detail_note": "У навесов уже лежит полная сводка по трём соседним регионам: starter frontier теперь читает их не как отдельные тревоги, а как одну связанную линию давления на весь внешний край.",
        "service_note": "После полной сводки лесной посёлок реагирует на группу как на тех, кто помог собрать общую frontier-картину, а не просто вернулся с одного дальнего хода.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_evidence_started",
        "context_note": "В посёлке уже начали раскладывать возвращённые field proofs как конкретную frontier evidence-сводку.",
        "detail_note": "У навесов уже лежит первый настоящий след с activated branch: разговор о frontier теперь держится не только на общих сводках, но и на принесённом evidence.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_evidence_compared",
        "context_note": "В лесном посёлке уже сравнивают разные returned proofs как части одной frontier evidence picture.",
        "detail_note": "По двум разным activated-branch traces посёлок уже видит, как отличаются не только pressure patterns, но и сами типы следа, которые возвращаются домой с рубежа.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_evidence_compiled",
        "context_note": "В посёлке уже собрали полную returned frontier evidence picture по всем трём activated branches.",
        "detail_note": "У навесов уже лежат signal cache, болотные швартовые метки и дорожный waybill scrap: starter frontier теперь держит дома не только broad reports, а конкретный evidence picture всей внешней линии.",
        "service_note": "После полной evidence picture лесной посёлок реагирует уже как база, которая не просто понимает frontier pressure, а держит у себя реальный набор возвращённых proofs.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_directive_started",
        "context_note": "В лесном посёлке уже перешли от returned evidence к первому directed frontier response.",
        "detail_note": "У навесов уже не только раскладывают proof, но и отправляют назад первое targeted order по одному внешнему краю.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_directive_expanded",
        "context_note": "В посёлке уже держат expanded frontier dispatch по двум внешним направлениям.",
        "detail_note": "Returned evidence здесь уже превращают в comparative directives: база координирует не один край, а сразу два разных frontier responses.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_directive_coordinated",
        "context_note": "В лесном посёлке уже выдали полный coordinated frontier dispatch по всем трём внешним краям.",
        "detail_note": "У навесов frontier system теперь читают и отправляют обратно как coordinated response: evidence превращается здесь в region-aware orders по всему внешнему кругу.",
        "service_note": "После полного dispatch лесной посёлок ведёт себя уже не только как база reports и evidence, а как coordinating base для всего frontier ring.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_stabilization_started",
        "context_note": "В посёлке уже видят первый подтверждённый результат полевой стабилизации на одном краю frontier.",
        "detail_note": "У навесов уже сверяют не только reports и directives: один внешний край теперь читается как реально удержанный подтверждённой field measure.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_stabilization_compared",
        "context_note": "В лесном посёлке уже сравнивают подтверждённую стабилизацию по двум разным frontier edges.",
        "detail_note": "База теперь видит не только evidence picture, но и comparative stabilization reading: разные края уже по-разному удержаны, и это читается как подтверждённый результат работы в поле.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_stabilization_compiled",
        "context_note": "В лесном посёлке уже собрали полную frontier stabilization picture по всем трём внешним краям.",
        "detail_note": "У навесов теперь лежит не только картина давления и evidence, но и подтверждённая сводка того, как северный рубеж, болота и тракт реально удержаны выполненными field measures.",
        "service_note": "После полного stabilization review лесной посёлок выглядит уже не только coordinating base, а местом, где frontier cycle замыкается подтверждённой работой из поля.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_readiness_prepared",
        "context_note": "В посёлке уже чувствуется первая readiness-готовность, выросшая из подтверждённой стабилизации frontier.",
        "detail_note": "Один подтверждённый stabilization result уже меняет домашний ритм: лесной посёлок собирается спокойнее и увереннее, чем в ранних reactive phases.",
        "service_note": "Первая readiness-поддержка уже доступна: база стала лучше подготовлена благодаря первой подтверждённой stabilization measure.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_readiness_ready",
        "context_note": "Лесной посёлок уже держит более собранную frontier readiness после comparative stabilization review.",
        "detail_note": "По двум подтверждённым stabilization measures база уже готовится не на ощупь: домашняя готовность стала заметно собраннее и осмысленнее.",
        "service_note": "Второй readiness tier уже чувствуется как более сильная и уверенная подготовка базы под внешний цикл.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_readiness_committed",
        "context_note": "В лесном посёлке уже собран полный frontier-readiness tier после полной stabilization picture.",
        "detail_note": "Полная подтверждённая stabilization picture замкнула внешний цикл в домашнюю готовность: база теперь выглядит по-настоящему собранной под следующий frontier response.",
        "service_note": "Лучший readiness tier делает посёлок не только местом сводок и координации, а реально подготовленной домашней опорой всего frontier cycle.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_mesh_started",
        "context_note": "В лесном посёлке уже понимают, что frontier перестал быть чисто spoke-like: один боковой line между внешними краями действительно открыт.",
        "detail_note": "У навесов уже отмечен первый discovered side-line между соседними frontier regions, и база смотрит на внешний край уже как на начавшую срастаться сеть, а не только на ряд возвратов домой.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_mesh_spanning",
        "context_note": "Лесной посёлок уже видит spanning side-network по двум разным lateral links между внешними краями.",
        "detail_note": "Два реальных боковых перехода меняют structural reading frontier: starter frontier уже окружён не единичным исключением, а растущей сетью прямых внешних связей.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_mesh_closed",
        "context_note": "В лесном посёлке уже собрали полную closed frontier mesh picture по northwatch, deep_marsh и western_road.",
        "detail_note": "Три discovered lateral links замкнули первый внешний треугольник вокруг базы: frontier теперь читается здесь не только по событиям и стабилизации, но и по реально возвращённой topology.",
        "service_note": "После полного mesh review посёлок ведёт себя как база, которая понимает уже не только cycle давления и ответа, а саму reclaimed frontier topology вокруг себя.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_serviced_mesh_started",
        "context_note": "В лесном посёлке уже знают, что одна reclaimed side-line не только открыта, но и реально checked в поле.",
        "detail_note": "У навесов уже лежит первая память о serviced боковой линии: один внешний ход теперь помнят не только по crossing, а по реальной полевой отметке и рабочему следу.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_serviced_mesh_spanning",
        "context_note": "Лесной посёлок уже видит spanning maintained side-network по двум checked mesh lines.",
        "detail_note": "Две serviced боковые линии дают базе новое structural reading frontier: внешние края уже связаны не только travel options, а линиями, которые действительно проверили и ввели в рабочую память.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_serviced_mesh_closed",
        "context_note": "В лесном посёлке уже собрали полную serviced mesh picture по всему reclaimed local triangle.",
        "detail_note": "Три checked side-lines замыкают не просто topology, а remembered serviced frontier fabric: база теперь видит reclaimed triangle как рабочую сеть, а не только как открытую геометрию.",
        "service_note": "После полного serviced mesh review посёлок ведёт себя как база, которая помнит не только lateral topology, но и то, что все её боковые линии уже реально проверены в поле.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_serviced_guidance_started",
        "context_note": "В лесном посёлке уже держат первую compact guidance memory по одной serviced боковой линии.",
        "detail_note": "Один checked side-line уже переведён здесь из памяти в практическую подсказку: база не только помнит этот ход, но и умеет коротко объяснить его рабочий ритм.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_serviced_guidance_spanning",
        "context_note": "Лесной посёлок уже собирает spanning route-guidance memory по двум serviced линиям reclaimed mesh.",
        "detail_note": "Две checked боковые линии дают базе уже не одну local hint, а более уверенную рабочую память о том, как читать и связывать reclaimed outer mesh в привычном frontier routine.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_serviced_guidance_closed",
        "context_note": "В лесном посёлке уже собрали полную route-guidance memory по всему serviced reclaimed triangle.",
        "detail_note": "Три serviced линии делают reclaimed mesh не только remembered, но и practically legible: база уже умеет сводить весь внешний треугольник в компактную рабочую guidance fabric.",
        "service_note": "После полного route-guidance review лесной посёлок ведёт себя как база, которая не только помнит checked side-lines, но и умеет выдавать по ним compact operational guidance.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_serviced_departure_started",
        "context_note": "В лесном посёлке уже держат первую departure-readiness memory по одной serviced боковой линии.",
        "detail_note": "Один checked side-line здесь уже считают не только понятным, но и достаточно собранным, чтобы на него можно было опираться при следующем коротком frontier departure.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_serviced_departure_spanning",
        "context_note": "Лесной посёлок уже собирает spanning departure-readiness memory по двум serviced линиям reclaimed mesh.",
        "detail_note": "Две checked боковые линии дают базе уже не одну departure hint, а более надёжную память о том, как собирать выход по нескольким рабочим боковым ходам внешнего треугольника.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_serviced_departure_closed",
        "context_note": "В лесном посёлке уже собрали полную departure-ready memory по всему serviced reclaimed triangle.",
        "detail_note": "Три serviced линии делают reclaimed mesh не только guidance-readable, но и compact departure-ready в домашней памяти: весь внешний треугольник теперь читается как рабочая ткань следующего выхода.",
        "service_note": "После полного departure-readiness review посёлок ведёт себя как база, которая не только помнит и объясняет serviced mesh, но и считает его готовой тканью следующего frontier departure.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_serviced_dispatch_started",
        "context_note": "В лесном посёлке уже держат первую compact outbound dispatch-board memory по одной ready линии.",
        "detail_note": "Один serviced и departure-ready боковой ход здесь уже держат не только в памяти выхода, но и как короткую dispatch строку для следующего outward move.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_serviced_dispatch_spanning",
        "context_note": "Лесной посёлок уже держит spanning dispatch-board memory по двум ready линиям reclaimed mesh.",
        "detail_note": "Две ready боковые линии дают базе уже не одну outbound строку, а более собранную dispatch-board память о том, как выставлять следующий ход по нескольким рабочим боковым линиям внешнего треугольника.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_serviced_dispatch_closed",
        "context_note": "В лесном посёлке уже собрали полную outbound dispatch-board memory по всему serviced reclaimed triangle.",
        "detail_note": "Три ready линии делают reclaimed mesh не только departure-readable, но и posted в домашней памяти как компактную dispatch-board fabric для следующего outward frontier хода.",
        "service_note": "После полного dispatch-board review база держит reclaimed triangle уже не только как remembered mesh, а как готовую outward-facing dispatch fabric.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_dispatch_receipt_review_started",
        "context_note": "В лесном посёлке уже видят первый returned field receipt по posted dispatch-board линии.",
        "detail_note": "Одна reopened side-line уже не только висит на домашней dispatch board, но и вернула назад осторожную field acknowledgement mark: база видит первый honest receipt loop по внешнему ходу.",
        "service_note": "После первого receipt review посёлок держит не только outbound dispatch memory, но и первую заметную обратную receipt-отметку с поля.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_dispatch_receipt_review_spanning",
        "context_note": "Лесной посёлок уже свёл два distinct returned field receipts по reopened side-lines.",
        "detail_note": "Две разные returned receipt marks показывают базе spanning field-acknowledged picture: dispatch-board память уже не одна posted строка, а несколько reopened линий, по которым acknowledgement действительно вернулся домой.",
        "service_note": "После второго receipt review база видит reclaimed mesh уже не только outward-posted, но и частично подтверждённым обратными field receipts.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_dispatch_receipt_review_closed",
        "context_note": "В лесном посёлке уже замкнули returned dispatch receipt picture по всему reclaimed local triangle.",
        "detail_note": "Watch-road receipt, cautious side-pass acknowledgement и marsh-edge watch confirmation уже лежат дома как одна returned receipt fabric: весь reclaimed triangle теперь читается как outward-posted и field-acknowledged frontier memory.",
        "service_note": "После полного receipt review посёлок держит первый closed-loop dispatch fabric по reclaimed triangle: база знает не только что память отправили, но и что её реально acknowledged обратно в поле.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_trusted_routines_started",
        "context_note": "В лесном посёлке уже признали первую returned trusted routine mark по reopened side-line.",
        "detail_note": "Одна reclaimed side-line уже remembered дома не только по dispatch receipt, но и как stable field habit: settlement видит первый честный случай, когда reopened линия реально вошла в trusted routine practice.",
        "service_note": "После первого trusted routine review база помнит одну боковую линию уже не только acknowledged, а как working frontier habit, достойный следующего return-aware planning.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_trusted_routines_spanning",
        "context_note": "Лесной посёлок уже держит spanning trusted routine picture по двум reopened side-lines.",
        "detail_note": "Две different routine marks показывают базе, что trusted frontier habit держится уже не локально в одном месте, а через несколько reclaimed side-lines: relay turn, reeds-turn или marsh-edge rhythm больше не выглядят isolated memory.",
        "service_note": "После второго trusted routine review settlement помнит reclaimed mesh уже не только как field-acknowledged fabric, а как несколько устойчивых routine habits.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_trusted_routines_closed",
        "context_note": "В лесном посёлке уже собрали полную trusted frontier routine picture по всему reclaimed local triangle.",
        "detail_note": "Watch-road relay turn, cautious reeds-side habit и marsh-edge watch rhythm уже сводятся дома в одну trusted routine fabric: весь reclaimed triangle remembered как стабильная frontier practice, а не только как dispatch memory и returned acknowledgement.",
        "service_note": "После полного trusted routine review база знает reclaimed triangle уже как trusted frontier routine recognized back at home base.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_standing_posts_started",
        "context_note": "В лесном посёлке уже признали первый returned standing-post signal по reopened side-line.",
        "detail_note": "Одна reclaimed side-line уже remembered дома не только как routine, а как held frontier post: settlement видит первый честный случай, когда боковую линию реально удерживают в поле как stable holding.",
        "service_note": "После первого standing-post review база помнит одну боковую линию уже не только как trusted routine, а как held frontier post.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_standing_posts_spanning",
        "context_note": "Лесной посёлок уже держит spanning standing-post picture по двум reopened side-lines.",
        "detail_note": "Два different standing-post signals показывают базе, что reclaimed mesh держится уже не одним isolated post, а несколькими line-side holdings: road-post turn, reeds-side post или marsh-edge watch больше не выглядят одиночными местными привычками.",
        "service_note": "После второго standing-post review settlement помнит reclaimed triangle уже как более широкую held frontier fabric.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_standing_posts_closed",
        "context_note": "В лесном посёлке уже собрали полную standing-post frontier picture по всему reclaimed local triangle.",
        "detail_note": "Watch-road post turn, cautious reeds-side post и marsh-edge standing watch уже сводятся дома в одну standing-post frontier fabric: весь reclaimed triangle remembered как stable held frontier holding, а не только как routine memory.",
        "service_note": "После полного standing-post review база знает reclaimed triangle уже как standing-post frontier fabric recognized back at home base.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_maintained_posts_started",
        "context_note": "В лесном посёлке уже признали первый returned maintained-post signal по reopened side-line.",
        "detail_note": "Одна reclaimed side-line уже remembered дома не только как held post, а как maintained frontier holding: settlement видит первый честный случай, когда боковую линию не просто держат, а реально поддерживают в рабочем relief cycle.",
        "service_note": "После первого maintained-post review база помнит одну боковую линию уже не только как standing post, а как actively maintained frontier post.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_maintained_posts_spanning",
        "context_note": "Лесной посёлок уже держит spanning maintained-post picture по двум reopened side-lines.",
        "detail_note": "Два different maintained-post signals показывают базе, что reclaimed mesh держится уже не одним isolated upkeep trace, а несколькими line-side maintenance rhythms: courier board, reeds-side watch или marsh-edge relief больше не выглядят локальной импровизацией.",
        "service_note": "После второго maintained-post review settlement помнит reclaimed triangle уже как более широкую maintained frontier holding fabric.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_maintained_posts_closed",
        "context_note": "В лесном посёлке уже собрали полную maintained-post frontier picture по всему reclaimed local triangle.",
        "detail_note": "Watch-road board refresh, cautious reeds-side upkeep и marsh-edge relief rhythm уже сводятся дома в одну maintained frontier post fabric: весь reclaimed triangle remembered как stable maintained holding, а не только как held standing-post memory.",
        "service_note": "После полного maintained-post review база знает reclaimed triangle уже как maintained frontier post fabric recognized back at home base.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_reclaimed_circuit_closed",
        "context_note": "В лесном посёлке reclaimed triangle уже remembered как stable local frontier circuit.",
        "detail_note": "Watch-road relay, reeds-side pass и marsh-edge relief уже держатся дома не как три отдельных upkeep traces, а как один reclaimed local circuit: settlement видит здесь первый coherent loop, который реально связывает maintained triangle в working frontier holding.",
        "service_note": "После reclaimed circuit review база знает maintained triangle уже не только как набор posts, а как stable local circuit с честной домашней памятью о whole loop.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_reclaimed_working_loop_closed",
        "context_note": "В лесном посёлке reclaimed triangle уже remembered как working local loop, который реально closes through the field.",
        "detail_note": "Watch-road relay handoff, reeds-side pass transfer и marsh-edge boundary handoff уже сводятся дома не просто в circuit memory, а в один working local loop: settlement видит closed frontier motion, где три reclaimed legs реально hand through one another и возвращаются как единая практика.",
        "service_note": "После working-loop review база знает reclaimed triangle уже не только как stable circuit, а как working local loop с честной closed-motion memory.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_reclaimed_circulation_closed",
        "context_note": "В лесном посёлке reclaimed triangle уже remembered как active local circulation, которая реально идёт через все три reclaimed legs.",
        "detail_note": "Watch-road relay traffic, reeds-side circulation и marsh-edge loop movement уже сводятся дома не просто в working loop, а в одну active local circulation: settlement видит ongoing frontier motion, где весь reclaimed triangle живёт как единая moving fabric.",
        "service_note": "После circulation review база знает reclaimed triangle уже не только как working loop, а как active local circulation с честной ongoing-motion memory.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_reclaimed_circulation_support_closed",
        "context_note": "В лесном посёлке reclaimed triangle уже remembered как useful local support fabric, которая реально несёт помощь через все три reclaimed legs.",
        "detail_note": "Watch-road relay aid, reeds-side crossing help и marsh-edge carried watch support уже сводятся дома не просто в active local circulation, а в одну practical support fabric: settlement видит не isolated support traces, а circulating frontier help-network, который живёт по всему reclaimed triangle.",
        "service_note": "После circulation-support review база знает reclaimed triangle уже не только как active local circulation, а как useful local support fabric с честной памятью о practical field help.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_reclaimed_support_delivery_closed",
        "context_note": "В лесном посёлке reclaimed triangle уже remembered как delivered frontier help-network, которая реально доводит practical aid через все три reclaimed legs.",
        "detail_note": "Watch-road relay aid, reeds-side crossing help и marsh-edge watch help уже сводятся дома не просто в support fabric, а в одну delivered-help network: settlement видит не isolated support traces, а practical help, которая реально placed through the reclaimed loop там, где она нужна.",
        "service_note": "После support-delivery review база знает reclaimed triangle уже не только как useful local support fabric, а как working delivered-help network с честной памятью о delivered field aid.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_reclaimed_support_use_closed",
        "context_note": "В лесном посёлке reclaimed triangle уже remembered как actively used support fabric, где delivered help реально работает через все три reclaimed legs.",
        "detail_note": "Watch-road relay aid in use, reeds-side crossing help in use и marsh-edge watch aid in use уже сводятся дома не просто в delivered-help network, а в одну operational support practice: settlement видит, что practical help уже не только доводят по loop, но и реально вводят в local field use на всём reclaimed triangle.",
        "service_note": "После support-use review база знает reclaimed triangle уже не только как delivered-help network, а как actively used support fabric с честной памятью о practical field use.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_reclaimed_refuge_uptake_closed",
        "context_note": "В лесном посёлке reclaimed triangle уже remembered как working refuge-facing frontier fabric, на которую реально опираются для shelter, receiving и recovery.",
        "detail_note": "Watch-road wayfarers sheltered, reeds-side stragglers received и marsh-edge recoveries steadied уже сводятся дома не просто в support-use memory, а в одну practical refuge / recovery infrastructure: settlement видит, что reclaimed triangle реально работает как линия подхвата и восстановления по всем трём legs.",
        "service_note": "После refuge-uptake review база знает reclaimed triangle уже не только как actively used support fabric, а как working refuge-facing frontier fabric с честной памятью о shelter / receiving / recovery use.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_reclaimed_return_to_line_closed",
        "context_note": "В лесном посёлке reclaimed triangle уже remembered как working return-to-line frontier fabric, на которую реально опираются для onward release, forward guidance и edge-return handoff.",
        "detail_note": "Watch-road wayfarers sent onward, reeds-side stragglers guided forward и marsh-edge recoveries returned to line уже сводятся дома не просто в refuge-facing memory, а в одну practical return-flow infrastructure: settlement видит, что reclaimed triangle реально возвращает людей в движение по всем трём legs.",
        "service_note": "После return-to-line review база знает reclaimed triangle уже не только как refuge-facing fabric, а как working return-to-line frontier fabric с честной памятью о onward continuity across the whole loop.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_reclaimed_onward_referral_closed",
        "context_note": "В лесном посёлке reclaimed triangle уже remembered как working onward-referral frontier fabric, на которую реально опираются для reentry referral, forward referral и edge-return continuation.",
        "detail_note": "Watch-road reentry referral posted, reeds-side forward referral marked и marsh-edge return referral set уже сводятся дома не просто в return-to-line memory, а в одну practical onward-guidance / continuation infrastructure: settlement видит, что reclaimed triangle реально направляет resumed traffic по надёжному продолжению линии на всех трёх legs.",
        "service_note": "После onward-referral review база знает reclaimed triangle уже не только как return-to-line fabric, а как working onward-referral frontier fabric с честной памятью о dependable continuation across the whole loop.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_support_prepared",
        "context_note": "В посёлке уже начали собирать осторожную рубежную поддержку под первый внешний доклад.",
        "detail_note": "У сараев уже отмечен первый практический отклик на дальние сводки: короткий охотничий набор, трезвая наводка и готовность держать быстрый возвратный ход.",
        "service_note": "После первого frontier report посёлок уже не только слушает, но и даёт осторожную практическую поддержку под следующий короткий выход.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_support_ready",
        "context_note": "Лесной посёлок уже держит более собранную рубежную поддержку по повторяющемуся frontier pattern.",
        "detail_note": "По двум сводкам подряд у охотничьих навесов уже собирают не импровизацию, а осмысленную линию поддержки: отмеченные ходы, ускоренный сбор и более точный возвратный порядок.",
        "service_note": "После второго stage посёлок реагирует уже как настоящий frontier base: помощь стала точнее и сознательнее, чем первый осторожный отклик.",
    },
    {
        "node_id": "forest_settlement",
        "state_flag": "frontier_support_committed",
        "context_note": "В посёлке уже держат полный tier frontier support под общую сводку со всех соседних рубежей.",
        "detail_note": "После полной frontier summary лесной посёлок перешёл к лучшей версии своей практической поддержки: дорожные наборы, маршрутные пометки и ритм возвратов уже собраны как единый ответ на давление по всей линии.",
        "service_note": "Теперь посёлок не просто понимает картину рубежа, а организованно действует под неё: это лучший tier local frontier support, который он может дать без превращения в отдельную систему снабжения.",
    },
    {
        "node_id": "western_road_watch",
        "state_flag": "western_road_delay_notice_taken",
        "context_note": "На западном тракте уже предупредили группу о задержанном обозе, дорожной арке и разбитом объезде.",
        "detail_note": "У входной стоянки уже помнят, что этой группе рассказывали, где последний обоз сошёл с линии тракта и почему задержку стоит читать по следам, а не по слухам.",
    },
    {
        "node_id": "northwatch_outpost",
        "state_flag": "northwatch_briefing_taken",
        "context_note": "На северном рубеже уже отметили для группы короткую вводную по линии дозора и опасному проходу.",
        "detail_note": "Смена дозора уже проговаривала этой группе, где держится безопасная линия и почему зольный проход считают нервным направлением.",
        "service_note": "Короткая вводная по рубежу уже собрана; теперь дозор скорее уточняет детали, чем начинает рассказ заново.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "state_flag": "northwatch_quartermaster_supplies",
        "context_note": "На интендантском дворе уже отмечена выданная группе рубежная выкладка.",
        "detail_note": "На ящиках у навеса видно, что для этой группы уже собирали короткий северный комплект и записывали выдачу.",
        "service_note": "Полный рубежный набор уже выдавали; дальше здесь скорее добавят мелочь, чем снова откроют склад как в первый раз.",
    },
    {
        "node_id": "northwatch_palisade",
        "state_flag": "northwatch_signal_report_taken",
        "context_note": "На палисаде уже разобрали сигнальные метки и связали тревогу рубежа с разбитым редутом над проходом.",
        "detail_note": "Метки на досках и воск на сигнальных щитах уже читались этой группой как часть последней сводки рубежа, указывающей прямо на разбитый редут.",
    },
    {
        "node_id": "northwatch_palisade",
        "state_flag": "northwatch_relay_watch_prepared",
        "context_note": "На палисаде уже держат первый relay-дозор, собранный под базовую поддержку с лесного посёлка.",
        "detail_note": "Свежие chalk marks, запасной рог и короткая перекличка с двором показывают, что северный рубеж уже начал превращать поддержку базы в реальную readiness-практику.",
    },
    {
        "node_id": "northwatch_palisade",
        "state_flag": "northwatch_relay_watch_ready",
        "context_note": "Сигнальная палисада уже работает как более надёжная relay-точка северного рубежа.",
        "detail_note": "Щиты, метки и порядок вызова у палисады теперь выглядят собраннее: ready-stage поддержка дала рубежу не только припасы, но и лучший relay rhythm.",
    },
    {
        "node_id": "northwatch_palisade",
        "state_flag": "northwatch_relay_watch_committed",
        "context_note": "Палисада уже держит лучший relay-порядок северного рубежа и читается как настоящая strongpoint-точка.",
        "detail_note": "По палисаде видно, что committed-stage support дошёл до поля: relay line работает ровно, тревога с редута больше не тонет в случайности, а сам рубеж выглядит организованнее.",
    },
    {
        "node_id": "broken_redoubt",
        "state_flag": "northwatch_redoubt_trace_found",
        "context_note": "У редута уже замечены свежие следы недавней рубежной тревоги и брошенного снабженческого ящика.",
        "detail_note": "Под разбитой кладкой нашли следы торопливой стоянки и обрывки складской метки, которые уже нельзя принять за старый мусор.",
    },
    {
        "node_id": "broken_redoubt",
        "state_flag": "northwatch_redoubt_cache_logged",
        "context_note": "У редута уже сверили сигнальный тайник, и место читается как след организованного watch-отхода, а не просто как брошенная точка тревоги.",
        "detail_note": "Под кладкой уже разобрали сигнальные бирки и watch-rotation slate: у редута сохранилась не только паника, но и след последнего собранного рубежного порядка.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "state_flag": "northwatch_redoubt_return_logged",
        "context_note": "Во дворе уже приняли обратный доклад с редута, и интендант смотрит на группу как на тех, кто сходил туда не зря.",
        "detail_note": "На столе при складе лежит свежая пометка о возвращении группы с редута, и разговор во дворе идёт уже не о догадках, а о подтверждённой тревоге.",
        "service_note": "После обратного доклада склад уже реагирует на группу как на проверенный патрульный состав, а не как на случайных путников.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "state_flag": "northwatch_support_prepared",
        "context_note": "На интендантском дворе уже чувствуют первую поддержку, пришедшую с базы на северный рубеж.",
        "detail_note": "Северный склад уже работает чуть собраннее: по двору видно, что внешняя база начала подпира́ть рубеж не только словами, но и ритмом снабжения.",
        "service_note": "С первым outward support deployment северный двор уже выдаёт помощь не как одинокую импровизацию, а как часть начавшейся линии поддержки.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "state_flag": "northwatch_support_ready",
        "context_note": "Интендантский двор уже держит более надёжный порядок снабжения по готовой support-линии с базы.",
        "detail_note": "На рубеже стало заметно больше организованности: выдача идёт быстрее, а сам двор выглядит как точка preparedness, а не как место постоянного аврала.",
        "service_note": "С ready-stage поддержкой северный двор стал заметно увереннее и полезнее для повторных коротких рубежных ходов.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "state_flag": "northwatch_support_committed",
        "context_note": "Северный рубеж уже получает лучший field-facing support tier с базы.",
        "detail_note": "По складу видно, что рубеж теперь встроен в общую линию frontier support: порядок снабжения ощущается крепче и шире, чем раньше.",
        "service_note": "Полный support deployment делает северный двор лучшей версией самого себя: это уже не только выдержка дозора, но и реальная организованная опора.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "state_flag": "northwatch_directive_posted",
        "context_note": "На интендантском дворе уже лежит redoubt directive, присланный с базы по возвращённому evidence.",
        "detail_note": "Северный двор уже работает не только по памяти дозора: на столе лежит прямой домашний order по redoubt watch и relay response.",
        "service_note": "Northwatch теперь держит не только support-line, но и явный coordinated order с базы по redoubt response.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "state_flag": "northwatch_directive_fulfilled",
        "context_note": "На северном дворе уже не просто вывесили redoubt order, а реально закрепили watch-line к редуту и боковую линию к тракту.",
        "detail_note": "Приказ с базы уже довели до поля: ash_pass к broken_redoubt держится как подтверждённый дозорный ход, а сам рубеж уже готов держать reopened side line к western_road.",
        "service_note": "Northwatch теперь ощущается не только как получатель directive, а как рубеж, который реально выполнил redoubt watch order и подготовил боковой frontier line.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "state_flag": "northwatch_watchroad_slate_logged",
        "context_note": "На интендантском дворе уже сверили courier slate по reopened watch-road line к western_road.",
        "detail_note": "На столе у склада лежит свежая slate-пометка по связным выходам на тракт: боковая линия к western_road теперь помнится здесь как рабочий relay rhythm, а не как случайное открытие.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "state_flag": "northwatch_watchroad_dispatch_received",
        "context_note": "На северном дворе уже приняли relay receipt по watch-road line после домашнего dispatch-board review.",
        "detail_note": "Courier slate здесь теперь не просто сверили: на столе у склада уже лежит короткая receipt-пометка о том, что домашняя dispatch-board память по линии к western_road дошла обратно в поле.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_watchroad_relay_turn_marked",
        "context_note": "На постоялом дворе уже держат remembered relay turn по watch-road line к northwatch.",
        "detail_note": "У yard теперь виден не только общий corridor order, но и привычный relay turn mark по северной линии: короткий courier rhythm к northwatch вошёл в рабочую память двора.",
        "service_note": "После relay turn mark двор держит северную боковую линию как lived-in courier habit, а не как единичный reopened link.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_watchroad_post_turn_set",
        "context_note": "На постоялом дворе уже держат held watch-road standing post по линии к northwatch.",
        "detail_note": "Северная боковая линия здесь теперь читается не только по relay turn, а как собранный road-post rhythm: courier turn к northwatch удерживается как рабочий постовой порядок двора.",
        "service_note": "После standing-post follow-up waystation_yard ведёт watch-road line как held relay post, а не только как remembered courier habit.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_watchroad_post_board_refreshed",
        "context_note": "На постоялом дворе уже обновляют upkeep board по held watch-road post к northwatch.",
        "detail_note": "Северная боковая линия здесь теперь читается не только как выставленный post, а как maintained relief rhythm: courier board и turn-mark по watch-road держат в свежем порядке.",
        "service_note": "После upkeep follow-up waystation_yard ведёт watch-road line как maintained post fabric, а не только как held standing post.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_watchroad_circuit_handoff_closed",
        "context_note": "На постоялом дворе уже держат watch-road line к northwatch как relay handoff общего reclaimed circuit.",
        "detail_note": "Северная боковая линия здесь читается уже не только по maintained board, а как circuit relay leg: yard держит короткую передачу между домашним loop memory и road-side handoff к northwatch.",
        "service_note": "После circuit handoff waystation_yard ведёт watch-road line уже как часть общего reclaimed loop, а не только как отдельно maintained post.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_watchroad_loop_traffic_started",
        "context_note": "На постоялом дворе уже держат watch-road line к northwatch как живой relay traffic leg working reclaimed loop.",
        "detail_note": "Северная боковая линия здесь показывает уже не только handoff closure, а loop circulation: через yard реально проходит короткий courier traffic, который связывает watch-road leg с остальными звеньями reclaimed triangle.",
        "service_note": "После loop-traffic follow-up waystation_yard ведёт watch-road line уже как moving relay leg, а не только как closed handoff.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_watchroad_circulation_support_ready",
        "context_note": "На постоялом дворе уже держат watch-road line к northwatch как relay-road support leg active reclaimed circulation.",
        "detail_note": "Северная боковая линия здесь даёт уже не только loop traffic, а practical relay help: через yard идёт небольшая, но реальная support mark, на которую можно опереться как на carried road-leg aid.",
        "service_note": "После circulation-support follow-up waystation_yard ведёт watch-road line уже как practical support leg, а не только как moving relay traffic.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_watchroad_support_delivered",
        "context_note": "На постоялом дворе уже держат watch-road line к northwatch как leg, куда practical relay aid реально delivered в поле.",
        "detail_note": "Северная боковая линия здесь даёт уже не только support trace, а delivered road-leg help: courier aid действительно handed in на дворе и поддерживает watch-road проход как usable relay-side assistance.",
        "service_note": "После support-delivery follow-up waystation_yard ведёт watch-road line уже как место delivered relay help, а не только как prepared support leg.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_watchroad_support_in_use",
        "context_note": "На постоялом дворе уже держат watch-road line к northwatch как leg, где delivered relay aid реально используется в поле.",
        "detail_note": "Северная боковая линия здесь даёт уже не только delivered help, а practical road-leg use: yard ведёт короткий courier handoff по более собранному relay rhythm, и помощь здесь читается как реально применённая, а не просто доведённая.",
        "service_note": "После support-use follow-up waystation_yard ведёт watch-road line уже как место, где delivered relay help реально работает в практике.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_watchroad_wayfarers_sheltered",
        "context_note": "На постоялом дворе уже держат watch-road line к northwatch как roadside fallback, где реально подхватывают измотанных путников.",
        "detail_note": "Северная боковая линия здесь даёт уже не только applied road-leg help, а practical shelter uptake: yard принимает вымотанных wayfarers с reclaimed line и делает watch-road leg честной точкой короткого fallback, а не только местом relay use.",
        "service_note": "После refuge-uptake follow-up waystation_yard ведёт watch-road line уже как place of shelter fallback, а не только как support in use.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_watchroad_wayfarers_sent_onward",
        "context_note": "На постоялом дворе уже держат watch-road line к northwatch как re-entry point, откуда sheltered wayfarers реально пускают дальше.",
        "detail_note": "Северная боковая линия здесь даёт уже не только fallback, а practical return-to-line release: yard выпускает road-weary wayfarers обратно в движение и делает watch-road leg честной точкой onward re-entry, а не только местом shelter.",
        "service_note": "После return-to-line follow-up waystation_yard ведёт watch-road line уже как onward release point, а не только как roadside fallback.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_watchroad_reentry_referral_posted",
        "context_note": "На постоялом дворе уже держат watch-road line к northwatch как reentry referral point, где resumed wayfarers получают явный continuation cue.",
        "detail_note": "Северная боковая линия здесь даёт уже не только onward release, а practical onward-referral mark: yard указывает dependable continuation дальше по watch-road leg и делает этот roadside return point честной точкой referral, а не только повторного старта.",
        "service_note": "После onward-referral follow-up waystation_yard ведёт watch-road line уже как reentry referral point, а не только как onward release point.",
    },
    {
        "node_id": "ash_pass",
        "state_flag": "northwatch_directive_fulfilled",
        "context_note": "На ash_pass уже держат не только ход к редуту, но и reopened боковую линию к болотной протоке.",
        "detail_note": "После выполненной рубежной директивы ash_pass читается не как тупиковый тревожный ход, а как рабочая watch-side линия к deep_marsh.",
    },
    {
        "node_id": "ash_pass",
        "state_flag": "northwatch_marsh_watch_sign_logged",
        "context_note": "На ash_pass уже сверили свежий sign по reopened watch-marsh line к deep_marsh.",
        "detail_note": "У края прохода уже знают, как читать болотную боковую линию не только по памяти дозора, но и по свежему edge-sign, который остался после прямого marsh crossing.",
    },
    {
        "node_id": "ash_pass",
        "state_flag": "northwatch_marsh_watch_dispatch_received",
        "context_note": "На ash_pass уже приняли wet-line receipt по линии к deep_marsh после домашнего dispatch-board review.",
        "detail_note": "У края прохода теперь держат не только свежий sign, но и короткую receipt-пометку о том, что домашняя dispatch-board память по мокрой boundary line дошла обратно в поле.",
    },
    {
        "node_id": "ash_pass",
        "state_flag": "northwatch_marsh_edge_watch_turn_kept",
        "context_note": "На ash_pass уже держат remembered edge-watch turn по мокрой линии к deep_marsh.",
        "detail_note": "Край прохода теперь показывает не только sign и receipt, но и lived-in boundary rhythm: мокрая watch-line к deep_marsh вошла в рабочую местную привычку.",
        "service_note": "После edge-watch turn ash_pass ведёт marsh boundary line как remembered local watch habit, а не как разовую полевую отметку.",
    },
    {
        "node_id": "ash_pass",
        "state_flag": "northwatch_marsh_edge_post_watch_set",
        "context_note": "На ash_pass уже держат held marsh-edge standing watch по мокрой линии к deep_marsh.",
        "detail_note": "Край прохода теперь показывает не только remembered rhythm, а собранный edge-post порядок: wet boundary line к deep_marsh удерживается как реальная standing watch practice.",
        "service_note": "После standing-post follow-up ash_pass ведёт мокрую boundary line как held edge-post watch, а не только как remembered routine.",
    },
    {
        "node_id": "ash_pass",
        "state_flag": "northwatch_marsh_edge_watch_relief_refreshed",
        "context_note": "На ash_pass уже обновляют marsh-edge relief по held boundary watch к deep_marsh.",
        "detail_note": "Край прохода теперь показывает не только held edge-post, а maintained wet-line relief cycle: boundary watch у сырой кромки обновляют как рабочую практику смены.",
        "service_note": "После upkeep follow-up ash_pass ведёт мокрую boundary line как maintained marsh-edge watch, а не только как held standing post.",
    },
    {
        "node_id": "ash_pass",
        "state_flag": "northwatch_marsh_edge_circuit_handoff_marked",
        "context_note": "На ash_pass уже держат мокрую линию к deep_marsh как edge handoff общего reclaimed circuit.",
        "detail_note": "Край прохода теперь показывает не только maintained relief, а wet boundary leg общего loop: edge-watch handoff связывает marsh edge с остальными circuit lines, а не держится изолированной сменой.",
        "service_note": "После circuit handoff ash_pass ведёт мокрую boundary line как часть общего reclaimed loop, а не только как maintained edge watch.",
    },
    {
        "node_id": "ash_pass",
        "state_flag": "northwatch_marsh_edge_loop_traffic_marked",
        "context_note": "На ash_pass уже держат мокрую линию к deep_marsh как живой edge-traffic leg working reclaimed loop.",
        "detail_note": "Край прохода теперь показывает не только edge handoff, а loop movement по мокрой boundary line: живая circulation memory проходит здесь между северным watch и чёрной водой как часть одного moving loop.",
        "service_note": "После loop-traffic follow-up ash_pass ведёт мокрую boundary line уже как moving edge leg, а не только как handoff closure.",
    },
    {
        "node_id": "ash_pass",
        "state_flag": "northwatch_marsh_edge_circulation_support_carried",
        "context_note": "На ash_pass уже держат мокрую линию к deep_marsh как edge-watch support leg active reclaimed circulation.",
        "detail_note": "Край прохода теперь даёт уже не только loop movement, а practical wet-boundary help: по кромке идёт carried edge-watch support mark, которая делает мокрую линию полезной, а не только движущейся.",
        "service_note": "После circulation-support follow-up ash_pass ведёт мокрую boundary line уже как practical edge-support leg, а не только как moving traffic.",
    },
    {
        "node_id": "ash_pass",
        "state_flag": "northwatch_marsh_edge_support_delivered",
        "context_note": "На ash_pass уже держат мокрую линию к deep_marsh как leg, куда practical edge aid реально delivered в поле.",
        "detail_note": "Край прохода теперь даёт уже не только carried support trace, а delivered wet-boundary help: edge-watch aid действительно handed in на сырой кромке и поддерживает boundary watch как usable field assistance.",
        "service_note": "После support-delivery follow-up ash_pass ведёт мокрую boundary line уже как место delivered edge help, а не только как carried support leg.",
    },
    {
        "node_id": "ash_pass",
        "state_flag": "northwatch_marsh_edge_support_in_use",
        "context_note": "На ash_pass уже держат мокрую линию к deep_marsh как leg, где delivered edge aid реально используется в boundary watch.",
        "detail_note": "Край прохода теперь даёт уже не только delivered wet-boundary help, а practical edge-leg use: помощь вошла в сам watch turn на сырой кромке и делает передачу между northwatch и deep_marsh реально используемой field practice.",
        "service_note": "После support-use follow-up ash_pass ведёт мокрую boundary line уже как место, где delivered edge help реально работает в watch practice.",
    },
    {
        "node_id": "ash_pass",
        "state_flag": "northwatch_marsh_edge_recoveries_steadied",
        "context_note": "На ash_pass уже держат мокрую линию к deep_marsh как recovery stop, где людей реально приводят в устойчивость на boundary edge.",
        "detail_note": "Край прохода теперь даёт уже не только applied edge-support use, а practical recovery uptake: на сырой кромке переводят дух, собирают вымотанных и steadied recoveries перед следующим ходом, так что wet boundary leg работает как честная recovery shelter inside reclaimed fabric.",
        "service_note": "После refuge-uptake follow-up ash_pass ведёт мокрую boundary line уже как recovery stop, а не только как support in use.",
    },
    {
        "node_id": "ash_pass",
        "state_flag": "northwatch_marsh_edge_recoveries_returned_to_line",
        "context_note": "На ash_pass уже держат мокрую линию к deep_marsh как edge-return point, откуда steadied recoveries реально возвращают в line movement.",
        "detail_note": "Край прохода теперь даёт уже не только recovery shelter, а practical return-to-line handoff: после короткого восстановления recoveries снова вводят в wet boundary movement, и leg работает как честная точка edge re-entry в watch-side line.",
        "service_note": "После return-to-line follow-up ash_pass ведёт мокрую boundary line уже как recovery-to-line return point, а не только как recovery stop.",
    },
    {
        "node_id": "ash_pass",
        "state_flag": "northwatch_marsh_edge_return_referral_set",
        "context_note": "На ash_pass уже держат мокрую линию к deep_marsh как return-line referral point, где returned recoveries получают явный continuation cue обратно в boundary/watch continuity.",
        "detail_note": "Край прохода теперь даёт уже не только edge re-entry, а practical onward-referral handoff: returned recoveries здесь не просто снова идут в line movement, а получают чёткий return-line referral по wet boundary leg, который делает marsh-edge continuation понятной и dependable.",
        "service_note": "После onward-referral follow-up ash_pass ведёт мокрую boundary line уже как return-line referral point, а не только как edge-return point.",
    },
    {
        "node_id": "deep_marsh_threshold",
        "state_flag": "deep_marsh_mist_notice_taken",
        "context_note": "На пороге глубоких болот уже отмечено предупреждение о тумане, чёрной воде и коротком безопасном ходе.",
        "detail_note": "У первых кочек уже помнят, что для этой группы туман не был пустой декорацией, а стал рабочим предупреждением о глубоком болоте.",
    },
    {
        "node_id": "drowned_waystone",
        "state_flag": "deep_marsh_waymarks_read",
        "context_note": "Утопленный камень уже читали как рабочую болотную метку, и направление к старой переправе стало понятнее.",
        "detail_note": "Мох, зарубки и срезы на камне уже разбирали не наугад, а как настоящую болотную наводку к более тёмной воде.",
    },
    {
        "node_id": "ruined_settlement",
        "state_flag": "ruined_watchfire_trace_found",
        "context_note": "В руинах уже отмечали свежий след короткой стоянки и тревожный проход к шахтному направлению.",
        "detail_note": "Среди пустых дворов уже нашли недавний след костра и свежие метки, из-за которых руины ощущаются не просто старыми, а всё ещё живыми для чужого хода.",
    },
    {
        "node_id": "mile_marker_arch",
        "state_flag": "western_road_waybill_read",
        "context_note": "На верстовой арке уже разобрали дорожные отметки и поняли, куда сошёл задержанный обоз.",
        "detail_note": "Меловые знаки на арке уже читали как рабочую следовую сводку: теперь ясно, что свежая задержка уходит в разбитый объезд к брошенной повозке.",
    },
    {
        "node_id": "mile_marker_arch",
        "state_flag": "western_road_detour_markers_prepared",
        "context_note": "У верстовой арки уже обновили первые detour markers под начальную поддержку с базы.",
        "detail_note": "На столбах снова видны marker posts для объезда: тракт ещё rough, но corridor уже держится не только на памяти возчиков.",
    },
    {
        "node_id": "mile_marker_arch",
        "state_flag": "western_road_detour_markers_ready",
        "context_note": "У арки уже держат более надёжную marker-line для разбитого объезда.",
        "detail_note": "Ready-stage support сделал detour line ровнее: дорожные метки снова работают как настоящая corridor guidance, а не как случайная импровизация.",
    },
    {
        "node_id": "mile_marker_arch",
        "state_flag": "western_road_detour_markers_committed",
        "context_note": "Верстовая арка уже держит лучший corridor-marker response на западном тракте.",
        "detail_note": "Committed-stage backing дошёл и сюда: marker line на объезде собрана лучше всего, и western_road читается как поддержанный travel corridor, а не только как место задержки.",
    },
    {
        "node_id": "broken_waycart",
        "state_flag": "western_road_wagon_trace_found",
        "context_note": "У брошенной повозки уже нашли свежий след дорожной задержки и спешной перегрузки.",
        "detail_note": "У сломанной оси уже отмечены свежие ремни, следы переноски груза и короткая стоянка, после которой обоз ушёл дальше налегке.",
    },
    {
        "node_id": "broken_waycart",
        "state_flag": "western_road_waycart_manifest_logged",
        "context_note": "У повозки уже разобрали обрывок обозной ведомости, и место читается как понятный corridor-proof дорожного срыва.",
        "detail_note": "Возле сломанной оси уже собрали waybill scrap и меловую пометку перегрузки: поломка выглядит не случайностью, а зафиксированным следом спешного caravan-отхода.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_waystation_aid_received",
        "context_note": "Во дворе уже приняли обратный рассказ о задержке на объезде и выдали группе дорожную поддержку как знакомому составу.",
        "detail_note": "Под навесом ещё видны следы недавно выданного дорожного набора после рассказа о брошенной повозке и разбитом объезде.",
        "service_note": "После обратного рассказа двор уже реагирует на группу как на тех, кто реально сходил по следу обоза, а не просто просит помощь с дороги.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_support_prepared",
        "context_note": "На постоялом дворе уже чувствуют первый внешний backing, пришедший с базы на тракт.",
        "detail_note": "Двор работает чуть спокойнее: возчики уже знают, что дальний road support начал тянуться не только изнутри тракта, но и с базовой линии.",
        "service_note": "С первым support stage двор уже выглядит менее случайным и более готовым к следующим дорожным возвратам.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_support_ready",
        "context_note": "Постоялый двор уже держит более надёжный road-support tier благодаря готовой базе.",
        "detail_note": "Под навесами стало больше порядка и уверенности: yard feels like a working corridor node, а не как временный дорожный костыль.",
        "service_note": "Ready-stage support делает западный тракт ощутимо надёжнее для тех, кто возвращается со следа.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_support_committed",
        "context_note": "На постоялом дворе уже действует лучший дорожный support tier, дошедший с базы.",
        "detail_note": "Западный тракт теперь ощущается частью общей support-линии: двор держит лучший ритм помощи, а caravan-узел стал заметно устойчивее.",
        "service_note": "Полный support deployment делает waystation настоящей внешней опорой тракта, а не только местом случайной передышки.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_directive_posted",
        "context_note": "На постоялом дворе уже отметили corridor directive, присланный с базы по возвращённому road evidence.",
        "detail_note": "Под навесом теперь лежит не только local marker order, но и прямое домашнее предписание по ритму detour response и corridor control.",
        "service_note": "Western_road теперь держит не только поддержку, но и явный coordinated corridor order с базы.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_directive_fulfilled",
        "context_note": "На дворе уже не только отметили corridor order, но и закрепили detour handling как рабочий порядок для reopened side line.",
        "detail_note": "Western_road теперь держит не просто chalked directive, а реально проведённый порядок двора: detour line читается собраннее, а боковые проходы к северному рубежу и болотной линии выглядят снова рабочими.",
        "service_note": "Постоялый двор уже выполнил corridor directive и ведёт detour response как подтверждённый полевой порядок, готовый держать боковые frontier lines.",
    },
    {
        "node_id": "sunken_ferry",
        "state_flag": "deep_marsh_ferry_trace_found",
        "context_note": "У затонувшей переправы уже замечали свежие следы недавней остановки и брошенный болотный шнур.",
        "detail_note": "На сваях у переправы уже отмечали не только старую труху, но и свежий след недавнего болотного хода.",
    },
    {
        "node_id": "sunken_ferry",
        "state_flag": "deep_marsh_ferry_moorings_logged",
        "context_note": "У переправы уже сверили швартовые метки, и место читается как старая working crossing-memory, а не как просто затонувший настил.",
        "detail_note": "На сваях уже разобрали тихие швартовые метки и срез тростника: у переправы сохранилась осторожная болотная память о том, как здесь держали короткий ход через воду.",
    },
    {
        "node_id": "blackwater_run",
        "state_flag": "deep_marsh_directive_fulfilled",
        "context_note": "У чёрной протоки уже держат не только quiet crossing line, но и reopened боковые ходы к тракту и северному рубежу.",
        "detail_note": "После выполненной болотной директивы протока снова читается как рабочий frontier-side выход: осторожный болотный ход теперь доведён до прямых боковых линий в сторону western_road и northwatch_frontier.",
    },
    {
        "node_id": "blackwater_run",
        "state_flag": "deep_marsh_sidepass_marked",
        "context_note": "У чёрной протоки уже отметили reeds по reopened marsh-road side-pass к western_road.",
        "detail_note": "На чёрной воде теперь видна не только память о quiet crossing, но и свежая осторожная отметка по боковой линии к тракту: болотный side-pass действительно вошёл в local habit.",
    },
    {
        "node_id": "blackwater_run",
        "state_flag": "deep_marsh_sidepass_dispatch_received",
        "context_note": "У чёрной протоки уже приняли side-pass receipt после домашнего dispatch-board review.",
        "detail_note": "Возле чёрной воды теперь держат не только reeds mark, но и короткую receipt-пометку о том, что домашняя dispatch-board память по marsh-road line дошла обратно в поле.",
    },
    {
        "node_id": "blackwater_run",
        "state_flag": "deep_marsh_sidepass_reed_turn_kept",
        "context_note": "У чёрной протоки уже держат remembered reeds-turn по cautious side-pass к western_road.",
        "detail_note": "У воды теперь видно не только sign и receipt, но и lived-in safe detour habit: осторожный side-pass к western_road вошёл в местную болотную практику.",
        "service_note": "После reeds-turn протока ведёт marsh-road side-pass как remembered safe-use trace, а не как одноразовое подтверждение линии.",
    },
    {
        "node_id": "blackwater_run",
        "state_flag": "deep_marsh_sidepass_reed_post_set",
        "context_note": "У чёрной протоки уже держат held reeds-side standing post по cautious side-pass к western_road.",
        "detail_note": "У воды теперь видно не только remembered detour habit, а guarded crossing post: side-pass к western_road удерживается как рабочая постовая отметка и осторожный standing trace.",
        "service_note": "После standing-post follow-up blackwater_run ведёт marsh-road side-pass как held reeds-side post, а не только как safe-use habit.",
    },
    {
        "node_id": "blackwater_run",
        "state_flag": "deep_marsh_sidepass_reed_watch_refreshed",
        "context_note": "У чёрной протоки уже обновляют reeds-side upkeep по held side-pass к western_road.",
        "detail_note": "У воды теперь видно не только held crossing post, а maintained reeds-watch cycle: cautious side-pass к western_road держат в рабочем relief порядке у самой чёрной воды.",
        "service_note": "После upkeep follow-up blackwater_run ведёт side-pass как maintained reeds-side post fabric, а не только как held standing trace.",
    },
    {
        "node_id": "blackwater_run",
        "state_flag": "deep_marsh_sidepass_circuit_handoff_tied",
        "context_note": "У чёрной протоки уже держат cautious side-pass к western_road как marsh-leg handoff общего reclaimed circuit.",
        "detail_note": "У воды теперь видно не только maintained reeds-watch, а marsh-side leg общего loop: cautious pass держит понятную передачу между road relay и boundary watch внутри одного reclaimed circuit rhythm.",
        "service_note": "После circuit handoff blackwater_run ведёт side-pass уже как часть общего reclaimed loop, а не только как maintained reeds-side post.",
    },
    {
        "node_id": "blackwater_run",
        "state_flag": "deep_marsh_sidepass_loop_traffic_traced",
        "context_note": "У чёрной протоки уже держат cautious side-pass к western_road как живой marsh-traffic leg working reclaimed loop.",
        "detail_note": "У воды теперь видно не только handoff tie, а живое loop movement по cautious pass: reeds-side traffic реально циркулирует между road relay и wet boundary leg как часть одной moving frontier practice.",
        "service_note": "После loop-traffic follow-up blackwater_run ведёт side-pass уже как moving marsh leg, а не только как closed handoff.",
    },
    {
        "node_id": "blackwater_run",
        "state_flag": "deep_marsh_sidepass_circulation_support_set",
        "context_note": "У чёрной протоки уже держат cautious side-pass к western_road как marsh-pass support leg active reclaimed circulation.",
        "detail_note": "У воды теперь видно уже не только loop movement, а practical crossing help: reeds-side circulation приносит на cautious pass небольшую, но реальную support trace, которая делает мокрый ход полезнее в поле.",
        "service_note": "После circulation-support follow-up blackwater_run ведёт side-pass уже как practical marsh-support leg, а не только как moving traffic.",
    },
    {
        "node_id": "blackwater_run",
        "state_flag": "deep_marsh_sidepass_support_delivered",
        "context_note": "У чёрной протоки уже держат cautious side-pass к western_road как leg, куда practical crossing aid реально delivered в поле.",
        "detail_note": "Боковая линия здесь даёт уже не только support trace, а delivered marsh-leg help: reeds-side aid действительно handed in у протоки и поддерживает cautious crossing как usable field assistance.",
        "service_note": "После support-delivery follow-up blackwater_run ведёт cautious side-pass уже как место delivered crossing help, а не только как prepared support leg.",
    },
    {
        "node_id": "blackwater_run",
        "state_flag": "deep_marsh_sidepass_support_in_use",
        "context_note": "У чёрной протоки уже держат cautious side-pass к western_road как leg, где delivered crossing aid реально используется в поле.",
        "detail_note": "Боковая линия здесь даёт уже не только delivered marsh-leg help, а practical crossing use: reeds-side aid вошла в осторожный crossing rhythm и оставляет usable support note, которую можно нести дальше по сырому leg.",
        "service_note": "После support-use follow-up blackwater_run ведёт cautious side-pass уже как место, где delivered crossing help реально работает в practice.",
    },
    {
        "node_id": "blackwater_run",
        "state_flag": "deep_marsh_sidepass_stragglers_received",
        "context_note": "У чёрной протоки уже держат cautious side-pass к western_road как receiving point, куда реально принимают отбившихся stragglers.",
        "detail_note": "Боковая линия здесь даёт уже не только applied marsh-support use, а practical marsh fallback: у воды принимают запоздавших и вымотанных, а cautious side-pass начинает работать как честная receiving point для stragglers по reclaimed line.",
        "service_note": "После refuge-uptake follow-up blackwater_run ведёт cautious side-pass уже как fallback receiving point, а не только как support in use.",
    },
    {
        "node_id": "blackwater_run",
        "state_flag": "deep_marsh_sidepass_stragglers_guided_forward",
        "context_note": "У чёрной протоки уже держат cautious side-pass к western_road как forward-routing point, откуда received stragglers реально ведут дальше.",
        "detail_note": "Боковая линия здесь даёт уже не только fallback receiving point, а practical onward guidance: у воды принятых stragglers снова собирают в движение, и cautious side-pass начинает работать как честная точка forward return по reclaimed marsh leg.",
        "service_note": "После return-to-line follow-up blackwater_run ведёт cautious side-pass уже как forward-routing point, а не только как receiving fallback.",
    },
    {
        "node_id": "blackwater_run",
        "state_flag": "deep_marsh_sidepass_forward_referral_marked",
        "context_note": "У чёрной протоки уже держат cautious side-pass к western_road как forward-referral point, где guided stragglers получают safer continuation cue.",
        "detail_note": "Боковая линия здесь даёт уже не только onward guidance, а practical forward-referral mark: reeds-side leg явно указывает dependable safer continuation дальше по cautious pass и делает blackwater_run честной точкой referral, а не только возврата в движение.",
        "service_note": "После onward-referral follow-up blackwater_run ведёт cautious side-pass уже как forward-referral point, а не только как forward-routing point.",
    },
    {
        "node_id": "reed_shelter",
        "state_flag": "deep_marsh_shelter_aid_received",
        "context_note": "В тростниковом приюте уже дали группе сухой кров и короткую болотную поддержку после возвращения из сырого хода.",
        "detail_note": "Под навесом ещё видны следы недавно выданного сухого места и короткой помощи именно для этой группы.",
        "service_note": "Приют уже однажды дал этой группе тихий кров после болотного выхода и теперь скорее подтверждает знакомую помощь, чем впервые открывается.",
    },
    {
        "node_id": "reed_shelter",
        "state_flag": "deep_marsh_support_prepared",
        "context_note": "В тростниковом приюте уже чувствуют первую осторожную поддержку, дошедшую с базы.",
        "detail_note": "Даже болотный refuge выглядит чуть спокойнее: хозяйка уже не так бережёт каждый сухой пучок, потому что знает о первом внешнем backing.",
        "service_note": "С первым support stage приют отвечает теплее и увереннее, хотя по-прежнему держится тихо и бережно.",
    },
    {
        "node_id": "reed_shelter",
        "state_flag": "deep_marsh_support_ready",
        "context_note": "Тростниковый приют уже держит более надёжную refuge-помощь благодаря готовой базе.",
        "detail_note": "В приюте стало меньше нервной экономии и больше спокойной готовности помочь тем, кто возвращается из сырого хода.",
        "service_note": "Ready-stage support делает болотный refuge ощутимо надёжнее и человечнее на возвращении.",
    },
    {
        "node_id": "reed_shelter",
        "state_flag": "deep_marsh_support_committed",
        "context_note": "В тростниковом приюте уже действует лучший refuge-support tier, дошедший с базы.",
        "detail_note": "Болотный приют теперь ощущается не забытым краем, а настоящей тихой внешней опорой, которую база сумела дотянуть до самой сырой линии.",
        "service_note": "Полный support deployment делает refuge в deep_marsh лучшей версией его тихой помощи: мягкой, но уже не хрупкой.",
    },
    {
        "node_id": "reed_shelter",
        "state_flag": "deep_marsh_wayline_prepared",
        "context_note": "У тростникового приюта уже сплели первую quiet wayline для болотного возврата.",
        "detail_note": "Тростник у навеса перевязан не случайно: первая support-driven wayline помогает держать короткий ход назад к сухому настилу.",
    },
    {
        "node_id": "reed_shelter",
        "state_flag": "deep_marsh_wayline_ready",
        "context_note": "Приют уже держит более надёжную marsh-wayline для возврата из сырого хода.",
        "detail_note": "Ready-stage support дал приюту quiet wayfinding line: теперь refuge помогает не только переждать сырость, но и увереннее вернуться к ней.",
    },
    {
        "node_id": "reed_shelter",
        "state_flag": "deep_marsh_wayline_committed",
        "context_note": "Тростниковый приют уже держит лучшую quiet wayline deep_marsh.",
        "detail_note": "Полная поддержка с базы дошла до самого сырого края: quiet wayline держится лучше всего, и приют ощущается настоящей survival-опорой на возврате.",
    },
    {
        "node_id": "reed_shelter",
        "state_flag": "deep_marsh_directive_posted",
        "context_note": "У тростникового приюта уже связали присланный с базы crossing directive по возвращённому болотному evidence.",
        "detail_note": "Приют теперь держит не только quiet wayline, но и прямое домашнее указание о том, как вести осторожный болотный возврат после crossing-memory trace.",
        "service_note": "Deep_marsh теперь чувствует не только support, но и явный coordinated crossing order с базы.",
    },
    {
        "node_id": "reed_shelter",
        "state_flag": "deep_marsh_directive_fulfilled",
        "context_note": "У тростникового приюта уже не только связали directive, но и закрепили quiet crossing line.",
        "detail_note": "Болотный order довели до поля: приют теперь держит не только память о переправе, а подтверждённую quiet crossing line для осторожного возврата.",
        "service_note": "Deep_marsh уже выполнил crossing directive и держит у приюта реально закреплённую return line.",
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
    {
        "node_id": "northwatch_outpost",
        "first_entry_type": "settlement_welcome",
        "first_entry_title": "Северный рубеж принимает группу",
        "first_entry_note": "Дозорный костёр и навесы быстро дают понять: это уже новый участок карты, но ещё живой и обжитой.",
        "return_entry_type": "return_entry",
        "return_entry_title": "Снова на северном рубеже",
        "return_entry_note": "Пост узнаётся сразу, и группа быстро возвращает себе прежний ритм рубежного узла.",
    },
    {
        "node_id": "ash_pass",
        "first_entry_type": "quiet_entry",
        "first_entry_title": "Зольный проход открыт перед группой",
        "first_entry_note": "На шаге от рубежа место уже встречает не порядком поста, а сухой гарью и тревожной тишиной.",
        "return_entry_type": "return_entry",
        "return_entry_title": "Возвращение в зольный проход",
        "return_entry_note": "Проход узнаётся по гаревому ветру и ощущению, что запас безопасного хода снова короткий.",
    },
    {
        "node_id": "deep_marsh_threshold",
        "first_entry_type": "quiet_entry",
        "first_entry_title": "Глубокие болота принимают неохотно",
        "first_entry_note": "Порог глубоких болот встречает группу туманом, влажной тишиной и чувством, что дальше дорога держится только на старых метках.",
        "return_entry_type": "return_entry",
        "return_entry_title": "Снова на пороге глубоких болот",
        "return_entry_note": "Первые сухие кочки узнаются сразу, но дальше болото снова требует коротких и точных решений.",
    },
    {
        "node_id": "blackwater_run",
        "first_entry_type": "quiet_entry",
        "first_entry_title": "Чёрная протока выходит из тумана",
        "first_entry_note": "У протоки болото перестаёт быть только сырым фоном и превращается в узкий, вязкий рискованный ход.",
        "return_entry_type": "return_entry",
        "return_entry_title": "Возвращение к чёрной протоке",
        "return_entry_note": "У чёрной воды снова мало места для ошибки, и даже знакомый путь не кажется спокойным.",
    },
    {
        "node_id": "western_road_watch",
        "first_entry_type": "settlement_welcome",
        "first_entry_title": "Западный тракт принимает движение",
        "first_entry_note": "За воротами крепости группа попадает не в пустую отметку, а в живую дорожную линию со следами обозов, задержек и быстрых решений на ходу.",
        "return_entry_type": "return_entry",
        "return_entry_title": "Снова на западном тракте",
        "return_entry_note": "Широкий тракт узнаётся сразу, но следы недавнего прохода не дают воспринимать его как пустую безопасную полосу.",
    },
    {
        "node_id": "rutted_detour",
        "first_entry_type": "quiet_entry",
        "first_entry_title": "Разбитый объезд уводит с линии тракта",
        "first_entry_note": "На объезде ровная дорога заканчивается, и дальше западный ход читается уже по колее, задержкам и оставленному грузу.",
        "return_entry_type": "return_entry",
        "return_entry_title": "Возвращение на разбитый объезд",
        "return_entry_note": "На объезде снова мало порядка и много свежих следов, даже если маршрут уже знаком.",
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
        "node_id": "western_road_watch",
        "event_id": "western_road_watch_delay_notice",
        "first_visit_only": True,
        "one_shot": True,
        "result_type": "settlement_notice",
        "title": "На тракте сразу говорят о задержанном обозе",
        "summary": "При первом входе на western_road дорожные люди быстро отмечают недавнюю задержку обоза, верстовую арку с пометками и разбитый объезд, куда ушёл свежий след.",
        "result_summary": "Западный тракт встречает группу не тишиной, а дорожной сводкой: обоз недавно сошёл с линии у верстовой арки, и если проверять след, то смотреть нужно на объезд и брошенную повозку, а не просто идти дальше по дороге.",
        "discovered_notes": [
            "У дорожного навеса советуют сперва сверить пометки на арке, потом решать, стоит ли уходить в разбитый объезд за следом задержанного обоза."
        ],
        "intel_entry_type": "guidance",
        "intel_title": "Сводка о задержке на западном тракте",
        "node_state_flags": ["western_road_delay_notice_taken"],
        "node_state_summary": "На западном тракте уже отмечено первое дорожное предупреждение о задержанном обозе и разбитом объезде.",
        "applied_effects": ["destination_notice:western_road_watch", "intel:guidance"],
        "tags": ["road", "guidance", "western_road"],
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
    {
        "node_id": "forest_settlement",
        "event_id": "forest_settlement_hunters_warning",
        "first_visit_only": True,
        "one_shot": True,
        "result_type": "settlement_notice",
        "title": "Охотники быстро отмечают старую дорогу",
        "summary": "При первом заходе в лесной посёлок местные сразу предупреждают о старой дороге к руинам, тревожном шахтном следе и том, что идти туда лучше коротким ходом.",
        "result_summary": "Лесной посёлок встречает группу не только тёплым двором, но и рабочим предупреждением: старая дорога к руинам снова привлекает внимание, и идти туда стоит с понятной целью и возможностью быстро вернуться.",
        "discovered_notes": [
            "Охотники советуют сперва проверить старую дорогу, потом смотреть на руины и уже только после этого решать, стоит ли приближаться к шахтному входу."
        ],
        "intel_entry_type": "warning",
        "intel_title": "Предупреждение охотников о старой дороге",
        "node_state_flags": ["forest_hunters_warning_taken"],
        "node_state_summary": "В лесном посёлке уже отмечено первое предупреждение о старой дороге и руинах.",
        "applied_effects": ["destination_notice:forest_settlement", "intel:warning"],
        "tags": ["warning", "forest", "ruins"],
    },
    {
        "node_id": "northwatch_outpost",
        "event_id": "northwatch_outpost_briefing",
        "label": "Короткая сводка северного дозора",
        "first_visit_only": True,
        "one_shot": True,
        "result_type": "settlement_notice",
        "title": "Дозор быстро вводит группу в обстановку",
        "summary": "При первом входе дозорные коротко отмечают безопасную линию рубежа, склад снабжения, сигнальную палисаду и тревожный зольный проход.",
        "result_summary": "Северный рубеж встречает группу рабочей сводкой: сначала сверить сигналы на палисаде, затем уже решать, стоит ли лезть к редуту над зольным проходом.",
        "discovered_notes": [
            "Смена дозора советует сначала освоиться у поста и интендантского двора, потом подняться на палисаду и только после этого решать, нужен ли короткий выход к редуту над зольным проходом."
        ],
        "intel_entry_type": "guidance",
        "intel_title": "Сводка северного дозора",
        "node_state_flags": ["northwatch_briefing_taken"],
        "node_state_summary": "На северном рубеже уже отмечено первое дозорное введение для этой группы.",
        "applied_effects": ["destination_notice:northwatch_outpost", "intel:guidance"],
        "tags": ["frontier", "guidance", "northwatch"],
    },
    {
        "node_id": "ash_pass",
        "event_id": "ash_pass_warning",
        "label": "Гарь и осыпь на проходе",
        "result_type": "local_warning",
        "title": "Проход встречает гаревым ветром",
        "summary": "Зольный проход каждый раз напоминает, что это уже не спокойный дозорный узел, а нервная frontier-ветка.",
        "result_summary": "На входе в зольный проход ветер тянет гарью и мелкой осыпью: место честно предупреждает, что рубеж здесь уже тонкий.",
        "discovered_notes": [
            "На проходе не стоит тянуть с решением: ветер быстро съедает обзор, а под ногами осыпается сухой склон.",
            "Если тревога и правда идёт от редута, задерживаться у самой осыпи бессмысленно: всё важное лежит чуть выше, у старой каменной кладки."
        ],
        "intel_entry_type": "warning",
        "intel_title": "Предупреждение зольного прохода",
        "applied_effects": ["destination_warning:ash_pass", "intel:warning"],
        "tags": ["warning", "frontier", "ash_pass"],
    },
    {
        "node_id": "ruined_settlement",
        "event_id": "ruined_settlement_watchfire_trace",
        "first_visit_only": True,
        "one_shot": True,
        "result_type": "first_discovery",
        "title": "В руинах заметен свежий след костра",
        "summary": "Первый заход в руины показывает, что место не совсем мертво: среди пустых дворов виден свежий след короткой стоянки и тревожный ход к шахтному направлению.",
        "result_summary": "У разрушенного посёлка группа находит свежий след костра и понимает, что старая дорога ведёт не к пустому воспоминанию, а к месту, где кто-то бывал совсем недавно.",
        "discovered_notes": [
            "След короткой стоянки у руин подсказывает, что шахтное направление ещё тянет к себе чужие ходы, и возвращаться к посёлку теперь есть с чем."
        ],
        "intel_entry_type": "clue",
        "intel_title": "Свежий след у руин",
        "node_state_flags": ["ruined_watchfire_trace_found"],
        "node_state_summary": "У разрушенного посёлка уже найден свежий след короткой стоянки и тревожного прохода к шахтному направлению.",
        "applied_effects": ["destination_notice:ruined_settlement", "intel:clue"],
        "tags": ["clue", "ruins", "forest"],
    },
    {
        "node_id": "deep_marsh_threshold",
        "event_id": "deep_marsh_mist_notice",
        "first_visit_only": True,
        "one_shot": True,
        "result_type": "local_warning",
        "title": "Туман на пороге болот быстро съедает уверенность",
        "summary": "При первом входе в deep_marsh становится ясно, что здесь держатся не за широкую дорогу, а за редкие сухие метки и короткие решения.",
        "result_summary": "Глубокие болота встречают группу мокрым предупреждением: безопасный ход здесь короткий, а лишний круг по туману быстро делает местность чужой.",
        "discovered_notes": [
            "На болотном пороге лучше сначала держаться приюта и путевого камня, а в чёрную воду уходить только с понятной приметой."
        ],
        "intel_entry_type": "warning",
        "intel_title": "Предупреждение у порога глубоких болот",
        "node_state_flags": ["deep_marsh_mist_notice_taken"],
        "node_state_summary": "На пороге глубоких болот уже отмечено первое честное предупреждение о местном тумане и коротком безопасном ходе.",
        "applied_effects": ["destination_warning:deep_marsh_threshold", "intel:warning"],
        "tags": ["warning", "marsh", "deep_marsh"],
    },
    {
        "node_id": "blackwater_run",
        "event_id": "blackwater_run_warning",
        "result_type": "local_warning",
        "title": "Чёрная вода не даёт долгой остановки",
        "summary": "У чёрной протоки болото напоминает, что любой ход здесь должен быть коротким и собранным.",
        "result_summary": "На чёрной протоке вода подбирается к кочкам, туман съедает край берега, и место честно предупреждает: задержка здесь опаснее, чем в обычной сырости.",
        "discovered_notes": [
            "Если держать путь дальше протоки, лучше цепляться не за открытую воду, а за след старой переправы."
        ],
        "intel_entry_type": "warning",
        "intel_title": "Предупреждение чёрной протоки",
        "applied_effects": ["destination_warning:blackwater_run", "intel:warning"],
        "tags": ["warning", "marsh", "blackwater"],
    },
    {
        "node_id": "sunken_ferry",
        "event_id": "sunken_ferry_trace",
        "first_visit_only": True,
        "one_shot": True,
        "result_type": "first_discovery",
        "title": "У переправы виден свежий болотный след",
        "summary": "Затонувшая переправа оказывается не просто старым обломком: у сваи заметны свежие верёвки, срез тростника и след недавней короткой остановки.",
        "result_summary": "У затонувшей переправы группа находит свежий болотный след. Теперь deep_marsh читается не как пустая сырость, а как место, где по-прежнему ходят короткими тайными маршрутами.",
        "discovered_notes": [
            "У сломанной переправы ещё держится свежий болотный шнур и срезанный тростник: кто-то прошёл здесь совсем недавно и не задерживался надолго."
        ],
        "intel_entry_type": "clue",
        "intel_title": "След у затонувшей переправы",
        "node_state_flags": ["deep_marsh_ferry_trace_found"],
        "node_state_summary": "У затонувшей переправы уже найден свежий след недавнего болотного хода.",
        "applied_effects": ["destination_notice:sunken_ferry", "intel:clue"],
        "tags": ["clue", "marsh", "ferry"],
    },
    {
        "node_id": "rutted_detour",
        "event_id": "rutted_detour_warning",
        "result_type": "local_warning",
        "title": "На объезде колея ломает ритм дороги",
        "summary": "Разбитый объезд каждый раз напоминает, что здесь опаснее не сама глубина, а потеря темпа и неверный выбор следа.",
        "result_summary": "У разбитого объезда тракт перестаёт быть ровной линией: колея тянет вбок, следы путаются, и место честно предупреждает, что дорожная задержка здесь рождается из спешки.",
        "discovered_notes": [
            "Если идти по следу обоза, лучше держаться свежих грузовых следов и не верить старой сухой колее у края дороги."
        ],
        "intel_entry_type": "warning",
        "intel_title": "Предупреждение разбитого объезда",
        "applied_effects": ["destination_warning:rutted_detour", "intel:warning"],
        "tags": ["warning", "road", "detour"],
    },
    {
        "node_id": "broken_waycart",
        "event_id": "broken_waycart_trace",
        "first_visit_only": True,
        "one_shot": True,
        "result_type": "first_discovery",
        "title": "У повозки найден свежий дорожный след",
        "summary": "Брошенная повозка оказывается не старым хламом, а свежим следом задержанного обоза: груз разгружали наспех и уходили дальше налегке.",
        "result_summary": "У брошенной повозки группа находит свежий след дорожной задержки и спешной перегрузки. Теперь на western_road есть не только слух о задержке, а понятное подтверждение, с которым стоит возвращаться к двору у тракта.",
        "discovered_notes": [
            "По сломанной оси и порванным ремням видно, что обоз не погиб здесь, а быстро разгрузился и продолжил путь, бросив только поломанное звено."
        ],
        "intel_entry_type": "clue",
        "intel_title": "След у брошенной повозки",
        "node_state_flags": ["western_road_wagon_trace_found"],
        "node_state_summary": "У брошенной повозки уже найден свежий след дорожной задержки и спешной перегрузки.",
        "applied_effects": ["destination_notice:broken_waycart", "intel:clue"],
        "tags": ["clue", "road", "wagon"],
    },
    {
        "node_id": "broken_redoubt",
        "event_id": "broken_redoubt_supply_trace",
        "first_visit_only": True,
        "one_shot": True,
        "result_type": "first_discovery",
        "title": "У редута находят свежий след тревоги",
        "summary": "Разбитый редут оказывается не пустой декорацией: у кладки видны недавние следы тревожной стоянки и брошенного снабженческого ящика.",
        "result_summary": "У разбитого редута группа находит свежие следы тревоги и обрывок складской метки. Теперь на рубеж можно возвращаться уже не с догадкой, а с подтверждённым следом.",
        "discovered_notes": [
            "Под стеной редута лежит расколотый ящик с рубежной меткой: кто-то спешно бросал снабжение и отходил в сторону прохода.",
            "След у редута достаточно свежий, чтобы интендант на посту понял: тревога касается не только слухов, а реального недавнего хода."
        ],
        "intel_entry_type": "clue",
        "intel_title": "След тревоги у разбитого редута",
        "node_state_flags": ["northwatch_redoubt_trace_found"],
        "node_state_summary": "У разбитого редута уже найден след недавней тревожной стоянки и брошенного снабжения.",
        "applied_effects": ["destination_notice:broken_redoubt", "intel:clue"],
        "tags": ["clue", "frontier", "redoubt"],
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
        "summary": "Собрать лесные дорожные припасы после короткого обхода старой дороги и руин.",
        "result_summary": "Посёлок принимает обратный рассказ о старой дороге и руинах, собирает для группы крепкий лесной набор и отмечает, что помощь выдана уже после реального выхода, а не на одних разговорах.",
        "discovered_notes": [
            "Охотники советуют не растягивать следующий выход: старая дорога и руины уже проверены, а значит запас стоит тратить на уверенный короткий ход."
        ],
        "applied_effects": ["supplies_secured", "support_note:forest_return"],
        "node_state_flags": ["forest_supplies_secured", "forest_return_report_logged"],
        "node_state_summary": "В лесном посёлке уже приняли обратный рассказ о старой дороге и выдали дорожный набор этой группе.",
    },
    {
        "node_id": "forest_settlement",
        "service_key": "frontier_support",
        "service_id": "forest_settlement_frontier_support",
        "service_kind": "support",
        "result_type": "guidance_received",
        "summary": "Запросить первую осторожную frontier-поддержку после внешнего доклада.",
        "result_summary": "Лесной посёлок собирает для группы осторожную первую рубежную поддержку: короткую охотничью выкладку, сдержанную наводку и подготовку под быстрый возврат с края.",
        "discovered_notes": [
            "После первого внешнего доклада в посёлке уже не отмахиваются от дальних тревог и начинают собирать для группы практичный, но ещё осторожный выходной набор."
        ],
        "applied_effects": ["frontier_support:tier1", "intel:frontier_support"],
        "node_state_flags": ["frontier_support_prepared"],
        "node_state_summary": "В лесном посёлке уже собрали первый tier frontier support под единичный внешний доклад.",
        "required_state_flags": ["frontier_report_started"],
    },
    {
        "node_id": "forest_settlement",
        "service_key": "frontier_support",
        "service_id": "forest_settlement_frontier_support",
        "service_kind": "support",
        "result_type": "guidance_received",
        "summary": "Запросить усиленную frontier-поддержку после распознанного pattern.",
        "result_summary": "Когда повторяющийся frontier pattern уже подтверждён, посёлок даёт группе более собранную поддержку: уточнённые возвратные ориентиры, более уверенный сбор и чёткую готовность под нервный внешний ход.",
        "discovered_notes": [
            "После двух независимых сводок помощь в посёлке становится осмысленнее: теперь это не просто осторожность, а уже собранный ответ на повторяющийся рисунок frontier pressure."
        ],
        "applied_effects": ["frontier_support:tier2", "intel:frontier_support_pattern"],
        "node_state_flags": ["frontier_support_ready"],
        "node_state_summary": "В лесном посёлке уже держат второй tier frontier support под повторяющийся внешний pattern.",
        "required_state_flags": ["frontier_pattern_seen"],
    },
    {
        "node_id": "forest_settlement",
        "service_key": "frontier_support",
        "service_id": "forest_settlement_frontier_support",
        "service_kind": "support",
        "result_type": "guidance_received",
        "summary": "Запросить полный local frontier support после общей сводки по всем рубежам.",
        "result_summary": "После полной frontier summary посёлок выдаёт лучший tier local frontier support: согласованные дорожные пометки, приоритетный охотничий набор и понятный ритм возвратов под общий внешний нажим.",
        "discovered_notes": [
            "Когда картина сходится по всем трём соседним рубежам, посёлок отвечает уже не частным советом, а лучшей доступной local support-подготовкой под весь внешний край."
        ],
        "applied_effects": ["frontier_support:tier3", "intel:frontier_support_full"],
        "node_state_flags": ["frontier_support_committed"],
        "node_state_summary": "В лесном посёлке уже собран лучший tier frontier support под общую сводку со всех соседних рубежей.",
        "required_state_flags": ["frontier_full_pattern_logged"],
    },
    {
        "node_id": "forest_settlement",
        "service_key": "frontier_readiness",
        "service_id": "forest_settlement_frontier_readiness",
        "service_kind": "support",
        "result_type": "guidance_received",
        "summary": "Запросить первую readiness-поддержку после подтверждённой стабилизации на одном краю.",
        "result_summary": "После первого confirmed stabilization review лесной посёлок уже даёт группе более собранную домашнюю готовность: короткую frontier выкладку, ясный возвратный порядок и спокойную уверенность, что хотя бы один край теперь держится лучше.",
        "discovered_notes": [
            "Первый подтверждённый stabilization result позволяет базе отвечать не только советом, а первой реальной readiness-подготовкой под следующий внешний ход."
        ],
        "applied_effects": ["frontier_readiness:tier1", "intel:frontier_readiness"],
        "node_state_flags": ["frontier_readiness_prepared"],
        "node_state_summary": "В лесном посёлке уже собрали первый readiness tier на основе подтверждённой стабилизации frontier.",
        "required_state_flags": ["frontier_stabilization_started"],
    },
    {
        "node_id": "forest_settlement",
        "service_key": "frontier_readiness",
        "service_id": "forest_settlement_frontier_readiness",
        "service_kind": "support",
        "result_type": "guidance_received",
        "summary": "Запросить усиленную readiness-поддержку после comparative stabilization review.",
        "result_summary": "Когда база сравнила уже две подтверждённые stabilization measures, readiness response становится сильнее: сбор проходит быстрее, возвратные роли яснее, а посёлок ощущает себя не только реагирующим, а действительно подготовленным к новому внешнему ритму.",
        "discovered_notes": [
            "После comparative stabilization review readiness в посёлке становится заметно крепче: это уже не первый отклик, а собранная домашняя готовность под несколько frontier edges."
        ],
        "applied_effects": ["frontier_readiness:tier2", "intel:frontier_readiness_comparison"],
        "node_state_flags": ["frontier_readiness_ready"],
        "node_state_summary": "В лесном посёлке уже держат второй readiness tier после comparative stabilization review.",
        "required_state_flags": ["frontier_stabilization_compared"],
    },
    {
        "node_id": "forest_settlement",
        "service_key": "frontier_readiness",
        "service_id": "forest_settlement_frontier_readiness",
        "service_kind": "support",
        "result_type": "guidance_received",
        "summary": "Запросить полный frontier-readiness support после полной stabilization picture.",
        "result_summary": "После полной frontier stabilization picture посёлок выдаёт лучший tier readiness support: приоритетный сбор, чёткий возвратный порядок и уверенную домашнюю готовность, выросшую из реально подтверждённой стабилизации по всему внешнему кругу.",
        "discovered_notes": [
            "Полный stabilization review замыкается реальной домашней выгодой: база уже готовит следующий выход как место, которое не только понимает frontier, но и стало лучше подготовлено благодаря выполненной полевой работе."
        ],
        "applied_effects": ["frontier_readiness:tier3", "intel:frontier_readiness_full"],
        "node_state_flags": ["frontier_readiness_committed"],
        "node_state_summary": "В лесном посёлке уже собран лучший readiness tier после полной frontier stabilization picture.",
        "required_state_flags": ["frontier_stabilization_compiled"],
    },
    {
        "node_id": "northwatch_outpost",
        "service_key": "local_guidance",
        "service_id": "northwatch_outpost_guidance",
        "service_kind": "guidance",
        "one_shot": True,
        "result_type": "guidance_received",
        "summary": "Получить у дозора короткое уточнение по линии рубежа.",
        "result_summary": "Дозор отмечает для группы, где на рубеже держится надёжный отход и почему зольный проход лучше не растягивать в долгую прогулку.",
        "discovered_notes": [
            "На рубеже советуют возвращаться к костру до полной темноты: дальше линии навесов земля уже не прощает долгих пауз."
        ],
        "applied_effects": ["guidance_recorded:northwatch_outpost"],
    },
    {
        "node_id": "northwatch_quartermaster",
        "service_key": "resupply",
        "service_id": "northwatch_quartermaster_resupply",
        "service_kind": "supplies",
        "one_shot": True,
        "result_type": "supplies_secured",
        "summary": "Получить рубежный комплект и обратную поддержку после короткой вылазки к редуту.",
        "result_summary": "Интендант принимает обратный доклад о следе у редута, открывает склад и выдаёт группе компактный рубежный набор как честную поддержку за возвращение с полезной сводкой.",
        "discovered_notes": [
            "Кладовщик отмечает, что редут проверяли не зря: теперь на рубеже знают, куда смотреть, и выдают группе короткий комплект под следующий уверенный ход."
        ],
        "applied_effects": ["supplies_secured:northwatch_quartermaster", "support_note:northwatch_return"],
        "node_state_flags": ["northwatch_quartermaster_supplies", "northwatch_redoubt_return_logged"],
        "node_state_summary": "На интендантском дворе уже приняли обратный доклад с редута и выдали группе рубежный набор.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "service_key": "resupply",
        "service_id": "northwatch_quartermaster_resupply",
        "service_kind": "supplies",
        "one_shot": True,
        "result_type": "supplies_secured",
        "summary": "Получить рубежный набор с первым внешним backing от лесного посёлка.",
        "result_summary": "Интендантский двор уже чувствует первую поддержку с базы: набор собран чуть увереннее, а рубежный доклад принимают как часть большей линии помощи, а не только местной импровизации.",
        "discovered_notes": [
            "На северном рубеже уже знают, что лесной посёлок начал поддерживать дальние выходы, и потому интендант держит первый более собранный набор под короткие вылазки."
        ],
        "applied_effects": ["supplies_secured:northwatch_quartermaster", "support_note:northwatch_deployment"],
        "node_state_flags": ["northwatch_quartermaster_supplies", "northwatch_redoubt_return_logged", "northwatch_support_prepared"],
        "node_state_summary": "На северном рубеже уже ощущается первый внешний support deployment с базы.",
        "requires_any_group_node_state_flags": ["frontier_support_prepared"],
    },
    {
        "node_id": "northwatch_quartermaster",
        "service_key": "resupply",
        "service_id": "northwatch_quartermaster_resupply",
        "service_kind": "supplies",
        "one_shot": True,
        "result_type": "supplies_secured",
        "summary": "Получить более организованный рубежный набор после готовности базы.",
        "result_summary": "Когда лесной посёлок уже держит готовую линию поддержки, северный интендант отвечает заметно организованнее: набор полнее, порядок выдачи быстрее, а readiness рубежа ощущается не на словах, а в ритме самого двора.",
        "discovered_notes": [
            "Северный двор перестал работать от случая к случаю: с готовой поддержкой с базы рубеж держит более надёжный порядок снабжения."
        ],
        "applied_effects": ["supplies_secured:northwatch_quartermaster", "support_note:northwatch_ready"],
        "node_state_flags": ["northwatch_quartermaster_supplies", "northwatch_redoubt_return_logged", "northwatch_support_ready"],
        "node_state_summary": "На северном рубеже уже держат более организованную supply-readiness по внешней поддержке с базы.",
        "requires_any_group_node_state_flags": ["frontier_support_ready"],
    },
    {
        "node_id": "northwatch_quartermaster",
        "service_key": "resupply",
        "service_id": "northwatch_quartermaster_resupply",
        "service_kind": "supplies",
        "one_shot": True,
        "result_type": "supplies_secured",
        "summary": "Получить лучший рубежный набор после полной поддержки с базы.",
        "result_summary": "При полной поддержке с базы северный двор даёт лучшую полевую версию своего снабжения: быстрый приём, чёткий комплект и ощутимое чувство, что рубеж теперь держат как часть общей frontier-линии, а не одиночным упрямством.",
        "discovered_notes": [
            "После полной сводки и полной поддержки с базы северный рубеж выглядит уже не только стойким, но и по-настоящему снабжаемым."
        ],
        "applied_effects": ["supplies_secured:northwatch_quartermaster", "support_note:northwatch_committed"],
        "node_state_flags": ["northwatch_quartermaster_supplies", "northwatch_redoubt_return_logged", "northwatch_support_committed"],
        "node_state_summary": "На северном рубеже уже действует лучший support tier, пришедший из лесного посёлка.",
        "requires_any_group_node_state_flags": ["frontier_support_committed"],
    },
    {
        "node_id": "reed_shelter",
        "service_key": "shrine_aid",
        "service_id": "reed_shelter_shrine_aid",
        "service_kind": "shrine",
        "one_shot": True,
        "result_type": "lodging_received",
        "summary": "Попросить тихий сухой кров и болотную помощь под тростниковым навесом.",
        "result_summary": "Тростниковый приют даёт группе сухой настил, тёплую горечь от болотных трав и короткую подсказку, как не потерять обратный ход в тумане.",
        "discovered_notes": [
            "Хозяйка приюта советует возвращаться по собственным меткам, а не доверять открытому зеркалу воды после заката."
        ],
        "applied_effects": ["lodging_received", "marsh_refuge_recorded"],
        "node_state_flags": ["deep_marsh_shelter_aid_received"],
        "node_state_summary": "В тростниковом приюте уже дали группе тихий болотный кров после возвращения из сырого хода.",
    },
    {
        "node_id": "reed_shelter",
        "service_key": "shrine_aid",
        "service_id": "reed_shelter_shrine_aid",
        "service_kind": "shrine",
        "one_shot": True,
        "result_type": "lodging_received",
        "summary": "Попросить тихую болотную помощь, уже поддержанную с базы.",
        "result_summary": "Тростниковый приют даёт более уверенный тихий кров: хозяйка уже знает, что с базы начали тянуть поддержку наружу, и refuge feels less improvised, even in this wet dark edge.",
        "discovered_notes": [
            "Даже на болотной кромке чувствуется первый внешний backing: приют легче решается расходовать сухие травы и хороший настил на тех, кто возвращается с дальнего хода."
        ],
        "applied_effects": ["lodging_received", "marsh_refuge_recorded", "support_note:deep_marsh_prepared"],
        "node_state_flags": ["deep_marsh_shelter_aid_received", "deep_marsh_support_prepared"],
        "node_state_summary": "В тростниковом приюте уже чувствуют первую осторожную поддержку, пришедшую с базы.",
        "requires_any_group_node_state_flags": ["frontier_support_prepared"],
    },
    {
        "node_id": "reed_shelter",
        "service_key": "shrine_aid",
        "service_id": "reed_shelter_shrine_aid",
        "service_kind": "shrine",
        "one_shot": True,
        "result_type": "lodging_received",
        "summary": "Попросить более надёжную refuge-поддержку при готовой базе.",
        "result_summary": "Когда база уже держит готовую линию помощи, болотный refuge становится надёжнее: сухой настил, тёплая горечь и обратные метки готовят спокойнее и без прежней нервной экономии.",
        "discovered_notes": [
            "С ready-stage поддержкой приют уже меньше боится тратить хорошие болотные припасы на вернувшихся ходоков."
        ],
        "applied_effects": ["lodging_received", "marsh_refuge_recorded", "support_note:deep_marsh_ready"],
        "node_state_flags": ["deep_marsh_shelter_aid_received", "deep_marsh_support_ready"],
        "node_state_summary": "В тростниковом приюте уже держат более надёжную refuge-помощь благодаря готовой внешней поддержке.",
        "requires_any_group_node_state_flags": ["frontier_support_ready"],
    },
    {
        "node_id": "reed_shelter",
        "service_key": "shrine_aid",
        "service_id": "reed_shelter_shrine_aid",
        "service_kind": "shrine",
        "one_shot": True,
        "result_type": "lodging_received",
        "summary": "Попросить лучший болотный refuge-response после полной поддержки с базы.",
        "result_summary": "При полной поддержке с базы тростниковый приют даёт лучшую версию своей помощи: хороший сухой настил, не скупую травяную горечь и уверенный тихий advice на обратный ход через туман.",
        "discovered_notes": [
            "Полный support tier с базы делает болотный refuge ощутимо крепче: приют уже действует не на остатках, а с уверенностью, что дальний край не забыт."
        ],
        "applied_effects": ["lodging_received", "marsh_refuge_recorded", "support_note:deep_marsh_committed"],
        "node_state_flags": ["deep_marsh_shelter_aid_received", "deep_marsh_support_committed"],
        "node_state_summary": "В тростниковом приюте уже действует лучший refuge-support tier, дошедший с базы.",
        "requires_any_group_node_state_flags": ["frontier_support_committed"],
    },
    {
        "node_id": "waystation_yard",
        "service_key": "resupply",
        "service_id": "waystation_yard_resupply",
        "service_kind": "supplies",
        "one_shot": True,
        "result_type": "supplies_secured",
        "summary": "Получить дорожный набор и быструю помощь после проверки следа задержанного обоза.",
        "result_summary": "Постоялый двор принимает обратный рассказ о брошенной повозке, собирает для группы дорожный набор и отмечает, что помощь выдана уже после реальной проверки следа на тракте.",
        "discovered_notes": [
            "Возчики советуют не растягивать следующий выход: теперь ясно, где обоз потерял темп, а значит запас стоит тратить на уверенный дорожный ход, а не на долгий поиск."
        ],
        "applied_effects": ["supplies_secured:waystation_yard", "support_note:western_road_return"],
        "node_state_flags": ["western_road_waystation_aid_received"],
        "node_state_summary": "На постоялом дворе уже приняли рассказ о дорожной задержке и выдали группе дорожный набор.",
    },
    {
        "node_id": "waystation_yard",
        "service_key": "resupply",
        "service_id": "waystation_yard_resupply",
        "service_kind": "supplies",
        "one_shot": True,
        "result_type": "supplies_secured",
        "summary": "Получить дорожный набор, уже усиленный первым backing с базы.",
        "result_summary": "Постоялый двор работает спокойнее и надёжнее: с первой поддержкой с базы возчики держат лучший дорожный порядок и выдают набор не как редкую удачу, а как начало более устойчивой линии помощи на тракте.",
        "discovered_notes": [
            "На западном тракте уже знают, что лесной посёлок начал поддерживать дальние выходы, и двор охотнее держит собранный набор под тех, кто реально вернулся со следа."
        ],
        "applied_effects": ["supplies_secured:waystation_yard", "support_note:western_road_prepared"],
        "node_state_flags": ["western_road_waystation_aid_received", "western_road_support_prepared"],
        "node_state_summary": "На постоялом дворе уже чувствуют первый внешний backing с базы.",
        "requires_any_group_node_state_flags": ["frontier_support_prepared"],
    },
    {
        "node_id": "waystation_yard",
        "service_key": "resupply",
        "service_id": "waystation_yard_resupply",
        "service_kind": "supplies",
        "one_shot": True,
        "result_type": "supplies_secured",
        "summary": "Получить более надёжный дорожный набор при ready-stage поддержке.",
        "result_summary": "Когда база уже держит готовую линию поддержки, постоялый двор становится заметно dependable: запас готовят быстрее, дорожные пометки сходятся лучше, а сам yard feels like a working corridor node instead of a strained stopgap.",
        "discovered_notes": [
            "С ready-stage backing дорожный двор уже держит тракт не на одной привычке возчиков, а на более устойчивом support rhythm."
        ],
        "applied_effects": ["supplies_secured:waystation_yard", "support_note:western_road_ready"],
        "node_state_flags": ["western_road_waystation_aid_received", "western_road_support_ready"],
        "node_state_summary": "На постоялом дворе уже работает более надёжный road-support tier благодаря готовой базе.",
        "requires_any_group_node_state_flags": ["frontier_support_ready"],
    },
    {
        "node_id": "waystation_yard",
        "service_key": "resupply",
        "service_id": "waystation_yard_resupply",
        "service_kind": "supplies",
        "one_shot": True,
        "result_type": "supplies_secured",
        "summary": "Получить лучший дорожный набор после полной поддержки с базы.",
        "result_summary": "При полной поддержке с базы постоялый двор выдаёт лучшую версию своей дорожной помощи: dependable caravan notes, быстрый сбор и явное чувство, что западный тракт теперь встроен в общую линию frontier support, а не держится в одиночку.",
        "discovered_notes": [
            "Полный support tier с базы делает тракт ощутимо надёжнее: двор уже работает как настоящая внешняя опора, а не как случайный спасительный навес."
        ],
        "applied_effects": ["supplies_secured:waystation_yard", "support_note:western_road_committed"],
        "node_state_flags": ["western_road_waystation_aid_received", "western_road_support_committed"],
        "node_state_summary": "На постоялом дворе уже действует лучший дорожный support tier, дошедший с базы.",
        "requires_any_group_node_state_flags": ["frontier_support_committed"],
    },
)


STATIC_MAP_SERVICE_REQUIREMENTS: tuple[dict[str, Any], ...] = (
    {
        "node_id": "craft_town",
        "service_id": "craft_town_local_guidance",
        "requires_destination_event_id": "craft_town_arrival_notice",
        "requires_destination_event_result_type": "settlement_notice",
        "unlock_hint": "Сначала получить местную наводку при прибытии в городок.",
    },
    {
        "node_id": "chapel_village",
        "service_id": "chapel_village_shrine_aid",
        "return_visit_only": True,
        "unlock_hint": "Тихий кров при часовне предлагают охотнее тем, кто уже возвращался сюда.",
    },
    {
        "node_id": "forest_settlement",
        "service_id": "forest_settlement_resupply",
        "requires_destination_event_id": "forest_settlement_hunters_warning",
        "requires_destination_event_result_type": "settlement_notice",
        "min_visit_count": 2,
        "unlock_hint": "Полный лесной набор выдают только после первой охотничьей сводки и повторного захода в посёлок.",
    },
    {
        "node_id": "forest_settlement",
        "service_id": "forest_settlement_frontier_support",
        "requires_node_state_flag": "frontier_report_started",
        "unlock_hint": "Сначала свести хотя бы первую frontier-сводку по внешнему рубежу.",
    },
    {
        "node_id": "forest_settlement",
        "service_id": "forest_settlement_frontier_readiness",
        "requires_node_state_flag": "frontier_stabilization_started",
        "unlock_hint": "Сначала получить хотя бы первый подтверждённый результат полевой стабилизации frontier.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "service_id": "northwatch_quartermaster_resupply",
        "return_visit_only": True,
        "min_visit_count": 2,
        "unlock_hint": "Интендант открывает рубежный склад только тем, кто уже сходил на короткую вылазку по рубежу и вернулся с первой сводкой.",
    },
    {
        "node_id": "reed_shelter",
        "service_id": "reed_shelter_shrine_aid",
        "return_visit_only": True,
        "min_visit_count": 2,
        "unlock_hint": "Тростниковый приют открывает сухой настил только тем, кто уже сходил в сырой ход и вернулся до полной темноты.",
    },
    {
        "node_id": "waystation_yard",
        "service_id": "waystation_yard_resupply",
        "return_visit_only": True,
        "min_visit_count": 2,
        "unlock_hint": "Постоялый двор собирает полный дорожный набор только тем, кто уже сходил по следу задержанного обоза и вернулся с дороги.",
    },
)


STATIC_MAP_REGION_GATEWAYS: tuple[dict[str, Any], ...] = (
    {
        "gateway_id": "forest_settlement_northwatch",
        "source_node_id": "forest_settlement",
        "route_id": "forest_settlement->old_fortress_edge:move",
        "target_region_id": "northwatch_frontier",
        "target_region_label": "Северный рубеж",
        "target_anchor_node_id": "northwatch_outpost",
        "label": "Выход к северному рубежу",
        "requires_node_state_flag": "forest_supplies_secured",
        "unlock_hint": "Сначала собрать лесные припасы перед дальним выходом к северному рубежу.",
    },
    {
        "gateway_id": "northwatch_outpost_starter_frontier",
        "source_node_id": "northwatch_outpost",
        "route_id": "northwatch_outpost->northwatch_quartermaster:move",
        "target_region_id": "starter_frontier",
        "target_region_label": "Стартовое пограничье",
        "target_anchor_node_id": "forest_settlement",
        "label": "Тропа обратно к лесному посёлку",
        "unlock_hint": "Дозор держит обратную тропу открытой, пока погода не ломает северный подход.",
    },
    {
        "gateway_id": "northwatch_quartermaster_western_road",
        "source_node_id": "northwatch_quartermaster",
        "route_id": "northwatch_quartermaster->ash_pass:move",
        "target_region_id": "western_road",
        "target_region_label": "Западный тракт",
        "target_anchor_node_id": "waystation_yard",
        "label": "Боковая линия к западному тракту",
        "requires_all_group_node_state_flags": [
            "northwatch_directive_fulfilled",
            "western_road_directive_fulfilled",
        ],
        "unlock_hint": "Боковая frontier-линия между северным рубежом и трактом открывается только когда обе стороны реально выполнили своё stabilization work.",
    },
    {
        "gateway_id": "ash_pass_deep_marsh",
        "source_node_id": "ash_pass",
        "route_id": "northwatch_quartermaster->ash_pass:move",
        "target_region_id": "deep_marsh",
        "target_region_label": "Глубокие болота",
        "target_anchor_node_id": "reed_shelter",
        "label": "Боковая линия к тростниковому приюту",
        "requires_all_group_node_state_flags": [
            "northwatch_directive_fulfilled",
            "deep_marsh_directive_fulfilled",
        ],
        "unlock_hint": "Боковая watch-marsh линия держится только когда и северный рубеж, и болотный край подтвердили выполненную полевую стабилизацию.",
    },
    {
        "gateway_id": "fortress_gate_western_road",
        "source_node_id": "fortress_gate",
        "route_id": "start_trakt->fortress_gate:move",
        "target_region_id": "western_road",
        "target_region_label": "Западный тракт",
        "target_anchor_node_id": "western_road_watch",
        "label": "Выход на западный тракт",
        "requires_destination_event_id": "fortress_gate_watch_warning",
        "unlock_hint": "Сначала выслушать предупреждение дозора у ворот.",
    },
    {
        "gateway_id": "western_road_watch_starter_frontier",
        "source_node_id": "western_road_watch",
        "route_id": "western_road_watch->waystation_yard:move",
        "target_region_id": "starter_frontier",
        "target_region_label": "Стартовое пограничье",
        "target_anchor_node_id": "fortress_gate",
        "label": "Возврат к воротам крепости",
        "unlock_hint": "Пока тракт читается по первым дорожным меткам, обратный ход к воротам остаётся явным.",
    },
    {
        "gateway_id": "waystation_yard_northwatch",
        "source_node_id": "waystation_yard",
        "route_id": "waystation_yard->rutted_detour:move",
        "target_region_id": "northwatch_frontier",
        "target_region_label": "Северный рубеж",
        "target_anchor_node_id": "northwatch_quartermaster",
        "label": "Боковая линия к северному рубежу",
        "requires_all_group_node_state_flags": [
            "northwatch_directive_fulfilled",
            "western_road_directive_fulfilled",
        ],
        "unlock_hint": "Боковой frontier-проход к северному рубежу держится только после того, как и двор, и рубеж подтвердили выполненную стабилизацию.",
    },
    {
        "gateway_id": "waystation_yard_deep_marsh",
        "source_node_id": "waystation_yard",
        "route_id": "waystation_yard->rutted_detour:move",
        "target_region_id": "deep_marsh",
        "target_region_label": "Глубокие болота",
        "target_anchor_node_id": "blackwater_run",
        "label": "Боковая линия к чёрной протоке",
        "requires_all_group_node_state_flags": [
            "deep_marsh_directive_fulfilled",
            "western_road_directive_fulfilled",
        ],
        "unlock_hint": "Боковой marsh-road проход держится только когда и болотная линия, и тракт подтвердили выполненную полевую стабилизацию.",
    },
    {
        "gateway_id": "marsh_edge_deep_marsh",
        "source_node_id": "marsh_edge",
        "route_id": "ruined_settlement->marsh_edge:move",
        "target_region_id": "deep_marsh",
        "target_region_label": "Глубокие болота",
        "target_anchor_node_id": "deep_marsh_threshold",
        "label": "Тропа в глубокие болота",
        "requires_min_visit_count": 2,
        "unlock_hint": "К болотной кромке нужно вернуться хотя бы ещё раз, чтобы закрепить дальний выход.",
    },
    {
        "gateway_id": "deep_marsh_threshold_starter_frontier",
        "source_node_id": "deep_marsh_threshold",
        "route_id": "deep_marsh_threshold->reed_shelter:move",
        "target_region_id": "starter_frontier",
        "target_region_label": "Стартовое пограничье",
        "target_anchor_node_id": "marsh_edge",
        "label": "Обратный ход к болотной кромке",
        "unlock_hint": "Пока держатся первые сухие кочки, обратный ход к кромке болот остаётся различимым.",
    },
    {
        "gateway_id": "blackwater_run_western_road",
        "source_node_id": "blackwater_run",
        "route_id": "blackwater_run->sunken_ferry:move",
        "target_region_id": "western_road",
        "target_region_label": "Западный тракт",
        "target_anchor_node_id": "waystation_yard",
        "label": "Боковая линия к западному тракту",
        "requires_all_group_node_state_flags": [
            "deep_marsh_directive_fulfilled",
            "western_road_directive_fulfilled",
        ],
        "unlock_hint": "Тихий боковой ход к тракту удерживается только после того, как и болотная линия, и дорожный двор подтвердили выполненную стабилизацию.",
    },
    {
        "gateway_id": "reed_shelter_northwatch",
        "source_node_id": "reed_shelter",
        "route_id": "deep_marsh_threshold->reed_shelter:move",
        "target_region_id": "northwatch_frontier",
        "target_region_label": "Северный рубеж",
        "target_anchor_node_id": "ash_pass",
        "label": "Боковая линия к северному рубежу",
        "requires_all_group_node_state_flags": [
            "northwatch_directive_fulfilled",
            "deep_marsh_directive_fulfilled",
        ],
        "unlock_hint": "Боковой marsh-watch проход держится только после того, как и рубеж, и болотная линия подтвердили выполненную стабилизацию.",
    },
    {
        "gateway_id": "forgotten_shrine_sunken_reaches",
        "source_node_id": "forgotten_shrine",
        "route_id": "marsh_edge->forgotten_shrine:move",
        "target_region_id": "sunken_reaches",
        "target_region_label": "Затонувшие низины",
        "label": "Затопленная тропа за святилищем",
        "future_stub": True,
    },
)

STATIC_MAP_REGION_IDENTITIES: tuple[dict[str, Any], ...] = (
    {
        "region_id": "starter_frontier",
        "region_label": "Стартовое пограничье",
        "node_ids": (
            "start_trakt",
            "eastern_bank",
            "craft_town",
            "forest_road",
            "road_hamlet",
            "chapel_village",
            "forest_settlement",
            "ruined_settlement",
            "marsh_edge",
            "fortress_gate",
            "watchtower",
            "old_fortress_edge",
            "forgotten_shrine",
            "mine_entrance",
        ),
    },
    {
        "region_id": "northwatch_frontier",
        "region_label": "Северный рубеж",
        "node_ids": (
            "northwatch_outpost",
            "northwatch_quartermaster",
            "northwatch_palisade",
            "ash_pass",
            "broken_redoubt",
        ),
    },
    {
        "region_id": "western_road",
        "region_label": "Западный тракт",
        "node_ids": (
            "western_road_watch",
            "waystation_yard",
            "mile_marker_arch",
            "rutted_detour",
            "broken_waycart",
        ),
    },
    {
        "region_id": "deep_marsh",
        "region_label": "Глубокие болота",
        "node_ids": (
            "deep_marsh_threshold",
            "reed_shelter",
            "drowned_waystone",
            "blackwater_run",
            "sunken_ferry",
        ),
    },
)

STATIC_MAP_REGION_ONBOARDING: tuple[dict[str, Any], ...] = (
    {
        "region_id": "starter_frontier",
        "region_label": "Стартовое пограничье",
        "anchor_node_id": "start_trakt",
        "starter_reveal_node_ids": ("craft_town", "fortress_gate"),
        "starter_reveal_route_ids": (
            "start_trakt->craft_town:move",
            "start_trakt->fortress_gate:move",
        ),
        "intel_title": "Опорные пути стартового пограничья",
        "intel_summary": "При первом входе в стартовое пограничье группа быстро закрепляет основные безопасные выходы от стартового тракта.",
        "onboarding_note": "Стартовый тракт сразу открывает ближайшие безопасные опорные точки региона.",
    },
    {
        "region_id": "northwatch_frontier",
        "region_label": "Северный рубеж",
        "anchor_node_id": "northwatch_outpost",
        "starter_reveal_node_ids": ("northwatch_quartermaster", "northwatch_palisade", "ash_pass"),
        "starter_reveal_route_ids": (
            "northwatch_outpost->northwatch_quartermaster:move",
            "northwatch_quartermaster->northwatch_outpost:move",
            "northwatch_outpost->northwatch_palisade:move",
            "northwatch_palisade->northwatch_outpost:move",
            "northwatch_outpost->ash_pass:move",
            "ash_pass->northwatch_outpost:move",
        ),
        "intel_title": "Северный рубеж раскрывает первую линию дозора",
        "intel_summary": "При входе на северный рубеж группа сразу закрепляет пост, интендантский двор, обзорную палисаду и опасный зольный проход.",
        "onboarding_note": "Северный рубеж больше не пустой якорь: пост сразу раскрывает рабочий дозорный узел и первую опасную frontier-ветку.",
    },
    {
        "region_id": "western_road",
        "region_label": "Западный тракт",
        "anchor_node_id": "western_road_watch",
        "starter_reveal_node_ids": ("waystation_yard", "mile_marker_arch", "rutted_detour"),
        "starter_reveal_route_ids": (
            "western_road_watch->waystation_yard:move",
            "waystation_yard->western_road_watch:move",
            "western_road_watch->mile_marker_arch:move",
            "mile_marker_arch->western_road_watch:move",
            "western_road_watch->rutted_detour:move",
            "rutted_detour->western_road_watch:move",
        ),
        "intel_title": "Первые дорожные опоры западного тракта",
        "intel_summary": "При входе на western_road группа сразу закрепляет двор у тракта, верстовую арку и разбитый объезд, где скапливаются свежие следы недавнего прохода.",
        "onboarding_note": "Западный тракт больше не anchor-only выход: регион сразу раскрывает roadside support-точку, дорожный marker и рискованный объезд с живым следом.",
    },
    {
        "region_id": "deep_marsh",
        "region_label": "Глубокие болота",
        "anchor_node_id": "deep_marsh_threshold",
        "starter_reveal_node_ids": ("reed_shelter", "drowned_waystone", "blackwater_run"),
        "starter_reveal_route_ids": (
            "deep_marsh_threshold->reed_shelter:move",
            "reed_shelter->deep_marsh_threshold:move",
            "deep_marsh_threshold->drowned_waystone:move",
            "drowned_waystone->deep_marsh_threshold:move",
            "deep_marsh_threshold->blackwater_run:move",
            "blackwater_run->deep_marsh_threshold:move",
        ),
        "intel_title": "Первые ориентиры глубоких болот",
        "intel_summary": "При входе в deep_marsh группа сразу закрепляет тростниковый приют, утопленный путевой камень и рискованный ход к чёрной протоке.",
        "onboarding_note": "Глубокие болота больше не anchor-only порог: регион сразу раскрывает refuge, waymark-landmark и тёмный болотный ход.",
    },
)


def _normalized_text(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalized_text_list(values: Any) -> list[str]:
    if not isinstance(values, (list, tuple, set)):
        return []
    return [
        str(value).strip().lower()
        for value in values
        if str(value or "").strip()
    ]


def _matches_group_state_requirement_variant(
    item: dict[str, Any],
    *,
    state_flags: list[str] | set[str] | None = None,
    group_state_flags: list[str] | set[str] | None = None,
    region_link_ids: list[str] | set[str] | None = None,
) -> bool:
    local_flags = {
        str(flag).strip().lower()
        for flag in (state_flags or [])
        if str(flag or "").strip()
    }
    global_flags = {
        str(flag).strip().lower()
        for flag in (group_state_flags or [])
        if str(flag or "").strip()
    }
    available_region_link_ids = {
        str(link_id).strip().lower()
        for link_id in (region_link_ids or [])
        if str(link_id or "").strip()
    }
    required_state_flags = set(_normalized_text_list(item.get("required_state_flags")))
    if required_state_flags and not required_state_flags.issubset(local_flags):
        return False
    requires_any_group_flags = set(_normalized_text_list(item.get("requires_any_group_node_state_flags")))
    if requires_any_group_flags and not (requires_any_group_flags & global_flags):
        return False
    requires_all_group_flags = set(_normalized_text_list(item.get("requires_all_group_node_state_flags")))
    if requires_all_group_flags and not requires_all_group_flags.issubset(global_flags):
        return False
    required_min_group_flags = max(0, int(item.get("requires_min_group_node_state_flags") or 0))
    if required_min_group_flags > 0:
        group_flag_pool = set(_normalized_text_list(item.get("group_node_state_flag_pool")))
        if len(group_flag_pool & global_flags) < required_min_group_flags:
            return False
    requires_any_region_link_ids = set(_normalized_text_list(item.get("requires_any_region_link_ids")))
    if requires_any_region_link_ids and not (requires_any_region_link_ids & available_region_link_ids):
        return False
    requires_all_region_link_ids = set(_normalized_text_list(item.get("requires_all_region_link_ids")))
    if requires_all_region_link_ids and not requires_all_region_link_ids.issubset(available_region_link_ids):
        return False
    requires_min_region_link_count = max(0, int(item.get("requires_min_region_link_count") or 0))
    if requires_min_region_link_count > 0:
        region_link_id_pool = set(_normalized_text_list(item.get("region_link_id_pool")))
        if len(region_link_id_pool & available_region_link_ids) < requires_min_region_link_count:
            return False
    return True


def _group_state_requirement_specificity(item: dict[str, Any]) -> tuple[int, int, int, int, int, int, int]:
    return (
        max(0, int(item.get("requires_min_region_link_count") or 0)),
        len(_normalized_text_list(item.get("requires_all_region_link_ids"))),
        len(_normalized_text_list(item.get("requires_any_region_link_ids"))),
        max(0, int(item.get("requires_min_group_node_state_flags") or 0)),
        len(_normalized_text_list(item.get("requires_all_group_node_state_flags"))),
        len(_normalized_text_list(item.get("requires_any_group_node_state_flags"))),
        len(_normalized_text_list(item.get("required_state_flags"))),
    )


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
            metadata["settlement_kind"] = "village" if node_id in {"chapel_village", "forest_settlement", "northwatch_outpost", "northwatch_quartermaster", "reed_shelter"} else "hamlet"
            metadata["environment_hint"] = "marsh" if node_id == "reed_shelter" else ("wooded" if node_id in {"forest_road", "forest_settlement"} else "frontier")
            metadata["safe_rest_hint"] = node_id in {"road_hamlet", "chapel_village", "forest_settlement", "northwatch_outpost", "northwatch_quartermaster", "reed_shelter"}
        elif zone_band == "danger":
            metadata["settlement_kind"] = "ruins" if node_id == "ruined_settlement" else "wilds"
            metadata["environment_hint"] = "marsh" if node_id in {"marsh_edge", "deep_marsh_threshold", "blackwater_run"} else "ruined_frontier"
            metadata["safe_rest_hint"] = False
    elif node_type == "landmark":
        metadata["poi_kind"] = "fortified" if node_id in {"fortress_gate", "old_fortress_edge", "watchtower", "northwatch_palisade", "broken_redoubt"} else "shrine"
        metadata["environment_hint"] = "fortified" if node_id == "fortress_gate" else ("marsh" if node_id in {"forgotten_shrine", "drowned_waystone", "sunken_ferry"} else "frontier")
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
    state_flags: list[str] | set[str] | None = None,
    group_state_flags: list[str] | set[str] | None = None,
    region_link_ids: list[str] | set[str] | None = None,
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
        reveal_node_ids = [
            str(node_ref).strip()
            for node_ref in (item.get("reveal_node_ids") or [])
            if str(node_ref or "").strip() and get_static_node(str(node_ref)) is not None
        ]
        if reveal_node_ids:
            effect["reveal_node_ids"] = reveal_node_ids
        route_access_updates: list[dict[str, Any]] = []
        for route_update in (item.get("route_access_updates") or []):
            if not isinstance(route_update, dict):
                continue
            route_id = str(route_update.get("route_id") or "").strip().lower()
            access_state = str(route_update.get("access_state") or "").strip().lower()
            if not route_id or access_state not in {"open", "cleared", "blocked"}:
                continue
            normalized_update: dict[str, Any] = {
                "route_id": route_id,
                "access_state": access_state,
            }
            summary = str(route_update.get("summary") or "").strip()
            if summary:
                normalized_update["summary"] = summary
            block_reason = str(route_update.get("block_reason") or "").strip()
            if block_reason:
                normalized_update["block_reason"] = block_reason
            route_access_updates.append(normalized_update)
        if route_access_updates:
            effect["route_access_updates"] = route_access_updates
        requires_any_group_node_state_flags = _normalized_text_list(item.get("requires_any_group_node_state_flags"))
        if requires_any_group_node_state_flags:
            effect["requires_any_group_node_state_flags"] = requires_any_group_node_state_flags
        requires_all_group_node_state_flags = _normalized_text_list(item.get("requires_all_group_node_state_flags"))
        if requires_all_group_node_state_flags:
            effect["requires_all_group_node_state_flags"] = requires_all_group_node_state_flags
        requires_min_group_node_state_flags = int(item.get("requires_min_group_node_state_flags") or 0)
        if requires_min_group_node_state_flags > 0:
            effect["requires_min_group_node_state_flags"] = requires_min_group_node_state_flags
        group_node_state_flag_pool = _normalized_text_list(item.get("group_node_state_flag_pool"))
        if group_node_state_flag_pool:
            effect["group_node_state_flag_pool"] = group_node_state_flag_pool
        requires_any_region_link_ids = _normalized_text_list(item.get("requires_any_region_link_ids"))
        if requires_any_region_link_ids:
            effect["requires_any_region_link_ids"] = requires_any_region_link_ids
        requires_all_region_link_ids = _normalized_text_list(item.get("requires_all_region_link_ids"))
        if requires_all_region_link_ids:
            effect["requires_all_region_link_ids"] = requires_all_region_link_ids
        requires_min_region_link_count = int(item.get("requires_min_region_link_count") or 0)
        if requires_min_region_link_count > 0:
            effect["requires_min_region_link_count"] = requires_min_region_link_count
        region_link_id_pool = _normalized_text_list(item.get("region_link_id_pool"))
        if region_link_id_pool:
            effect["region_link_id_pool"] = region_link_id_pool
        if effect["action_id"] and effect["label"]:
            effects.append(effect)
    if state_flags is None and group_state_flags is None and region_link_ids is None:
        return effects
    best_effects: dict[str, dict[str, Any]] = {}
    for effect in effects:
        action_id = str(effect.get("action_id") or "").strip().lower()
        if not action_id:
            continue
        if not _matches_group_state_requirement_variant(
            effect,
            state_flags=state_flags,
            group_state_flags=group_state_flags,
            region_link_ids=region_link_ids,
        ):
            continue
        current_best = best_effects.get(action_id)
        if not current_best or _group_state_requirement_specificity(effect) >= _group_state_requirement_specificity(current_best):
            best_effects[action_id] = effect
    return [dict(best_effects[action_id]) for action_id in sorted(best_effects.keys())]


def get_static_node_context_action_requirements(
    *,
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    resolved_node_id = _normalized_text(node_id)
    if not resolved_node_id and isinstance(current_map_position, dict):
        resolved_node_id = _normalized_text(current_map_position.get("node_id"))
    if not resolved_node_id:
        return []
    requirements: list[dict[str, Any]] = []
    for item in STATIC_MAP_CONTEXT_ACTION_REQUIREMENTS:
        if _normalized_text(item.get("node_id")) != resolved_node_id:
            continue
        action_id = _normalized_text(item.get("action_id"))
        if not action_id:
            continue
        requirement: dict[str, Any] = {
            "node_id": resolved_node_id,
            "action_id": action_id,
            "unlock_hint": str(item.get("unlock_hint") or "").strip(),
        }
        requires_node_state_flag = _normalized_text(item.get("requires_node_state_flag"))
        if requires_node_state_flag:
            requirement["requires_node_state_flag"] = requires_node_state_flag
        requires_destination_event_id = _normalized_text(item.get("requires_destination_event_id"))
        if requires_destination_event_id:
            requirement["requires_destination_event_id"] = requires_destination_event_id
        requires_destination_event_result_type = _normalized_text(item.get("requires_destination_event_result_type"))
        if requires_destination_event_result_type:
            requirement["requires_destination_event_result_type"] = requires_destination_event_result_type
        requires_any_group_node_state_flags = _normalized_text_list(item.get("requires_any_group_node_state_flags"))
        if requires_any_group_node_state_flags:
            requirement["requires_any_group_node_state_flags"] = requires_any_group_node_state_flags
        requires_all_group_node_state_flags = _normalized_text_list(item.get("requires_all_group_node_state_flags"))
        if requires_all_group_node_state_flags:
            requirement["requires_all_group_node_state_flags"] = requires_all_group_node_state_flags
        requires_min_group_node_state_flags = int(item.get("requires_min_group_node_state_flags") or 0)
        if requires_min_group_node_state_flags > 0:
            requirement["requires_min_group_node_state_flags"] = requires_min_group_node_state_flags
        group_node_state_flag_pool = _normalized_text_list(item.get("group_node_state_flag_pool"))
        if group_node_state_flag_pool:
            requirement["group_node_state_flag_pool"] = group_node_state_flag_pool
        requires_any_region_link_ids = _normalized_text_list(item.get("requires_any_region_link_ids"))
        if requires_any_region_link_ids:
            requirement["requires_any_region_link_ids"] = requires_any_region_link_ids
        requires_all_region_link_ids = _normalized_text_list(item.get("requires_all_region_link_ids"))
        if requires_all_region_link_ids:
            requirement["requires_all_region_link_ids"] = requires_all_region_link_ids
        requires_min_region_link_count = int(item.get("requires_min_region_link_count") or 0)
        if requires_min_region_link_count > 0:
            requirement["requires_min_region_link_count"] = requires_min_region_link_count
        region_link_id_pool = _normalized_text_list(item.get("region_link_id_pool"))
        if region_link_id_pool:
            requirement["region_link_id_pool"] = region_link_id_pool
        if bool(item.get("first_visit_only")):
            requirement["first_visit_only"] = True
        if bool(item.get("return_visit_only")):
            requirement["return_visit_only"] = True
        min_visit_count = int(item.get("min_visit_count") or 0)
        if min_visit_count > 0:
            requirement["min_visit_count"] = min_visit_count
        requirements.append(requirement)
    return requirements


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
    state_flags: list[str] | set[str] | None = None,
    group_state_flags: list[str] | set[str] | None = None,
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
        required_state_flags = _normalized_text_list(item.get("required_state_flags"))
        if required_state_flags:
            effect["required_state_flags"] = required_state_flags
        requires_any_group_node_state_flags = _normalized_text_list(item.get("requires_any_group_node_state_flags"))
        if requires_any_group_node_state_flags:
            effect["requires_any_group_node_state_flags"] = requires_any_group_node_state_flags
        requires_all_group_node_state_flags = _normalized_text_list(item.get("requires_all_group_node_state_flags"))
        if requires_all_group_node_state_flags:
            effect["requires_all_group_node_state_flags"] = requires_all_group_node_state_flags
        requires_min_group_node_state_flags = int(item.get("requires_min_group_node_state_flags") or 0)
        if requires_min_group_node_state_flags > 0:
            effect["requires_min_group_node_state_flags"] = requires_min_group_node_state_flags
        group_node_state_flag_pool = _normalized_text_list(item.get("group_node_state_flag_pool"))
        if group_node_state_flag_pool:
            effect["group_node_state_flag_pool"] = group_node_state_flag_pool
        if service_key and service_id:
            effects.append(effect)
    if state_flags is None and group_state_flags is None:
        return effects
    best_effects: dict[str, dict[str, Any]] = {}
    for effect in effects:
        service_ref = str(effect.get("service_id") or effect.get("service_key") or "").strip().lower()
        if not service_ref:
            continue
        if not _matches_group_state_requirement_variant(
            effect,
            state_flags=state_flags,
            group_state_flags=group_state_flags,
        ):
            continue
        current_best = best_effects.get(service_ref)
        if not current_best or _group_state_requirement_specificity(effect) >= _group_state_requirement_specificity(current_best):
            best_effects[service_ref] = effect
    return [dict(best_effects[service_ref]) for service_ref in sorted(best_effects.keys())]


def get_static_node_service_requirements(
    *,
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    resolved_node_id = _normalized_text(node_id)
    if not resolved_node_id and isinstance(current_map_position, dict):
        resolved_node_id = _normalized_text(current_map_position.get("node_id"))
    if not resolved_node_id:
        return []
    requirements: list[dict[str, Any]] = []
    for item in STATIC_MAP_SERVICE_REQUIREMENTS:
        if _normalized_text(item.get("node_id")) != resolved_node_id:
            continue
        service_id = _normalized_text(item.get("service_id"))
        service_key = _normalized_text(item.get("service_key"))
        if not service_id and not service_key:
            continue
        requirement: dict[str, Any] = {
            "node_id": resolved_node_id,
            "service_id": service_id,
            "service_key": service_key,
            "unlock_hint": str(item.get("unlock_hint") or "").strip(),
        }
        requires_node_state_flag = _normalized_text(item.get("requires_node_state_flag"))
        if requires_node_state_flag:
            requirement["requires_node_state_flag"] = requires_node_state_flag
        requires_destination_event_id = _normalized_text(item.get("requires_destination_event_id"))
        if requires_destination_event_id:
            requirement["requires_destination_event_id"] = requires_destination_event_id
        requires_destination_event_result_type = _normalized_text(item.get("requires_destination_event_result_type"))
        if requires_destination_event_result_type:
            requirement["requires_destination_event_result_type"] = requires_destination_event_result_type
        requires_any_group_node_state_flags = _normalized_text_list(item.get("requires_any_group_node_state_flags"))
        if requires_any_group_node_state_flags:
            requirement["requires_any_group_node_state_flags"] = requires_any_group_node_state_flags
        requires_all_group_node_state_flags = _normalized_text_list(item.get("requires_all_group_node_state_flags"))
        if requires_all_group_node_state_flags:
            requirement["requires_all_group_node_state_flags"] = requires_all_group_node_state_flags
        requires_min_group_node_state_flags = int(item.get("requires_min_group_node_state_flags") or 0)
        if requires_min_group_node_state_flags > 0:
            requirement["requires_min_group_node_state_flags"] = requires_min_group_node_state_flags
        group_node_state_flag_pool = _normalized_text_list(item.get("group_node_state_flag_pool"))
        if group_node_state_flag_pool:
            requirement["group_node_state_flag_pool"] = group_node_state_flag_pool
        if bool(item.get("first_visit_only")):
            requirement["first_visit_only"] = True
        if bool(item.get("return_visit_only")):
            requirement["return_visit_only"] = True
        min_visit_count = int(item.get("min_visit_count") or 0)
        if min_visit_count > 0:
            requirement["min_visit_count"] = min_visit_count
        requirements.append(requirement)
    return requirements


def get_static_region_gateways(
    *,
    region_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    resolved_region_id = _normalized_text(region_id)
    if not resolved_region_id and isinstance(current_map_position, dict):
        resolved_region_id = _normalized_text(current_map_position.get("map_level"))
    if not resolved_region_id:
        resolved_region_id = "region"
    if resolved_region_id != "region":
        return []
    gateways: list[dict[str, Any]] = []
    for item in STATIC_MAP_REGION_GATEWAYS:
        source_node_id = _normalized_text(item.get("source_node_id"))
        gateway_id = _normalized_text(item.get("gateway_id"))
        target_region_id = _normalized_text(item.get("target_region_id"))
        if not source_node_id or not gateway_id or not target_region_id:
            continue
        gateway: dict[str, Any] = {
            "gateway_id": gateway_id,
            "source_node_id": source_node_id,
            "route_id": _normalized_text(item.get("route_id")),
            "target_region_id": target_region_id,
            "target_region_label": str(item.get("target_region_label") or target_region_id).strip(),
            "target_anchor_node_id": _normalized_text(item.get("target_anchor_node_id")),
            "label": str(item.get("label") or gateway_id).strip(),
            "future_stub": bool(item.get("future_stub")),
            "unlock_hint": str(item.get("unlock_hint") or "").strip(),
        }
        requires_node_state_flag = _normalized_text(item.get("requires_node_state_flag"))
        if requires_node_state_flag:
            gateway["requires_node_state_flag"] = requires_node_state_flag
        requires_destination_event_id = _normalized_text(item.get("requires_destination_event_id"))
        if requires_destination_event_id:
            gateway["requires_destination_event_id"] = requires_destination_event_id
        requires_destination_event_result_type = _normalized_text(item.get("requires_destination_event_result_type"))
        if requires_destination_event_result_type:
            gateway["requires_destination_event_result_type"] = requires_destination_event_result_type
        requires_any_group_node_state_flags = _normalized_text_list(item.get("requires_any_group_node_state_flags"))
        if requires_any_group_node_state_flags:
            gateway["requires_any_group_node_state_flags"] = requires_any_group_node_state_flags
        requires_all_group_node_state_flags = _normalized_text_list(item.get("requires_all_group_node_state_flags"))
        if requires_all_group_node_state_flags:
            gateway["requires_all_group_node_state_flags"] = requires_all_group_node_state_flags
        min_visit_count = int(item.get("requires_min_visit_count") or item.get("min_visit_count") or 0)
        if min_visit_count > 0:
            gateway["requires_min_visit_count"] = min_visit_count
        gateways.append(gateway)
    return gateways


def get_static_region_identity(
    *,
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    resolved_node_id = _normalized_text(node_id)
    if not resolved_node_id and isinstance(current_map_position, dict):
        resolved_node_id = _normalized_text(current_map_position.get("node_id"))
    if not resolved_node_id:
        return None
    for item in STATIC_MAP_REGION_IDENTITIES:
        node_ids = {
            _normalized_text(candidate)
            for candidate in (item.get("node_ids") or [])
            if _normalized_text(candidate)
        }
        if resolved_node_id not in node_ids:
            continue
        region_id = _normalized_text(item.get("region_id"))
        region_label = str(item.get("region_label") or region_id).strip()
        if not region_id or not region_label:
            continue
        return {
            "region_id": region_id,
            "region_label": region_label,
            "node_ids": sorted(node_ids),
        }
    return None


def get_static_region_onboarding(region_id: str | None = None) -> dict[str, Any] | None:
    resolved_region_id = _normalized_text(region_id)
    if not resolved_region_id:
        return None
    for item in STATIC_MAP_REGION_ONBOARDING:
        if _normalized_text(item.get("region_id")) != resolved_region_id:
            continue
        return {
            "region_id": resolved_region_id,
            "region_label": str(item.get("region_label") or resolved_region_id).strip(),
            "anchor_node_id": _normalized_text(item.get("anchor_node_id")),
            "starter_reveal_node_ids": [
                str(node_id).strip()
                for node_id in (item.get("starter_reveal_node_ids") or [])
                if str(node_id or "").strip() and get_static_node(str(node_id)) is not None
            ],
            "starter_reveal_route_ids": [
                str(route_id).strip()
                for route_id in (item.get("starter_reveal_route_ids") or [])
                if str(route_id or "").strip()
            ],
            "intel_title": str(item.get("intel_title") or "").strip(),
            "intel_summary": str(item.get("intel_summary") or "").strip(),
            "onboarding_note": str(item.get("onboarding_note") or "").strip(),
        }
    return None


def get_static_region_anchor_onboarding(anchor_node_id: str | None = None) -> dict[str, Any] | None:
    resolved_anchor_node_id = _normalized_text(anchor_node_id)
    if not resolved_anchor_node_id:
        return None
    for item in STATIC_MAP_REGION_ONBOARDING:
        if _normalized_text(item.get("anchor_node_id")) != resolved_anchor_node_id:
            continue
        return get_static_region_onboarding(_normalized_text(item.get("region_id")))
    return None


def get_static_node_region_gateways(
    node_id: str | None = None,
    current_map_position: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    resolved_node_id = _normalized_text(node_id)
    if not resolved_node_id and isinstance(current_map_position, dict):
        resolved_node_id = _normalized_text(current_map_position.get("node_id"))
    if not resolved_node_id:
        return []
    gateways: list[dict[str, Any]] = []
    for item in get_static_region_gateways(current_map_position=current_map_position):
        if _normalized_text(item.get("source_node_id")) == resolved_node_id:
            gateways.append(dict(item))
    return gateways


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
        "frontier_support": {
            "label": "Поддержка рубежа",
            "service_type": "support",
            "summary": "Здесь можно получить практическую подготовку под следующий выход на внешний рубеж.",
        },
        "frontier_readiness": {
            "label": "Готовность рубежа",
            "service_type": "support",
            "summary": "Здесь можно получить домашнюю readiness-подготовку, выросшую из подтверждённой стабилизации frontier.",
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
        "frontier_support": "Посёлок собирает практическую рубежную поддержку под следующий внешний выход.",
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
