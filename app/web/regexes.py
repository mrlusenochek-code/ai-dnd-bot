import re

INNATE_SPELL_KEY_PATTERNS: dict[str, re.Pattern[str]] = {
    "levitate": re.compile(r"левитац|levitate", re.IGNORECASE),
    "passwall": re.compile(r"проход.*сквозь.*кам|passwall", re.IGNORECASE),
    "produce_flame": re.compile(r"создани[еия]\s+огня|produce\s+flame", re.IGNORECASE),
    "burning_hands": re.compile(r"горящ(?:ие|их)\s+руки|burning\s+hands", re.IGNORECASE),
    "shape_water": re.compile(r"формирован(?:ие|ия)\s+воды|shape\s+water", re.IGNORECASE),
    "create_or_destroy_water": re.compile(
        r"создани(?:е|я).*(?:уничтожени(?:е|я)).*воды|create.*destroy.*water",
        re.IGNORECASE,
    ),
    "minor_illusion": re.compile(r"мала[яй]\s+иллюз\w*|minor\s+illusion", re.IGNORECASE),
    "dancing_lights": re.compile(r"танцующ[а-яё]*\s+огн[а-яё]*|dancing\s+lights", re.IGNORECASE),
    "faerie_fire": re.compile(r"волшебн[а-яё]*\s+ог(?:н|он)[а-яё]*|faerie\s+fire", re.IGNORECASE),
    "detect_magic": re.compile(r"обнаружени[ея]\s+магии|detect\s+magic", re.IGNORECASE),
    "disguise_self": re.compile(r"маскировк\w*|disguise\s+self", re.IGNORECASE),
    "hex": re.compile(r"сглаз\w*|\bhex\b", re.IGNORECASE),
    "druidcraft": re.compile(r"искусств(?:о|а)\s+друид\w*|druidcraft", re.IGNORECASE),
    "enlarge_reduce": re.compile(
        r"увеличени[ея]\s*/?\s*уменьшени[ея]|enlarge\s*/?\s*reduce|enlarge\s+reduce",
        re.IGNORECASE,
    ),
    "shield": re.compile(r"(?:заклинани[ея]\s+)?щит\b|\bshield\b", re.IGNORECASE),
    "detect_thoughts": re.compile(
        r"обнаружени[ея]\s+мысл\w*|чтени[ея]\s+мысл\w*|detect\s+thoughts",
        re.IGNORECASE,
    ),
    "jump": re.compile(r"прыж\w*|\bjump\b", re.IGNORECASE),
    "misty_step": re.compile(r"туманн\w+\s+шаг\w*|misty\s+step", re.IGNORECASE),
    "thaumaturgy": re.compile(r"тауматург\w*|thaumaturgy", re.IGNORECASE),
    "hellish_rebuke": re.compile(r"адск\w*\s+(?:возмезди\w*|отпор\w*)|hellish\s+rebuke", re.IGNORECASE),
    "darkness": re.compile(
        r"(?:каст[а-яё]*|накладыва[а-яё]*|использу[а-яё]*|применя[а-яё]*)(?:\s+\S+){0,4}\s+\bтьм[а-яё]*\b|\bdarkness\b",
        re.IGNORECASE,
    ),
}


