from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


CATALOG_PATH = Path(__file__).with_name("enemy_catalog.json")


def _parse_cr(cr: Any) -> float | None:
    """
    CR can be: "1/8", "2", "—", "", None.
    Return float (e.g. 0.125) or None.
    """
    if not isinstance(cr, str):
        return None
    s = cr.strip()
    if not s or s in {"—", "-"}:
        return None
    if "/" in s:
        a, b = s.split("/", 1)
        if a.strip().isdigit() and b.strip().isdigit():
            denom = int(b.strip())
            if denom > 0:
                return int(a.strip()) / denom
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _is_reasonable_enemy(raw: dict[str, Any]) -> bool:
    # Отсекаем мусорные карточки (в каталоге такие встречаются)
    if not raw.get("key") or not isinstance(raw.get("key"), str):
        return False
    if not raw.get("name_ru") or not isinstance(raw.get("name_ru"), str):
        return False
    ac = raw.get("ac")
    hp = raw.get("hp_avg")
    if not isinstance(ac, int) or ac <= 0:
        return False
    if hp is None:
        return False
    if not isinstance(hp, int) or hp <= 0:
        return False

    stats = raw.get("stats")
    if isinstance(stats, dict):
        # если все статы нули — это почти наверняка поломанная карточка
        vals = [stats.get(k, 0) for k in ("str", "dex", "con", "int", "wis", "cha")]
        if all(isinstance(v, int) and v == 0 for v in vals):
            return False

    # CR пустой допускаем (на dndsu есть такие), но это “хуже”
    return True


def _quality_score(raw: dict[str, Any]) -> int:
    """
    Нужно для детерминированного выбора при дубликатах ключей:
    предпочитаем более “полную” карточку.
    """
    score = 0
    if _parse_cr(raw.get("cr")) is not None:
        score += 10
    if raw.get("xp") is not None:
        score += 3
    if raw.get("hp_formula"):
        score += 2
    stats = raw.get("stats")
    if isinstance(stats, dict) and any(int(stats.get(k, 0) or 0) != 0 for k in ("str","dex","con","int","wis","cha")):
        score += 1
    env = raw.get("environments")
    if isinstance(env, list) and len(env) > 0:
        score += 1
    return score


@dataclass(frozen=True)
class EnemyCatalog:
    enemies: list[dict[str, Any]]
    by_key: dict[str, dict[str, Any]]
    by_env: dict[str, list[dict[str, Any]]]


@lru_cache(maxsize=1)
def load_enemy_catalog() -> EnemyCatalog:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("enemy_catalog.json must be a JSON list")

    enemies: list[dict[str, Any]] = []
    by_key: dict[str, dict[str, Any]] = {}

    for it in payload:
        if not isinstance(it, dict):
            continue
        if not _is_reasonable_enemy(it):
            continue

        key = it["key"]
        # дедуп: оставляем “лучшее”
        prev = by_key.get(key)
        if prev is None or _quality_score(it) > _quality_score(prev):
            by_key[key] = it

    # стабильный порядок
    for key in sorted(by_key.keys()):
        enemies.append(by_key[key])

    by_env: dict[str, list[dict[str, Any]]] = {}
    for e in enemies:
        envs = e.get("environments") or []
        if not isinstance(envs, list):
            continue
        for env in envs:
            if isinstance(env, str) and env.strip():
                by_env.setdefault(env.strip(), []).append(e)

    return EnemyCatalog(enemies=enemies, by_key=by_key, by_env=by_env)


def get_enemy(key: str) -> dict[str, Any] | None:
    if not isinstance(key, str) or not key:
        return None
    return load_enemy_catalog().by_key.get(key)


def filter_enemies_by_env(envs: Iterable[str]) -> list[dict[str, Any]]:
    cat = load_enemy_catalog()
    wanted = [e.strip() for e in envs if isinstance(e, str) and e.strip()]
    if not wanted:
        return cat.enemies
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for env in wanted:
        for e in cat.by_env.get(env, []):
            k = e.get("key")
            if isinstance(k, str) and k not in seen:
                seen.add(k)
                out.append(e)
    return out
