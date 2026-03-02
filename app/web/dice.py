import random
import re


DICE_RE = re.compile(r"^\s*(?:(roll|adv|dis)\s+)?(\d+)\s*d\s*(\d+)\s*([+-]\s*\d+)?\s*$", re.IGNORECASE)


def roll_dice(n: int, sides: int) -> list[int]:
    return [random.randint(1, sides) for _ in range(n)]


def parse_dice(text: str):
    m = DICE_RE.match(text)
    if not m:
        return None
    mode = (m.group(1) or "roll").lower()
    n = int(m.group(2))
    sides = int(m.group(3))
    mod_raw = (m.group(4) or "").replace(" ", "")
    mod = int(mod_raw) if mod_raw else 0
    # reasonable limits
    if n < 1 or n > 50 or sides < 2 or sides > 1000:
        return None
    return mode, n, sides, mod, (f"{n}d{sides}{mod_raw}" if mod_raw else f"{n}d{sides}")