INV_MACHINE_LINE_RE = re.compile(
    r"^\s*(?:\(\s*)?@@(?P<cmd>INV_ADD|INV_REMOVE|INV_TRANSFER|EQUIP|UNEQUIP)\s*\((?P<args>.*)\)\s*(?:\))?\s*$",
    re.IGNORECASE,
)
ZONE_SET_MACHINE_LINE_RE = re.compile(r"^\s*(?:\(\s*)?@@ZONE_SET\s*\((?P<args>.*?)\)\s*(?:\))?\s*$", re.IGNORECASE)
SHAPECHANGER_SHIFT_RE = re.compile(
    r"(превращаюс|меняю\s+внешност|принимаю\s+облик|меняю\s+лицо|change\s+form|shapechange|disguise\s+myself)",
    re.IGNORECASE,
)
SHAPECHANGER_REVERT_RE = re.compile(
    r"(возвращаюс?\s+в\s+истинн|истинн(?:ая|ую)\s+форм|снимаю\s+облик|revert|true\s+form)",
    re.IGNORECASE,
)
SHAPECHANGER_PERSONA_CAPTURE_RE = re.compile(
    r"(?:превращаюс(?:ь)?|меняю\s+внешност(?:ь)?|принимаю\s+облик|меняю\s+лицо|change\s+form|shapechange|disguise\s+myself)"
    r"(?:\s*(?:в|под|как|into|as|to|:|-)\s*)?(?P<persona>[^\n\r]{1,240})?$",
    re.IGNORECASE,
)
MIND_LINK_SET_CAPTURE_RE = re.compile(
    r"(?:связь\s+разумов\s+с|телепатия\s+с|mind\s+link)\s+(?P<target>[^\n\r]{1,120})$",
    re.IGNORECASE,
)
MIND_LINK_SAY_CAPTURE_RE = re.compile(
    r"(?:телепатия|мысленно|mind)\s*:\s*(?P<text>[^\n\r]+)$",
    re.IGNORECASE,
)
MIND_LINK_REPLY_CAPTURE_RE = re.compile(
    r"(?:ответ\s+мысленно|мысль\s+в\s+ответ|telepathy\s+reply)\s*:\s*(?P<text>[^\n\r]+)$",
    re.IGNORECASE,
)
CHAT_COMBAT_ACTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "combat_shapechanger_revert",
        SHAPECHANGER_REVERT_RE,
    ),
    (
        "combat_shapechanger_shift",
        SHAPECHANGER_SHIFT_RE,
    ),
    (
        "combat_hooves_attack",
        re.compile(r"(копыт\w*|бью\s+копыт\w*|топч\w*)", re.IGNORECASE),
    ),
    (
        "combat_vampiric_bite",
        re.compile(r"(укус\s+вампир\w*|кусаю|впива\w+|пью\s+кров\w*|vampiric\s+bite)", re.IGNORECASE),
    ),
    (
        "combat_hidden_step",
        re.compile(
            r"(незрим\w*\s+поступ\w*|становлюсь\s+невидим\w*|скрываюсь\s+магией\s+фирболг\w*|hidden\s+step)",
            re.IGNORECASE,
        ),
    ),
    (
        "combat_taunt",
        re.compile(r"(насмешк\w*|дразн\w*|провоцир\w*|taunt\b)", re.IGNORECASE),
    ),
    (
        "combat_fearless",
        re.compile(r"(бесстраши\w*|fearless\b)", re.IGNORECASE),
    ),
    (
        "combat_attack",
        re.compile(
            r"(атак|напад|удар|бью|рубл|колю|выпад|тыч|пыр|замах|метаю|швыряю|стреля|выстрел|стрел|лук|арбалет|режу|вступаю\s+в\s+бой|вступить\s+в\s+бой|вхожу\s+в\s+бой|войти\s+в\s+бой|врываюсь\s+в\s+бой)",
            re.IGNORECASE,
        ),
    ),
    (
        "combat_mode_walk",
        re.compile(r"(?:\bиду\b(?!\s+\d)|по\s+земле|перехожу\s+на\s+шаг)", re.IGNORECASE),
    ),
    (
        "combat_mode_swim",
        re.compile(r"(плыв\w*|ныря\w*)", re.IGNORECASE),
    ),
    (
        "combat_mode_climb",
        re.compile(r"(лез\w*|карабка\w*)", re.IGNORECASE),
    ),
    ("combat_dodge", re.compile(r"(уклон|уворач|уворот|в защиту|защищаюсь|оборон|в оборону|блок|стойк|додж)", re.IGNORECASE)),
    ("combat_help", re.compile(r"(помога|помочь|помогу|поддерж|страх|отвлек|координ|даю преимущество|открываю окно|прикрываю)", re.IGNORECASE)),
    (
        "combat_escape",
        re.compile(
            r"(?:убег\w*|убеж\w*|сбег\w*|сбеж\w*|беж\w*|побег\w*|удир\w*|драп\w*|ретир\w*|свал\w*|спас\w*|бегу\s+прочь|уход\s+из\s+боя|выхожу\s+из\s+боя|выйт[ьи]\s+из\s+боя|выйду\s+из\s+боя|выйти\s+с\s+поля\s+боя|с\s+поля\s+боя|поле\s+боя)"
            ,
            re.IGNORECASE,
        ),
    ),
    ("combat_dash", re.compile(r"(рывок|спринт|\bбегу\b(?!\s+(?:прочь|из\s+боя|с\s+боя))|мчусь|ускоряюсь|ринул|бросаюсь вперед|стремглав|сокращаю дистанц)", re.IGNORECASE)),
    ("combat_move", re.compile(r"(двигаюсь\s+\d+|перемещаюсь\s+на\s+\d+|иду\s+\d+\s*(?:фт|фут(?:ов|а)?)?)", re.IGNORECASE)),
    ("combat_disengage", re.compile(r"(отхож|отход|отступ|отступаю|вырываюсь|разрыв дистанц|разрыва[юл]|разорва[лю]|отпрыг|отскоч|дисенгейдж)", re.IGNORECASE)),
    ("combat_hide", re.compile(r"(засад\w*|пряч\w*|скрываюсь\s+в\s+тени|hide\b)", re.IGNORECASE)),
    (
        "combat_rabbit_hop",
        re.compile(r"(кролич\w+\s+прыж\w*|прыж\w+\s+зайц\w*|rabbit\s+hop|прыгаю\s+рывком)", re.IGNORECASE),
    ),
    (
        "combat_lucky_footwork",
        re.compile(r"(сильн\w+\s+ног\w*|lucky\s+footwork|добавляю\s+1к4\s+к\s+ловк\w+\s+сейв\w*)", re.IGNORECASE),
    ),
    (
        "combat_saving_face",
        re.compile(r"(сохран\w+\s+лиц\w*|спас\w+\s+лиц\w*|saving\s+face|не\s+теряю\s+лиц\w*)", re.IGNORECASE),
    ),
    (
        "combat_eerie_token_create",
        re.compile(r"(созда\w+\s+жутк\w+\s+сувенир\w*|жутк\w+\s+сувенир\w*|создат\w+\s+сувенир\w*|eerie\s+token)", re.IGNORECASE),
    ),
    (
        "combat_eerie_token_message",
        re.compile(
            r"(переда\w+\s+сообщени\w+\s+сувенир\w*|телепатическ\w+\s+сообщени\w*|send\s+message)",
            re.IGNORECASE,
        ),
    ),
    (
        "combat_eerie_token_view",
        re.compile(r"(смотрю\s+через\s+сувенир\w*|вхож\w+\s+в\s+транс|remote\s+view|scry\s+token)", re.IGNORECASE),
    ),
    (
        "combat_grung_poison_weapon",
        re.compile(
            r"(смазыва\w*\s+оруж\w*\s+ядом|наношу\s+яд|яд\s+на\s+оруж\w*|poison\s+weapon|apply\s+poison)",
            re.IGNORECASE,
        ),
    ),
    (
        "combat_takeoff",
        re.compile(r"(взлетаю|взлёт|поднимаюсь\s+в\s+воздух|в\s+воздух)", re.IGNORECASE),
    ),
    (
        "combat_land",
        re.compile(r"(приземляюсь|снижаюсь|опускаюсь|на\s+землю)", re.IGNORECASE),
    ),
    (
        "rest_long",
        re.compile(r"(долг(?:ий|ого)\s+отдых|long\s+rest|сплю\s+всю\s+ночь|отдыхаю\s+до\s+утра)", re.IGNORECASE),
    ),
    (
        "breathe_underwater",
        re.compile(
            r"(дышу\s+под\s+водой|ныряю|задерживаю\s+дыхание\s+под\s+водой|breathe\s+underwater)",
            re.IGNORECASE,
        ),
    ),
    (
        "water_immerse",
        re.compile(
            r"(погружаюсь\s+в\s+воду|час\s+в\s+воде|купал(?:ся|ась)|immerse\s+in\s+water)",
            re.IGNORECASE,
        ),
    ),
    (
        "mind_link_set",
        re.compile(r"(связь\s+разумов\s+с\s+\S+|телепатия\s+с\s+\S+|mind\s+link\s+(?!off\b)\S+)", re.IGNORECASE),
    ),
    (
        "mind_link_clear",
        re.compile(r"(разорва\w*\s+связ\w*|снят\w*\s+связ\w*|mind\s+link\s+off|unlink\b)", re.IGNORECASE),
    ),
    (
        "mind_link_say",
        re.compile(r"(телепатия\s*:|мысленно\s*:|mind\s*:)", re.IGNORECASE),
    ),
    (
        "mind_link_reply",
        re.compile(r"(ответ\s+мысленно\s*:|мысль\s+в\s+ответ\s*:|telepathy\s+reply\s*:)", re.IGNORECASE),
    ),
    (
        "combat_innate_spell",
        re.compile(
            r"(?:кастую|колдую|накладываю|использую\s+заклинание|заклинание|"
            r"левитац|levitate|проход.*сквозь.*кам|passwall|создани[еия]\s+огня|produce\s+flame|"
            r"горящ(?:ие|их)\s+руки|burning\s+hands|формирован(?:ие|ия)\s+воды|shape\s+water|"
            r"создани(?:е|я).*(?:уничтожени(?:е|я)).*воды|create.*destroy.*water|"
            r"мала[яй]\s+иллюз\w*|minor\s+illusion|"
            r"танцующ[а-яё]*\s+огн[а-яё]*|dancing\s+lights|волшебн[а-яё]*\s+ог(?:н|он)[а-яё]*|faerie\s+fire|"
            r"обнаружени[ея]\s+магии|detect\s+magic|маскировк\w*|disguise\s+self|"
            r"сглаз\w*|\bhex\b|"
            r"искусств(?:о|а)\s+друид\w*|druidcraft|"
            r"увеличени[ея]\s*/?\s*уменьшени[ея]|enlarge\s*/?\s*reduce|enlarge\s+reduce|"
            r"(?:заклинани[ея]\s+)?щит\b|shield|"
            r"обнаружени[ея]\s+мысл\w*|чтени[ея]\s+мысл\w*|detect\s+thoughts|"
            r"прыж\w*|jump|туманн\w+\s+шаг\w*|misty\s+step|"
            r"тауматург\w*|thaumaturgy|адск\w*\s+(?:возмезди\w*|отпор\w*)|hellish\s+rebuke|darkness)",
            re.IGNORECASE,
        ),
    ),
    (
        "combat_stone_endurance",
        re.compile(r"(каменн\w*\s+вынослив\w*|stone\s+endurance|снижаю\s+урон)", re.IGNORECASE),
    ),
    (
        "combat_healing_hands",
        re.compile(
            r"(исцеляющ\w*\s+рук\w*|healing\s+hands|лечу\s+прикосновением|исцеляю\s+прикосновением)",
            re.IGNORECASE,
        ),
    ),
    (
        "combat_aasimar_transform",
        re.compile(
            r"(преобразуюс|раскрываю\s+крыл|сияющ|поглощение\s+сияния|некротическ(?:ий|ого)\s+покров|radiant\s+soul|radiant\s+consumption|necrotic\s+shroud)",
            re.IGNORECASE,
        ),
    ),
    (
        "combat_breath_weapon",
        re.compile(
            r"(оружи\w+\s+дыхани\w+|выдыха\w+|дыш\w+\s+(?:огн|плам|молн|кисл|яд|холод)|breath\s+weapon)",
            re.IGNORECASE,
        ),
    ),
    (
        "use_built_for_success",
        re.compile(
            r"(создан\w*\s+для\s+успех\w*|добавляю\s+1\s*к\s*4|добавляю\s+1d4|built\s+for\s+success)",
            re.IGNORECASE,
        ),
    ),
    (
        "combat_fury_of_small",
        re.compile(
            r"(разъяр[её]нн\w+\s+мелкот\w*|ярост\w+\s+мелкот\w*|ярост\w+\s+мал\w*|выпускаю\s+ярост\w*|"
            r"ярюсь|впадаю\s+в\s+ярост\w*(?:\s+мелкот\w*)?|fury\s+of\s+the\s+small)",
            re.IGNORECASE,
        ),
    ),
    ("combat_use_object", re.compile(r"(использую|применяю|активирую|включаю|поджигаю|зажигаю|пью|выпиваю|нажимаю|достаю|зелье|флакон|свиток|факел|рычаг|кнопк)", re.IGNORECASE)),
    (
        "tortle_shell_in",
        re.compile(
            r"(?:пряч\w*|залез\w*|втяг\w*|убира\w*|скрыва\w*)(?:\s+\S+){0,3}?\s+(?:в|внутрь)\s+(?:свой\s+)?панцир\w*",
            re.IGNORECASE,
        ),
    ),
    (
        "tortle_shell_out",
        re.compile(
            r"(?:вылез\w*|выбира\w*|выхож\w*|вытягива\w*|раскрыва\w*)(?:\s+\S+){0,3}?\s+(?:из|с)\s+(?:своего\s+)?панцир\w*",
            re.IGNORECASE,
        ),
    ),
    ("combat_end_turn", re.compile(r"(конец хода|заканчиваю ход|передаю ход|пас|пропускаю ход|жду|ничего не делаю)", re.IGNORECASE)),
]
COMBAT_MECHANICS_EVENT_RE = re.compile(
    r"(?:@@|🎲|Бросок атаки|Результат:|Урон:|:\s*HP\s+\d+/\d+|vs AC|Раунд\s+\d+|Ход автоматически передан)",
    flags=re.IGNORECASE,
)
COMBAT_MOVE_DISTANCE_RE = re.compile(
    r"(?:двигаюсь\s+|перемещаюсь\s+на\s+|иду\s+)(\d+)(?:\s*(?:фт|фут(?:ов|а)?))?",
    re.IGNORECASE,
)
ZONE_MOVE_RE = re.compile(
    r"\b(?:иду|пойду|направляюсь|отправляюсь|захожу|вхожу|перехожу|возвращаюсь)\b"
    r"(?:\s+\S+){0,4}?\s+\b(?:в|на|к)\b\s+([^\n\.,;:!\?\(\)\[\]\{\}]+)",
    re.IGNORECASE,
)
