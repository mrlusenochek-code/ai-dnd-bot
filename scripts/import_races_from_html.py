#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
from pathlib import Path
from typing import Any

from app.rules.catalog_loader import load_catalogs
from app.rules.character_catalog import BASE_CLASS_CATALOG, BASE_RACE_CATALOG

DEFAULT_CATALOG_SOURCE_DIR = "/home/lus/code/game_resources/catalog_source"
DEFAULT_PRIVATE_DATA_DIR = "./data_private"
GENERATED_RACES_FILE = "races_generated.json"
SOURCE_LABEL = "game_resources/catalog_source"
NOTES_LABEL_RU = "Импортировано автоматически, требует ревью"

STAT_ALIASES: list[tuple[str, str]] = [
    ("str", r"сил"),
    ("dex", r"ловкост"),
    ("con", r"телосложен"),
    ("int", r"интеллект"),
    ("wis", r"мудрост"),
    ("cha", r"харизм"),
]

LANGUAGE_ALIASES: list[tuple[str, str]] = [
    ("common", r"общ"),
    ("elvish", r"эльф"),
    ("dwarvish", r"дварф"),
    ("orc", r"орк"),
    ("draconic", r"дракон"),
    ("goblin", r"гоблин"),
    ("gnomish", r"гном"),
    ("halfling", r"полурос"),
    ("giant", r"великан"),
    ("primordial", r"первичн"),
    ("abyssal", r"бездн"),
    ("infernal", r"инфернал"),
    ("celestial", r"небесн"),
    ("sylvan", r"сильван"),
    ("undercommon", r"подземн"),
]


def _slug(value: Any) -> str:
    return re.sub(r"\s+", "_", str(value or "").strip().lower())


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


def _extract_desc_html(page_html: str) -> str:
    patterns = [
        r"<div class=['\"]desc card__article-body['\"][^>]*>(.*?)</div>\s*<ul class=['\"]params card__article-body['\"]",
        r"<div class=['\"]desc card__article-body['\"][^>]*>(.*?)</div>",
    ]
    for pattern in patterns:
        m = re.search(pattern, page_html, flags=re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1)
    return ""


def _entry_id_from_dir(path: Path) -> str:
    slug = re.sub(r"^\d+-", "", path.name.strip())
    return _slug(slug)


def _extract_names(page_html: str, race_id: str) -> tuple[str, str | None]:
    m = re.search(r"class=['\"]item-link['\"][^>]*>(.*?)</a>", page_html, flags=re.IGNORECASE | re.DOTALL)
    if m:
        title_text = _strip_tags(m.group(1))
        bracket_match = re.match(r"^(.*?)\s*\[([^\]]+)\]\s*$", title_text)
        if bracket_match:
            name_ru = bracket_match.group(1).strip() or race_id
            name_en = bracket_match.group(2).strip() or None
            return name_ru, name_en
        if title_text:
            return title_text, None

    m = re.search(r"<title>(.*?)</title>", page_html, flags=re.IGNORECASE | re.DOTALL)
    if m:
        title = _strip_tags(m.group(1))
        parts = [part.strip() for part in title.split("/") if part.strip()]
        if parts:
            return parts[0], None
    return race_id, None


def _extract_feature_section(desc_html: str) -> str:
    start = re.search(r"<h[23][^>]*>.*?Особенности.*?</h[23]>", desc_html, flags=re.IGNORECASE | re.DOTALL)
    if start:
        tail = desc_html[start.start() :]
    else:
        first_asi = re.search(r"Увеличение\s+характеристик", desc_html, flags=re.IGNORECASE)
        if not first_asi:
            return desc_html
        tail = desc_html[first_asi.start() :]

    stop = re.search(
        r"(?:id=['\"](?:podrasy|raznovidnosti)['\"]|>\s*(?:Подрасы|Разновидности)\s*<)",
        tail,
        flags=re.IGNORECASE,
    )
    if stop:
        return tail[: stop.start()]
    return tail


