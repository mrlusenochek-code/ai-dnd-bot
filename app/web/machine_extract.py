import logging
from typing import Any

from app.combat.machine_commands import extract_combat_machine_commands
from app.web.machine_lines import _parse_inventory_machine_line, _parse_zone_set_machine_line
from app.web.regexes import ZONE_SET_MACHINE_LINE_RE

logger = logging.getLogger("app.web.server")


def _trim_for_log(text: str, limit: int = 700) -> str:
    txt = str(text or "").strip()
    if len(txt) <= limit:
        return txt
    return txt[:limit] + "... [truncated]"


def _extract_inventory_machine_commands(text: str) -> tuple[str, list[dict[str, Any]]]:
    out_lines: list[str] = []
    commands: list[dict[str, Any]] = []
    for line in str(text or "").splitlines():
        if not str(line).lstrip().startswith("@@INV_"):
            out_lines.append(line)
            continue
        parsed = _parse_inventory_machine_line(line)
        if parsed:
            commands.append(parsed)
        else:
            logger.warning("invalid inventory machine command", extra={"action": {"line": _trim_for_log(line, 260)}})
    return "\n".join(out_lines).strip(), commands


def _extract_machine_commands(text: str) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    out_lines: list[str] = []
    inv_commands: list[dict[str, Any]] = []
    zone_set_commands: list[dict[str, Any]] = []
    # На этом этапе боевые команды только скрываем из видимого текста; применение подключим позже.
    try:
        combat_parsed = extract_combat_machine_commands(text)
        if combat_parsed.had_any_commands:
            logger.debug(
                "combat machine preview: start=%s enemies=%d end=%s random_events=%d",
                combat_parsed.combat_start is not None,
                len(combat_parsed.combat_enemy_add),
                combat_parsed.combat_end is not None,
                len(combat_parsed.random_events),
            )
        combat_visible_text = combat_parsed.visible_text
    except Exception:
        combat_visible_text = str(text or "")
    for line in str(combat_visible_text or "").splitlines():
        lstripped = str(line).lstrip()
        candidate_line = lstripped
        while candidate_line.startswith("("):
            candidate_line = candidate_line[1:].lstrip()
        if candidate_line.startswith("@@INV_") or candidate_line.startswith("@@EQUIP") or candidate_line.startswith("@@UNEQUIP"):
            parsed = _parse_inventory_machine_line(line)
            if parsed:
                inv_commands.append(parsed)
            else:
                logger.warning("invalid inventory machine command", extra={"action": {"line": _trim_for_log(line, 260)}})
            continue
        if ZONE_SET_MACHINE_LINE_RE.match(lstripped):
            parsed_zone = _parse_zone_set_machine_line(line)
            if parsed_zone:
                zone_set_commands.append(parsed_zone)
            else:
                logger.warning("invalid zone_set machine command", extra={"action": {"line": _trim_for_log(line, 260)}})
            continue
        if candidate_line.startswith("@@"):
            logger.warning("unknown machine command", extra={"action": {"line": _trim_for_log(line, 260)}})
            continue
        out_lines.append(line)
    return "\n".join(out_lines).strip(), inv_commands, zone_set_commands
