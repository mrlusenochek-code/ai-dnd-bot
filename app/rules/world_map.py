from __future__ import annotations

import zlib
from dataclasses import dataclass
from typing import Any, Iterable


# Строки должны совпадать с enemy_catalog environments
ENVIRONMENTS = (
    "город",
    "лес",
    "побережье",
    "под водой",
    "болото",
    "горы",
    "холмы",
    "луг",
    "пустыня",
    "арктика",
    "подземье",
)

DIRS = {
    "n": (0, -1),
    "s": (0, 1),
    "w": (-1, 0),
    "e": (1, 0),
}


def world_seed_from_text(text: str) -> int:
    s = (text or "").encode("utf-8", errors="ignore")
    return int(zlib.adler32(s) & 0xFFFFFFFF)


def _chunk_key(cx: int, cy: int) -> str:
    return f"{int(cx)},{int(cy)}"


def _hash_u32(*parts: Any) -> int:
    blob = "|".join(str(p) for p in parts).encode("utf-8", errors="ignore")
    return int(zlib.adler32(blob) & 0xFFFFFFFF)


def _pick_from_weights(seed_u32: int, items: list[tuple[str, int]]) -> str:
    total = sum(max(0, int(w)) for _, w in items)
    if total <= 0:
        return items[0][0]
    r = seed_u32 % total
    acc = 0
    for name, w in items:
        acc += max(0, int(w))
        if r < acc:
            return name
    return items[-1][0]


def pick_chunk_env(seed: int, cx: int, cy: int) -> str:
    """
    Простая, но связная логика:
    - ближе к старту иногда город,
    - по Y меняется климат (север арктика, юг пустыня),
    - иногда побережье/под водой,
    - иногда подземье.
    """
    base = _hash_u32("chunk_env", seed, cx, cy)

    dist = abs(cx) + abs(cy)
    if dist <= 2:
        # на старте чуть чаще город, чтобы не было пустоты
        if (base % 100) < 25:
            return "город"

    # климат по широте
    if cy <= -8:
        climate = "пустыня"
    elif cy >= 8:
        climate = "арктика"
    else:
        climate = "temperate"

    # вероятность “особых” биомов
    if (base % 1000) < 35:
        return "подземье"

    if (base % 1000) < 85:
        # побережье
        return "побережье"

    if climate == "пустыня":
        weights = [
            ("пустыня", 60),
            ("холмы", 15),
            ("горы", 10),
            ("луг", 10),
            ("болото", 5),
        ]
        return _pick_from_weights(base, weights)

    if climate == "арктика":
        weights = [
            ("арктика", 60),
            ("горы", 20),
            ("лес", 10),
            ("холмы", 10),
        ]
        return _pick_from_weights(base, weights)

    # умеренный пояс
    weights = [
        ("лес", 30),
        ("луг", 20),
        ("холмы", 18),
        ("болото", 12),
        ("горы", 10),
        ("город", 10),
    ]
    return _pick_from_weights(base, weights)


def generate_chunk_meta(seed: int, cx: int, cy: int) -> dict[str, Any]:
    env = pick_chunk_env(seed, cx, cy)
    h = _hash_u32("chunk_meta", seed, cx, cy)

    # каркас фич (потом можно расширять: деревни, руины, данжи и т.д.)
    has_road = (h % 100) < (18 if env not in ("под водой",) else 3)
    danger = 0
    if env in ("подземье", "болото"):
        danger += 1
    if env in ("горы", "пустыня", "арктика"):
        danger += 1

    return {
        "cx": int(cx),
        "cy": int(cy),
        "env": env,
        "has_road": bool(has_road),
        "danger": int(danger),
    }


def tile_env(seed: int, chunk_size: int, x: int, y: int, chunk_env: str) -> str:
    """
    Внутри чанка даём небольшую вариативность.
    Для побережья часть клеток делаем "под водой".
    """
    if chunk_env == "побережье":
        h = _hash_u32("tile", seed, x, y)
        # примерно 25% клеток = вода
        if (h % 100) < 25:
            return "под водой"
    return chunk_env


