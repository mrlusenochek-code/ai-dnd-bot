import re
from typing import Optional

from app.db.models import Character, Player, Session
from app.web.inventory_helpers import _equip_state_line, _inventory_state_line
from app.web.regexes import CHAT_COMBAT_ACTION_PATTERNS, ZONE_MOVE_RE
from app.web.session_state import _get_player_position_label
from app.web.utils import as_int


STATE_COMMAND_ALIASES = {"state", "inv", "инв", "inventory"}


def infer_zone_from_action(text: str, current_zone: str) -> str:
    t = str(text or "").strip().lower()
    if not t:
        return current_zone

    def _known_zone(src: str) -> str:
        if any(k in src for k in ("таверн", "бар", "внутри", "остаюсь")):
            return "таверна"
        if any(k in src for k in ("улиц", "выйду", "выхожу", "на улиц")):
            return "улица у таверны"
        if any(k in src for k in ("центр", "площад")):
            return "центр города"
        if any(k in src for k in ("река", "берег")):
            return "берег реки"
        if "замок" in src:
            if any(k in src for k in ("в замк", "внутри замк", "захожу в зам", "войти в зам", "вхожу в зам")):
                return "замок"
            return "дорога к замку"
        return ""

    m = ZONE_MOVE_RE.search(t)
    if m:
        candidate = re.sub(r"\s+", " ", m.group(1)).strip(" \t\r\n\"'`").lower()
        if len(candidate) > 80:
            candidate = candidate[:80].rstrip()
        known = _known_zone(t)
        if known:
            return known
        if len(candidate) >= 3:
            return candidate

    known = _known_zone(t)
    if known:
        return known
    return current_zone


def _format_state_text_for_player(sess: Session, player: Player, ch: Optional[Character]) -> str:
    zone = _get_player_position_label(sess, player.id)
    char_name = str(ch.name).strip() if ch and str(ch.name or "").strip() else "(персонаж не создан)"
    hp_sta = "HP/STA: —"
    if ch:
        hp_sta = f"HP {as_int(ch.hp, 0)}/{as_int(ch.hp_max, 0)} | STA {as_int(ch.sta, 0)}/{as_int(ch.sta_max, 0)}"
    equip_line = _equip_state_line(ch)
    inv_line = _inventory_state_line(ch)
    return f"Состояние: {char_name}\nЗона: {zone}\n{hp_sta}\nОдето: {equip_line}\nИнвентарь: {inv_line}"


def _detect_chat_combat_action(text: str) -> Optional[str]:
    txt = str(text or "").strip()
    if not txt:
        return None
    for action, pattern in CHAT_COMBAT_ACTION_PATTERNS:
        if pattern.search(txt):
            return action
    return None
