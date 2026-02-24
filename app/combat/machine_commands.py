from __future__ import annotations

# Модуль нужен для безопасного вынесения парсинга боевых машинных команд из server.py,
# чтобы позже подключить его без перегрузки веб-слоя.

from dataclasses import dataclass
import re
from typing import Dict, List


@dataclass(frozen=True)
class CombatStartCommand:
    zone: str | None
    cause: str | None
    surprise: str | None


@dataclass(frozen=True)
class CombatEnemyAddCommand:
    enemy_id: str
    name: str
    hp: int | None
    ac: int | None
    init_mod: int | None
    threat: int | None


@dataclass(frozen=True)
class CombatEndCommand:
    result: str | None


@dataclass(frozen=True)
class RandomEventCommand:
    key: str
    category: str | None
    severity: int | None


@dataclass(frozen=True)
class ParsedMachineCommands:
    visible_text: str
    combat_start: CombatStartCommand | None
    combat_enemy_add: tuple[CombatEnemyAddCommand, ...]
    combat_end: CombatEndCommand | None
    random_events: tuple[RandomEventCommand, ...]
    had_any_commands: bool


COMBAT_START_MACHINE_LINE_RE = re.compile(
    r'^\s*(?:\(\s*)?@@COMBAT_START\((?P<args>.*?)\)\s*(?:\))?\s*$'
)
COMBAT_ENEMY_ADD_MACHINE_LINE_RE = re.compile(
    r'^\s*(?:\(\s*)?@@COMBAT_ENEMY_ADD\((?P<args>.*?)\)\s*(?:\))?\s*$'
)
COMBAT_END_MACHINE_LINE_RE = re.compile(
    r'^\s*(?:\(\s*)?@@COMBAT_END\((?P<args>.*?)\)\s*(?:\))?\s*$'
)
RANDOM_EVENT_MACHINE_LINE_RE = re.compile(
    r'^\s*(?:\(\s*)?@@RANDOM_EVENT\((?P<args>.*?)\)\s*(?:\))?\s*$'
)


def parse_machine_args(raw: str) -> dict[str, str]:
    parts: List[str] = []
    current: List[str] = []
    in_quotes = False

    for char in raw:
        if char == '"':
            in_quotes = not in_quotes
            current.append(char)
            continue
        if char == ',' and not in_quotes:
            part = ''.join(current).strip()
            if part:
                parts.append(part)
            current = []
            continue
        current.append(char)

    tail = ''.join(current).strip()
    if tail:
        parts.append(tail)

    result: Dict[str, str] = {}
    for part in parts:
        if '=' not in part:
            continue
        key, value = part.split('=', 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        result[key] = value

    return result


def _clean_str(value: str | None) -> str | None:
    if value is None:
        return None

    cleaned = value.strip()
    if len(cleaned) >= 2 and cleaned[0] == '"' and cleaned[-1] == '"':
        cleaned = cleaned[1:-1].strip()

    if not cleaned:
        return None

    if cleaned.lower() == 'none':
        return None

    return cleaned


def _to_int(value: str | None) -> int | None:
    cleaned = _clean_str(value)
    if cleaned is None:
        return None

    if not re.fullmatch(r'[+-]?\d+', cleaned):
        return None

    return int(cleaned)


def extract_combat_machine_commands(text: str) -> ParsedMachineCommands:
    visible_lines: List[str] = []
    combat_start: CombatStartCommand | None = None
    combat_enemy_add: List[CombatEnemyAddCommand] = []
    combat_end: CombatEndCommand | None = None
    random_events: List[RandomEventCommand] = []
    had_any_commands = False

    for line in text.splitlines():
        start_match = COMBAT_START_MACHINE_LINE_RE.fullmatch(line)
        if start_match:
            had_any_commands = True
            args = parse_machine_args(start_match.group('args'))
            combat_start = CombatStartCommand(
                zone=_clean_str(args.get('zone')),
                cause=_clean_str(args.get('cause')),
                surprise=_clean_str(args.get('surprise')),
            )
            continue

        enemy_add_match = COMBAT_ENEMY_ADD_MACHINE_LINE_RE.fullmatch(line)
        if enemy_add_match:
            had_any_commands = True
            args = parse_machine_args(enemy_add_match.group('args'))
            enemy_id = _clean_str(args.get('enemy_id'))
            name = _clean_str(args.get('name'))
            if enemy_id is not None and name is not None:
                combat_enemy_add.append(
                    CombatEnemyAddCommand(
                        enemy_id=enemy_id,
                        name=name,
                        hp=_to_int(args.get('hp')),
                        ac=_to_int(args.get('ac')),
                        init_mod=_to_int(args.get('init_mod')),
                        threat=_to_int(args.get('threat')),
                    )
                )
            continue

        end_match = COMBAT_END_MACHINE_LINE_RE.fullmatch(line)
        if end_match:
            had_any_commands = True
            args = parse_machine_args(end_match.group('args'))
            combat_end = CombatEndCommand(result=_clean_str(args.get('result')))
            continue

        random_event_match = RANDOM_EVENT_MACHINE_LINE_RE.fullmatch(line)
        if random_event_match:
            had_any_commands = True
            args = parse_machine_args(random_event_match.group('args'))
            key = _clean_str(args.get('key'))
            if key is not None:
                random_events.append(
                    RandomEventCommand(
                        key=key,
                        category=_clean_str(args.get('category')),
                        severity=_to_int(args.get('severity')),
                    )
                )
            continue

        visible_lines.append(line)

    visible_text = '\n'.join(visible_lines).strip()

    return ParsedMachineCommands(
        visible_text=visible_text,
        combat_start=combat_start,
        combat_enemy_add=tuple(combat_enemy_add),
        combat_end=combat_end,
        random_events=tuple(random_events),
        had_any_commands=had_any_commands,
    )


# Пример 1:
# Вход: "Туман\n(@@COMBAT_START(zone=\"bridge\", cause=ambush))\nБой начинается"
# Выход: visible_text="Туман\nБой начинается", combat_start.zone="bridge", had_any_commands=True
#
# Пример 2:
# Вход: "@@COMBAT_ENEMY_ADD(enemy_id=gob1, name=\"Goblin Raider\", hp=12, ac=13, init_mod=2, threat=1)"
# Выход: combat_enemy_add=(CombatEnemyAddCommand(...),), visible_text=""
#
# Пример 3:
# Вход: "(@@RANDOM_EVENT(key=storm, category=weather, severity=2))\nПорыв ветра"
# Выход: random_events=(RandomEventCommand(key=\"storm\", ...),), visible_text="Порыв ветра"
