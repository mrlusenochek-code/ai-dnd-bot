from __future__ import annotations

import re
import zlib
from dataclasses import dataclass
from typing import Any

from app.rules.move_intents import parse_move_intent
from app.rules.world_map import (
    ENVIRONMENTS,
    init_world_state,
    move as world_move,
    world_from_dict,
    world_to_dict,
)


@dataclass(frozen=True)
class NarrationConfig:
    view_radius: int = 1


FORBIDDEN_PATTERNS = (
    "мы продолжаем",
    "мастер помогает",
    "ты оказываешься перед выбором",
    "теперь ответ мастера будет таков",
    "[system]",
    "🧙 gm: []",
)


def _ensure_world(settings: dict[str, Any], session_id: str):
    raw_world = settings.get("world") if isinstance(settings, dict) else None
    ws = world_from_dict(raw_world)
    if ws is None:
        seed = int(zlib.adler32(str(session_id).encode("utf-8", errors="ignore")) & 0xFFFFFFFF)
        ws = init_world_state(seed=seed)
        if isinstance(settings, dict):
            world_payload = world_to_dict(ws)
            world_payload["env"] = ""
            settings["world"] = world_payload
    return ws


def _world_env_at_current_pos(settings: dict[str, Any], session_id: str) -> tuple[Any, str]:
    ws = _ensure_world(settings, session_id)
    patch: dict[str, Any] = {}
    ws, patch = world_move(ws, "n")
    ws, _ = world_move(ws, "s")

    env = str(patch.get("env") or "").strip()
    if env not in ENVIRONMENTS:
        stored = settings.get("world") if isinstance(settings, dict) else {}
        env = str((stored or {}).get("env") or "").strip()
    if env not in ENVIRONMENTS:
        env = ENVIRONMENTS[0]

    if isinstance(settings, dict):
        world_payload = world_to_dict(ws)
        world_payload["env"] = env
        settings["world"] = world_payload

    return ws, env


def _neighbor_hints(ws: Any) -> str:
    if ws is None:
        return ""
    hints: list[str] = []
    dirs = (("север", 0, -1), ("восток", 1, 0), ("юг", 0, 1), ("запад", -1, 0))
    for label, dx, dy in dirs:
        try:
            x = int(getattr(ws, "x", 0)) + dx
            y = int(getattr(ws, "y", 0)) + dy
            chunk_size = max(1, int(getattr(ws, "chunk_size", 10)))
            cx = x // chunk_size
            cy = y // chunk_size
            key = f"{cx},{cy}"
            chunks = getattr(ws, "chunks", {}) or {}
            meta = chunks.get(key) if isinstance(chunks, dict) else None
            env = str((meta or {}).get("env") or "").strip()
            if env and env in ENVIRONMENTS:
                hints.append(f"на {label} {env}")
        except Exception:
            continue
        if len(hints) >= 2:
            break
    if not hints:
        return ""
    return ", ".join(hints)


def _deterministic_detail(seed: int, x: int, y: int) -> str:
    pick = int(zlib.adler32(f"{seed}:{x}:{y}".encode("utf-8", errors="ignore")) & 0xFFFFFFFF) % 4
    details = (
        "В воздухе тянется запах сырой земли.",
        "Где-то рядом слышится глухой шорох.",
        "Ветер несет короткое эхо издалека.",
        "По краю взгляда мелькают тени и блики.",
    )
    return details[pick]


def build_location_block(settings: dict[str, Any], session_id: str, *, cfg: NarrationConfig | None = None) -> str:
    cfg = cfg or NarrationConfig()
    _ = cfg
    ws, env = _world_env_at_current_pos(settings, session_id)
    seed = int(getattr(ws, "seed", 0))
    x = int(getattr(ws, "x", 0))
    y = int(getattr(ws, "y", 0))

    lines: list[str] = []
    lines.append(f"Перед вами {env}, и пространство дышит настороженной тишиной.")
    nearby = _neighbor_hints(ws)
    if nearby:
        lines.append(f"Поблизости заметно, что {nearby}.")
    else:
        lines.append("Вокруг видны приметы сменяющейся местности и редкие ориентиры.")
    lines.append(_deterministic_detail(seed, x, y))
    return " ".join(lines[:3]).strip()


