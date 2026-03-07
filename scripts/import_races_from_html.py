#!/usr/bin/env python3
from __future__ import annotations

import html
import os
import pprint
import re
from pathlib import Path
from typing import Any

from app.rules.catalog_schema import normalize_race
from app.rules.character_catalog import BASE_RACE_CATALOG

DEFAULT_CATALOG_SOURCE_DIR = "/home/lus/code/game_resources/catalog_source"
OUTPUT_MODULE_PATH = Path("app/rules/races_imported.py")
DEFAULT_NOTES_RU = "Импортировано из внешнего источника, требует проверки мастером"
DEFAULT_SOURCE = "external resources"


def _slug(value: Any) -> str:
    return re.sub(r"\s+", "_", str(value or "").strip().lower())


def _key_from_dirname(dirname: str) -> str:
    match = re.match(r"^\d+-(.+)$", dirname.strip())
    if not match:
        return ""
    tail = match.group(1).strip().lower()
    if not tail:
        return ""
    return tail.replace("-", "_")


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _strip_tags(text: str) -> str:
    text = re.sub(r"<\s*br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .\n\t")


def _extract_name_ru(page_html: str, fallback: str) -> str:
    title_match = re.search(r"<title>(.*?)</title>", page_html, flags=re.IGNORECASE | re.DOTALL)
    if title_match:
        title_text = _strip_tags(title_match.group(1))
        if title_text:
            name = title_text.split("/", maxsplit=1)[0].strip()
            if name:
                return name

    h1_match = re.search(
        r"<h1[^>]*header-page_title[^>]*>.*?<a[^>]*>(.*?)</a>",
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if h1_match:
        h1_text = _strip_tags(h1_match.group(1)).strip()
        if h1_text:
            return h1_text

    return fallback


def _iter_race_html_dirs(source_root: Path) -> list[Path]:
    race_root = source_root / "race"
    if not race_root.is_dir():
        return []
    out: list[Path] = []
    for html_path in sorted(race_root.glob("**/index.html")):
        parent = html_path.parent
        if parent == race_root:
            continue
        out.append(parent)
    return out


def _normalize_imported_race(raw: dict[str, Any]) -> dict[str, Any] | None:
    normalized = normalize_race(raw)
    if not normalized:
        return None

    key = str(normalized.get("key") or "").strip()
    if not key:
        return None

    normalized["name_ru"] = str(raw.get("name_ru") or normalized.get("name_ru") or key).strip() or key
    normalized["size"] = str(normalized.get("size") or "medium").strip() or "medium"
    normalized["speed_ft"] = max(0, int(normalized.get("speed_ft") or 30))
    normalized["languages"] = list(normalized.get("languages") or ["common"]) or ["common"]
    normalized["asi"] = list(normalized.get("asi") or [])
    normalized["traits"] = list(normalized.get("traits") or [])
    normalized["subraces"] = list(normalized.get("subraces") or [])
    normalized["notes_ru"] = DEFAULT_NOTES_RU
    normalized["source"] = DEFAULT_SOURCE
    return normalized


def _build_race_payload(page_html: str, race_key: str) -> dict[str, Any]:
    name_ru = _extract_name_ru(page_html, race_key)
    return {
        "key": race_key,
        "name_ru": name_ru,
        "description_ru": "",
        "size": "medium",
        "speed_ft": 30,
        "languages": ["common"],
        "asi": [],
        "traits": [],
        "subraces": [],
        "notes_ru": DEFAULT_NOTES_RU,
        "source": DEFAULT_SOURCE,
        "tags": [],
    }


def _render_output_module(imported: list[dict[str, Any]]) -> str:
    payload = pprint.pformat(imported, width=120, sort_dicts=False)
    return (
        "from __future__ import annotations\n\n"
        "from typing import Any\n\n"
        "# Auto-generated from external resources via scripts/import_races_from_html.py\n"
        f"IMPORTED_RACE_CATALOG: list[dict[str, Any]] = {payload}\n"
    )


def main() -> int:
    source_dir = Path(os.getenv("CATALOG_SOURCE_DIR", DEFAULT_CATALOG_SOURCE_DIR)).expanduser()

    if not source_dir.is_dir():
        print(f"Catalog source dir not found: {source_dir}")
        return 1

    base_keys = {_slug(item.get("key")) for item in BASE_RACE_CATALOG if isinstance(item, dict)}

    imported: list[dict[str, Any]] = []
    skipped_existing = 0

    for article_dir in _iter_race_html_dirs(source_dir):
        race_key = _key_from_dirname(article_dir.name)
        if not race_key:
            continue
        if race_key in base_keys:
            skipped_existing += 1
            continue

        page_html = _read_text(article_dir / "index.html")
        if not page_html:
            continue

        race_raw = _build_race_payload(page_html, race_key)
        race = _normalize_imported_race(race_raw)
        if race:
            imported.append(race)

    imported.sort(key=lambda item: str(item.get("key") or ""))

    output_path = Path(__file__).resolve().parents[1] / OUTPUT_MODULE_PATH
    output_path.write_text(_render_output_module(imported), encoding="utf-8")

    print(f"Imported races written:  {len(imported)}")
    print(f"Skipped base races:      {skipped_existing}")
    print(f"Output module:           {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