def _extract_labeled_paragraphs(fragment_html: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in re.finditer(r"<p[^>]*>(.*?)</p>", fragment_html, flags=re.IGNORECASE | re.DOTALL):
        inner = m.group(1)
        strong_match = re.match(
            r"^\s*(?:<(?:em|i)[^>]*>\s*)?<strong[^>]*>(.*?)</strong>(?:\s*</(?:em|i)>)?\s*[:.]?\s*(.*)$",
            inner,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if not strong_match:
            continue
        label = _strip_tags(strong_match.group(1)).strip(" .:-")
        if not label:
            continue
        description = _strip_tags(strong_match.group(2))
        if not description:
            description = _strip_tags(inner)
            if description.lower().startswith(label.lower()):
                description = description[len(label) :].strip(" .:-")
        if description:
            out.append((label, description))
    return out


def _extract_speed_ft(text: str) -> int | None:
    m = re.search(r"(\d+)\s*фут", text, flags=re.IGNORECASE)
    if not m:
        return None
    try:
        return max(0, int(m.group(1)))
    except ValueError:
        return None


def _extract_size(size_text: str) -> str | None:
    text = size_text.lower()
    if "маленьк" in text:
        return "small"
    if "больш" in text:
        return "large"
    if "средн" in text:
        return "medium"
    return None


def _extract_asi(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for stat, pattern in STAT_ALIASES:
        m = re.search(pattern + r"[^\d]{0,40}(\d+)", text, flags=re.IGNORECASE)
        if not m:
            continue
        try:
            bonus = int(m.group(1))
        except ValueError:
            continue
        if stat in seen:
            continue
        out.append({"stat": stat, "bonus": bonus})
        seen.add(stat)
    return out


def _extract_languages(text: str) -> list[str]:
    out: list[str] = []
    lower = text.lower()
    for key, pattern in LANGUAGE_ALIASES:
        if re.search(pattern, lower, flags=re.IGNORECASE) and key not in out:
            out.append(key)
    return out


def _make_trait(label: str, description: str) -> dict[str, Any]:
    key = _slug(label)
    if not key:
        key = f"trait_{abs(hash(label)) % 100000}"
    return {
        "key": key,
        "name_ru": label,
        "description_ru": description,
    }


def _extract_subraces(desc_html: str) -> list[dict[str, Any]]:
    marker = re.search(
        r"(?:id=['\"](?:podrasy|raznovidnosti)['\"]|>\s*(?:Подрасы|Разновидности)\s*<)",
        desc_html,
        flags=re.IGNORECASE,
    )
    if not marker:
        return []

    tail = desc_html[marker.end() :]
    out: list[dict[str, Any]] = []
    block_pattern = (
        r"<h2[^>]*bigSectionTitle[^>]*>(.*?)</h2>\s*<div class=['\"]hide-wrapper['\"][^>]*>(.*?)</div>"
    )
    for block in re.finditer(block_pattern, tail, flags=re.IGNORECASE | re.DOTALL):
        name_ru = _strip_tags(block.group(1))
        if not name_ru:
            continue
        if name_ru.lower() == "homebrew":
            continue

        body_html = block.group(2)
        pairs = _extract_labeled_paragraphs(body_html)
        traits = [_make_trait(label, description) for label, description in pairs]

        asi: list[dict[str, Any]] = []
        speed_ft: int | None = None
        for label, description in pairs:
            low = label.lower()
            if "увеличение характеристик" in low:
                asi = _extract_asi(description)
            if "скорость" in low:
                speed_ft = _extract_speed_ft(description)

        out.append(
            {
                "key": _slug(name_ru),
                "name_ru": name_ru,
                "traits": traits,
                "asi": asi,
                **({"speed_ft": speed_ft} if speed_ft is not None else {}),
            }
        )
    return out


def _build_race_payload(page_html: str, race_id: str) -> dict[str, Any]:
    name_ru, name_en = _extract_names(page_html, race_id)
    desc_html = _extract_desc_html(page_html)
    feature_html = _extract_feature_section(desc_html)
    labels = _extract_labeled_paragraphs(feature_html)

    asi: list[dict[str, Any]] = []
    size = "medium"
    speed_ft = 30
    languages: list[str] = []
    traits: list[dict[str, Any]] = []

    for label, description in labels:
        low = label.lower()
        traits.append(_make_trait(label, description))
        if "увеличение характеристик" in low:
            parsed = _extract_asi(description)
            if parsed:
                asi = parsed
        elif low in {"размер", "size"}:
            parsed = _extract_size(description)
            if parsed:
                size = parsed
        elif "скорость" in low:
            parsed = _extract_speed_ft(description)
            if parsed is not None:
                speed_ft = parsed
        elif low in {"языки", "язык", "languages"}:
            parsed = _extract_languages(description)
            if parsed:
                languages = parsed

    subraces = _extract_subraces(desc_html)

    race: dict[str, Any] = {
        "id": race_id,
        "key": race_id,
        "name_ru": (name_ru or race_id).strip(),
        "name": name_en,
        "description_ru": _strip_tags(desc_html[:4000]),
        "size": size,
        "speed_ft": speed_ft,
        "languages": languages,
        "asi": asi,
        "traits": traits,
        "subraces": subraces,
        "notes_ru": NOTES_LABEL_RU,
        "source": SOURCE_LABEL,
        "source_ru": SOURCE_LABEL,
    }
    return race


def _write_json(path: Path, payload: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _existing_race_ids() -> set[str]:
    _classes, races = load_catalogs(base_classes=BASE_CLASS_CATALOG, base_races=BASE_RACE_CATALOG)
    ids: set[str] = set()
    for race in races:
        key = _slug(race.get("key") or race.get("id"))
        if key:
            ids.add(key)
    return ids


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


def main() -> int:
    source_dir = Path(os.getenv("CATALOG_SOURCE_DIR", DEFAULT_CATALOG_SOURCE_DIR)).expanduser()
    private_dir = Path(os.getenv("DNDSU_PRIVATE_DATA_DIR", DEFAULT_PRIVATE_DATA_DIR)).expanduser()
    output_path = private_dir / GENERATED_RACES_FILE

    if not source_dir.is_dir():
        print(f"Catalog source dir not found: {source_dir}")
        return 1

    existing_ids = _existing_race_ids()

    # If generated file already exists, allow regenerating those ids in-place.
    if output_path.exists() and output_path.is_file():
        try:
            existing_generated = json.loads(output_path.read_text(encoding="utf-8"))
            if isinstance(existing_generated, list):
                for item in existing_generated:
                    if not isinstance(item, dict):
                        continue
                    rid = _slug(item.get("id") or item.get("key"))
                    if rid:
                        existing_ids.discard(rid)
        except (OSError, json.JSONDecodeError):
            pass

    imported: list[dict[str, Any]] = []
    skipped = 0

    for article_dir in _iter_race_html_dirs(source_dir):
        race_id = _entry_id_from_dir(article_dir)
        if not race_id:
            continue
        if race_id in existing_ids:
            skipped += 1
            continue
        page_html = _read_text(article_dir / "index.html")
        if not page_html:
            continue
        race = _build_race_payload(page_html, race_id)
        if not str(race.get("name_ru") or "").strip():
            race["name_ru"] = race_id
        imported.append(race)

    imported.sort(key=lambda item: str(item.get("id") or item.get("key") or ""))
    _write_json(output_path, imported)

    print(f"Generated races: {len(imported)} -> {output_path}")
    print(f"Skipped existing ids: {skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