def gm_output_contract() -> str:
    return (
        "ФОРМАТ ОТВЕТА (ОБЯЗАТЕЛЬНО):\n"
        "1) СНАЧАЛА: 2-4 предложения описания текущей локации (атмосфера, местность, что рядом).\n"
        "2) ПОТОМ: линейно отреагируй на действие игрока (без переписывания слов игрока, без реплик за игрока).\n"
        "3) В КОНЦЕ: один вопрос 'Что делаете дальше?' или 2-4 коротких варианта.\n\n"
        "ЗАПРЕЩЕНО:\n"
        "- мета-комментарии ('Мы продолжаем действие', 'последним действием игрока было', 'Теперь ответ мастера будет');\n"
        "- вставлять пустые блоки, [], {} и иные пустые заглушки;\n"
        "- приписывать игроку реплики или мысли ('Ты говоришь...', 'Ты отвечаешь...', 'Ты думаешь...');\n"
        "- придумывать фразы, которые игрок не говорил.\n"
    )


def apply_world_move_to_player_text(
    settings: dict[str, Any],
    session_id: str,
    text: str,
    *,
    combat_active: bool = False,
) -> tuple[str, bool]:
    if not isinstance(text, str):
        return str(text or ""), False

    intent = parse_move_intent(text)
    if intent is None or combat_active:
        return text, False

    ws = _ensure_world(settings, session_id)
    ws, patch = world_move(ws, intent.dir)
    env = str(patch.get("env") or "").strip()
    if env not in ENVIRONMENTS:
        env = ENVIRONMENTS[0]

    world_payload = world_to_dict(ws)
    world_payload["env"] = env
    settings["world"] = world_payload

    moved_text = text
    return moved_text, True


def build_gm_input_text(settings: dict[str, Any], session_id: str, player_text: str, *, moved: bool) -> str:
    loc = build_location_block(settings, session_id)
    contract = gm_output_contract()
    moved_line = "true" if bool(moved) else "false"
    return (
        f"{contract}\n"
        f"MOVED: {moved_line}\n"
        f"ТЕКУЩАЯ ЛОКАЦИЯ:\n{loc}\n\n"
        f"ДЕЙСТВИЕ ИГРОКА:\n{player_text}\n"
    )


def sanitize_gm_output(text: Any, *, location_fallback: str | None = None) -> str:
    if not isinstance(text, str):
        text = "" if text is None else str(text)

    raw = text.strip()
    if raw in ("", "[]", "{}", "[ ]", "{ }"):
        loc = (location_fallback or "").strip()
        if loc:
            return f"{loc}\n\nТы собираешься с мыслями. Что делаете дальше?"
        return "Ты собираешься с мыслями. Что делаете дальше?"

    lowered = raw.lower()
    for bad in FORBIDDEN_PATTERNS:
        lowered = lowered.replace(bad, "").strip()
    # keep original casing while stripping by patterns
    cleaned = raw
    for bad in FORBIDDEN_PATTERNS:
        cleaned = re.sub(re.escape(bad), "", cleaned, flags=re.IGNORECASE).strip()

    cleaned = cleaned.replace("[]", "").replace("{}", "").strip()
    cleaned = re.sub(r"(?im)^\s*\[\s*system\s*\].*$", "", cleaned).strip()

    if not cleaned:
        loc = (location_fallback or "").strip()
        if loc:
            return f"{loc}\n\nЧто делаете дальше?"
        return "Что делаете дальше?"

    if re.fullmatch(r"[\[\]{}\s]+", cleaned):
        loc = (location_fallback or "").strip()
        if loc:
            return f"{loc}\n\nЧто делаете дальше?"
        return "Что делаете дальше?"

    return cleaned