@dataclass
class WorldState:
    seed: int
    chunk_size: int
    x: int
    y: int
    chunks: dict[str, dict[str, Any]]  # key "cx,cy" -> meta


def init_world_state(*, seed: int, chunk_size: int = 10, pregen_radius_chunks: int = 4) -> WorldState:
    chunks: dict[str, dict[str, Any]] = {}
    for cy in range(-pregen_radius_chunks, pregen_radius_chunks + 1):
        for cx in range(-pregen_radius_chunks, pregen_radius_chunks + 1):
            k = _chunk_key(cx, cy)
            chunks[k] = generate_chunk_meta(seed, cx, cy)
    return WorldState(seed=int(seed), chunk_size=int(chunk_size), x=0, y=0, chunks=chunks)


def world_to_dict(ws: WorldState) -> dict[str, Any]:
    return {
        "v": 1,
        "seed": int(ws.seed),
        "chunk_size": int(ws.chunk_size),
        "x": int(ws.x),
        "y": int(ws.y),
        "chunks": dict(ws.chunks),
    }


def world_from_dict(raw: Any) -> WorldState | None:
    if not isinstance(raw, dict):
        return None
    if raw.get("v") != 1:
        return None
    seed = raw.get("seed")
    chunk_size = raw.get("chunk_size")
    x = raw.get("x")
    y = raw.get("y")
    chunks = raw.get("chunks")
    if not isinstance(seed, int) or not isinstance(chunk_size, int):
        return None
    if not isinstance(x, int) or not isinstance(y, int):
        return None
    if not isinstance(chunks, dict):
        return None
    fixed: dict[str, dict[str, Any]] = {}
    for k, v in chunks.items():
        if isinstance(k, str) and isinstance(v, dict):
            fixed[k] = v
    return WorldState(seed=seed, chunk_size=max(1, chunk_size), x=x, y=y, chunks=fixed)


def _ensure_view_chunks(ws: WorldState, view_radius_chunks: int) -> list[dict[str, Any]]:
    """
    Генерит недостающие чанки вокруг текущей позиции (по радиусу view).
    Возвращает список новых чанков (meta), чтобы можно было отправить в UI patch.
    """
    cx0 = ws.x // ws.chunk_size
    cy0 = ws.y // ws.chunk_size
    added: list[dict[str, Any]] = []

    for cy in range(cy0 - view_radius_chunks, cy0 + view_radius_chunks + 1):
        for cx in range(cx0 - view_radius_chunks, cx0 + view_radius_chunks + 1):
            k = _chunk_key(cx, cy)
            if k in ws.chunks:
                continue
            meta = generate_chunk_meta(ws.seed, cx, cy)
            ws.chunks[k] = meta
            added.append(meta)
    return added


def move(ws: WorldState, direction: str, *, view_radius_chunks: int = 2) -> tuple[WorldState, dict[str, Any]]:
    if direction not in DIRS:
        return ws, {"err": "unknown direction"}

    dx, dy = DIRS[direction]
    ws.x += int(dx)
    ws.y += int(dy)

    cx = ws.x // ws.chunk_size
    cy = ws.y // ws.chunk_size
    ckey = _chunk_key(cx, cy)
    if ckey not in ws.chunks:
        ws.chunks[ckey] = generate_chunk_meta(ws.seed, cx, cy)

    added = _ensure_view_chunks(ws, view_radius_chunks=view_radius_chunks)

    chunk_env = ws.chunks[ckey]["env"]
    env = tile_env(ws.seed, ws.chunk_size, ws.x, ws.y, chunk_env)

    patch = {
        "pos": {"x": ws.x, "y": ws.y},
        "env": env,
        "chunk": {"cx": cx, "cy": cy, "env": chunk_env},
        "new_chunks": added,
    }
    return ws, patch
