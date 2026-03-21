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
        "node_id": "broken_redoubt",
        "state_flag": "northwatch_redoubt_trace_found",
        "context_note": "У редута уже замечены свежие следы недавней рубежной тревоги и брошенного снабженческого ящика.",
        "detail_note": "Под разбитой кладкой нашли следы торопливой стоянки и обрывки складской метки, которые уже нельзя принять за старый мусор.",
    },
    {
        "node_id": "northwatch_quartermaster",
        "state_flag": "northwatch_redoubt_return_logged",
        "context_note": "Во дворе уже приняли обратный доклад с редута, и интендант смотрит на группу как на тех, кто сходил туда не зря.",
        "detail_note": "На столе при складе лежит свежая пометка о возвращении группы с редута, и разговор во дворе идёт уже не о догадках, а о подтверждённой тревоге.",
        "service_note": "После обратного доклада склад уже реагирует на группу как на проверенный патрульный состав, а не как на случайных путников.",
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
        "node_id": "broken_waycart",
        "state_flag": "western_road_wagon_trace_found",
        "context_note": "У брошенной повозки уже нашли свежий след дорожной задержки и спешной перегрузки.",
        "detail_note": "У сломанной оси уже отмечены свежие ремни, следы переноски груза и короткая стоянка, после которой обоз ушёл дальше налегке.",
    },
    {
        "node_id": "waystation_yard",
        "state_flag": "western_road_waystation_aid_received",
        "context_note": "Во дворе уже приняли обратный рассказ о задержке на объезде и выдали группе дорожную поддержку как знакомому составу.",
        "detail_note": "Под навесом ещё видны следы недавно выданного дорожного набора после рассказа о брошенной повозке и разбитом объезде.",
        "service_note": "После обратного рассказа двор уже реагирует на группу как на тех, кто реально сходил по следу обоза, а не просто просит помощь с дороги.",
    },
    {
        "node_id": "sunken_ferry",
        "state_flag": "deep_marsh_ferry_trace_found",
        "context_note": "У затонувшей переправы уже замечали свежие следы недавней остановки и брошенный болотный шнур.",
        "detail_note": "На сваях у переправы уже отмечали не только старую труху, но и свежий след недавнего болотного хода.",
    },
    {
        "node_id": "reed_shelter",
        "state_flag": "deep_marsh_shelter_aid_received",
        "context_note": "В тростниковом приюте уже дали группе сухой кров и короткую болотную поддержку после возвращения из сырого хода.",
        "detail_note": "Под навесом ещё видны следы недавно выданного сухого места и короткой помощи именно для этой группы.",
        "service_note": "Приют уже однажды дал этой группе тихий кров после болотного выхода и теперь скорее подтверждает знакомую помощь, чем впервые открывается.",
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
