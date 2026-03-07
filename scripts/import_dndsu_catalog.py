#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any


DEFAULT_DNDSU_DATA_DIR = "/home/lus/downloads/dndsu-full/dnd.su"
DEFAULT_PRIVATE_DATA_DIR = "./data_private"


def _slug(value: Any) -> str:
    return str(value or "").strip().lower().replace(" ", "_")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _strip_tags(text: str) -> str:
    cleaned = re.sub(r"<[^>]+>", " ", text)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _title_parts(html: str) -> tuple[str, str]:
    m = re.search(r"<title>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return "", ""
    title = _strip_tags(m.group(1))
    parts = [p.strip() for p in title.split("/") if p.strip()]
    if not parts:
        return "", ""
    name_ru = parts[0]
    source = parts[-1] if len(parts) >= 2 else ""
    return name_ru, source


def _source_from_html(html: str, fallback: str) -> str:
    m = re.search(
        r"<li>\s*<strong>\s*Источник:\s*</strong>\s*[«\"]?\s*(?:<span>)?([^<»\"]+)",
        html,
        flags=re.IGNORECASE,
    )
    if m:
        source = _strip_tags(m.group(1))
        if source:
            return source
    return fallback


def _extract_class_hit_die(html: str, default: int = 8) -> int:
    head = html.split("<div class='comment__body", 1)[0]
    m = re.search(r"Кость\s*Хитов[^\d]{0,60}1\s*[кk]\s*(\d+)", head, flags=re.IGNORECASE)
    if not m:
        m = re.search(r"hit\s*die[^\d]{0,60}d\s*(\d+)", head, flags=re.IGNORECASE)
    if not m:
        return default
    try:
        return max(1, int(m.group(1)))
    except ValueError:
        return default


def _extract_race_speed(html: str, default: int = 30) -> int:
    head = html.split("<div class='comment__body", 1)[0]
    patterns = [
        r"скорость\s+ходьбы\s+составляет\s*(\d+)\s*фут",
        r"скорость\s+ходьбы\s*[—-]\s*(\d+)\s*фут",
        r"базовая\s+скорость\s+ходьбы\s+увеличивается\s+до\s*(\d+)\s*фут",
    ]
    for pattern in patterns:
        m = re.search(pattern, head, flags=re.IGNORECASE)
        if m:
            try:
                return max(0, int(m.group(1)))
            except ValueError:
                return default
    return default


def _iter_article_dirs(base_dir: Path, rel_dirs: list[str]) -> list[Path]:
    out: list[Path] = []
    for rel_dir in rel_dirs:
        root = base_dir / rel_dir
        if not root.is_dir():
            continue
        for item in sorted(root.iterdir()):
            if not item.is_dir():
                continue
            if (item / "index.html").is_file():
                out.append(item)
    return out


def _entry_id_from_dir(path: Path) -> str:
    slug = re.sub(r"^\d+-", "", path.name.strip())
    return _slug(slug)


def _build_classes(base_dir: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for article_dir in _iter_article_dirs(base_dir, ["class", "homebrew/class"]):
        class_id = _entry_id_from_dir(article_dir)
        if not class_id or class_id in seen:
            continue
        html = _read_text(article_dir / "index.html")
        if not html:
            continue
        name_ru, source_from_title = _title_parts(html)
        source = _source_from_html(html, source_from_title or "dnd.su")
        items.append(
            {
                "id": class_id,
                "name_ru": name_ru or class_id,
                "source": source,
                "hit_die": _extract_class_hit_die(html, default=8),
                "traits": [],
                "features": [],
                "spells": [],
                "spellcasting": {},
            }
        )
        seen.add(class_id)
    return items


def _build_races(base_dir: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for article_dir in _iter_article_dirs(base_dir, ["race", "multiverse/race", "homebrew/race"]):
        race_id = _entry_id_from_dir(article_dir)
        if not race_id or race_id in seen:
            continue
        html = _read_text(article_dir / "index.html")
        if not html:
            continue
        name_ru, source_from_title = _title_parts(html)
        source = _source_from_html(html, source_from_title or "dnd.su")
        items.append(
            {
                "id": race_id,
                "name_ru": name_ru or race_id,
                "source": source,
                "speed_ft": _extract_race_speed(html, default=30),
                "traits": [],
                "features": [],
                "spells": [],
            }
        )
        seen.add(race_id)
    return items


def _write_json(path: Path, payload: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    dndsu_dir = Path(os.getenv("DNDSU_DATA_DIR", DEFAULT_DNDSU_DATA_DIR)).expanduser()
    private_dir = Path(os.getenv("DNDSU_PRIVATE_DATA_DIR", DEFAULT_PRIVATE_DATA_DIR)).expanduser()

    if not dndsu_dir.is_dir():
        print(f"DNDSU_DATA_DIR not found: {dndsu_dir}")
        return 1

    classes = sorted(_build_classes(dndsu_dir), key=lambda x: str(x.get("id") or ""))
    races = sorted(_build_races(dndsu_dir), key=lambda x: str(x.get("id") or ""))

    classes_path = private_dir / "dndsu_classes.json"
    races_path = private_dir / "dndsu_races.json"
    _write_json(classes_path, classes)
    _write_json(races_path, races)

    print(f"Imported classes: {len(classes)} -> {classes_path}")
    print(f"Imported races:   {len(races)} -> {races_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
