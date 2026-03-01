from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class MoveIntent:
    dir: str  # "n" | "s" | "e" | "w"
    reason: str


_DIR_WORDS = {
    # short
    "n": ("n", "n"),
    "s": ("s", "s"),
    "e": ("e", "e"),
    "w": ("w", "w"),
    # russian cardinal
    "с": ("n", "north"),
    "север": ("n", "north"),
    "ю": ("s", "south"),
    "юг": ("s", "south"),
    "в": ("e", "east"),
    "восток": ("e", "east"),
    "з": ("w", "west"),
    "запад": ("w", "west"),
    # relative (MVP: без "ориентации", фиксируем вперед=n и т.д.)
    "вперед": ("n", "forward"),
    "вперёд": ("n", "forward"),
    "назад": ("s", "back"),
    "влево": ("w", "left"),
    "налево": ("w", "left"),
    "вправо": ("e", "right"),
    "направо": ("e", "right"),
}

# глаголы движения (достаточно широкие, чтобы игрокам было удобно)
_VERB = r"(?:иду|идем|идём|пойду|пойдем|пойдём|шагаю|двигаюсь|двигаемся|направляюсь|направляемся|продвигаюсь|продвигаемся)"
# направление/относительное
_DIR = r"(?:n|s|e|w|с|ю|в|з|север|юг|восток|запад|вперед|вперёд|назад|влево|налево|вправо|направо)"
_RE = re.compile(rf"^\s*(?:{_VERB})\s*(?:на\s+)?(?P<d>{_DIR})\s*[.!?]?\s*$", re.IGNORECASE)


def parse_move_intent(text: str) -> MoveIntent | None:
    if not isinstance(text, str):
        return None
    t = text.strip().lower()
    if not t:
        return None

    # normalize ё
    t = t.replace("ё", "е")

    # 1) чистое "вперед/север/налево" и т.п.
    if t in _DIR_WORDS:
        d, reason = _DIR_WORDS[t]
        return MoveIntent(dir=d, reason=reason)

    # 2) "иду на север", "двигаюсь вперед" и т.д.
    m = _RE.match(t)
    if m:
        raw = m.group("d").lower().replace("ё", "е")
        if raw in _DIR_WORDS:
            d, reason = _DIR_WORDS[raw]
            return MoveIntent(dir=d, reason=reason)

    return None
