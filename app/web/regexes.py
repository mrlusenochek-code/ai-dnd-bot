import re


INV_MACHINE_LINE_RE = re.compile(
    r"^\s*(?:\(\s*)?@@(?P<cmd>INV_ADD|INV_REMOVE|INV_TRANSFER|EQUIP|UNEQUIP)\s*\((?P<args>.*)\)\s*(?:\))?\s*$",
    re.IGNORECASE,
)
ZONE_SET_MACHINE_LINE_RE = re.compile(r"^\s*(?:\(\s*)?@@ZONE_SET\s*\((?P<args>.*?)\)\s*(?:\))?\s*$", re.IGNORECASE)
CHAT_COMBAT_ACTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "combat_attack",
        re.compile(
            r"(атак|напад|удар|бью|рубл|колю|выпад|тыч|пыр|замах|метаю|швыряю|стреля|выстрел|стрел|лук|арбалет|режу|вступаю\s+в\s+бой|вступить\s+в\s+бой|вхожу\s+в\s+бой|войти\s+в\s+бой|врываюсь\s+в\s+бой)",
            re.IGNORECASE,
        ),
    ),
    ("combat_dodge", re.compile(r"(уклон|уворач|уворот|в защиту|защищаюсь|оборон|в оборону|блок|щит|стойк|додж)", re.IGNORECASE)),
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
    (
        "combat_takeoff",
        re.compile(r"(взлетаю|взлёт|поднимаюсь\s+в\s+воздух|в\s+воздух)", re.IGNORECASE),
    ),
    (
        "combat_land",
        re.compile(r"(приземляюсь|снижаюсь|опускаюсь|на\s+землю)", re.IGNORECASE),
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
