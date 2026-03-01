from __future__ import annotations

import random
import zlib
from dataclasses import dataclass
from typing import Any

from app.rules.enemy_catalog_data import load_enemies_by_env


@dataclass(frozen=True)
class EncounterDef:
    key: str
    enemy_key: str
    count: int
    reason: str


def _party_level_cr_cap(party_level: int) -> float:
    lvl = max(1, int(party_level))
    if lvl <= 1:
        return 1.0
    if lvl <= 3:
        return 2.0
    if lvl <= 5:
        return 3.0
    if lvl <= 7:
        return 4.0
    if lvl <= 9:
        return 5.0
    return 6.0


def _parse_cr(raw: Any) -> float | None:
    if isinstance(raw, (int, float)):
        return float(raw)
    if not isinstance(raw, str):
        return None
    txt = raw.strip()
    if not txt or txt in {"—", "-"}:
        return None
    if "/" in txt:
        left, right = txt.split("/", 1)
        if left.strip().isdigit() and right.strip().isdigit():
            denom = int(right.strip())
            if denom > 0:
                return int(left.strip()) / denom
        return None
    try:
        return float(txt)
    except ValueError:
        return None


def _rng_from_cell(seed: str, x: int, y: int, env: str) -> random.Random:
    src = f"{seed}:{x}:{y}:{env}:enc".encode("utf-8", errors="ignore")
    num = int(zlib.adler32(src) & 0xFFFFFFFF)
    return random.Random(num)


def pick_encounter(*, seed: str, x: int, y: int, env: str, party_level: int, rng=None) -> EncounterDef | None:
    active_rng = rng if rng is not None else _rng_from_cell(str(seed), int(x), int(y), str(env))

    # MVP: единый базовый шанс для всех биомов.
    if float(active_rng.random()) >= 0.25:
        return None

    enemies = load_enemies_by_env(str(env))
    if not enemies:
        return None

    cr_cap = _party_level_cr_cap(int(party_level))
    candidates: list[dict[str, Any]] = []
    for e in enemies:
        if not isinstance(e, dict):
            continue
        key = e.get("key")
        if not isinstance(key, str) or not key.strip():
            continue
        cr = _parse_cr(e.get("cr"))
        if cr is None:
            continue
        if cr <= cr_cap:
            candidates.append(e)
    if not candidates:
        return None

    idx = int(active_rng.randrange(len(candidates)))
    enemy = candidates[idx]
    enemy_key = str(enemy.get("key"))
    return EncounterDef(
        key=f"{seed}:{x}:{y}:{env}:{enemy_key}",
        enemy_key=enemy_key,
        count=1,
        reason=f"env={env};party_level={max(1, int(party_level))};cr_cap={cr_cap}",
    )
