import re

from typing import Any

from app.gm import sanitize as gm_sanitize


def _hp_state_label(hp_current: int, hp_max: int) -> str:
    hp_max_norm = max(1, int(hp_max))
    hp_cur_norm = max(0, int(hp_current))
    if hp_cur_norm <= 0:
        return "повержен"
    ratio = hp_cur_norm / hp_max_norm
    if ratio <= 0.1:
        return "при смерти"
    if ratio <= 0.3:
        return "тяжело ранен"
    if ratio <= 0.6:
        return "ранен"
    if ratio <= 0.85:
        return "слегка ранен"
    return "цел"


def _hit_force_label(total_damage: int) -> str:
    dmg = max(0, int(total_damage))
    if dmg <= 3:
        return "легко"
    if dmg <= 7:
        return "сильно"
    return "тяжело"


def _de_numberize_text(text: str) -> str:
    txt = str(text or "")
    txt = re.sub(r"\d+", "", txt)
    txt = gm_sanitize.COMBAT_NARRATION_BANNED_RE.sub("", txt)
    txt = re.sub(r"\s{2,}", " ", txt)
    txt = re.sub(r"\s+([,.;:!?])", r"\1", txt)
    return txt.strip()


def _combat_participant_line(actor: Any) -> str:
    name = str(getattr(actor, "name", "") or getattr(actor, "key", "") or "боец").strip()
    hp_cur = int(getattr(actor, "hp_current", 0) or 0)
    hp_max = int(getattr(actor, "hp_max", 1) or 1)
    state = _hp_state_label(hp_cur, hp_max)
    return f"{name} ({state})"
