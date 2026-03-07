#!/usr/bin/env python3
from __future__ import annotations

import ast
import copy
import html
import os
import pprint
import re
from pathlib import Path
from typing import Any

from app.rules.catalog_schema import normalize_race
from app.rules.character_catalog import BASE_RACE_CATALOG

DEFAULT_CATALOG_SOURCE_DIR = "/home/lus/code/game_resources/catalog_source"
SOURCE_LABEL = "game_resources/catalog_source"
NOTES_LABEL_RU = "Импортировано автоматически, требует ревью"
MERGE_FIELDS: tuple[str, ...] = (
    "name_ru",
    "size",
    "speed_ft",
    "languages",
    "asi",
    "traits",
    "subraces",
    "notes_ru",
    "source",
)

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


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _canonical_catalog_path() -> Path:
    return _repo_root() / "app" / "rules" / "character_catalog.py"


def _normalize_imported_race(raw: dict[str, Any]) -> dict[str, Any] | None:
    normalized = normalize_race(raw)
    if not normalized:
        return None

    race_id = str(normalized.get("key") or "").strip()
    normalized["name_ru"] = str(raw.get("name_ru") or normalized.get("name_ru") or race_id).strip() or race_id
    normalized["notes_ru"] = str(raw.get("notes_ru") or NOTES_LABEL_RU).strip() or NOTES_LABEL_RU
    normalized["source"] = str(raw.get("source") or normalized.get("source") or SOURCE_LABEL).strip() or SOURCE_LABEL
    return normalized


def _merge_canonical_races(
    *,
    canonical: list[dict[str, Any]],
    imported: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int, int]:
    merged = [copy.deepcopy(item) for item in canonical if isinstance(item, dict)]
    by_key: dict[str, int] = {}
    for idx, race in enumerate(merged):
        race_key = _slug(race.get("key") or race.get("id"))
        if race_key and race_key not in by_key:
            by_key[race_key] = idx

    updated = 0
    added = 0
    for race in imported:
        race_key = _slug(race.get("key") or race.get("id"))
        if not race_key:
            continue
        if race_key in by_key:
            current = merged[by_key[race_key]]
            for field in MERGE_FIELDS:
                if field == "name_ru":
                    current[field] = str(race.get(field) or race_key).strip() or race_key
                else:
                    current[field] = copy.deepcopy(race.get(field))
            updated += 1
            continue

        new_item = copy.deepcopy(race)
        new_item["key"] = race_key
        new_item["name_ru"] = str(new_item.get("name_ru") or race_key).strip() or race_key
        merged.append(new_item)
        by_key[race_key] = len(merged) - 1
        added += 1

    return merged, updated, added


def _render_race_catalog_block(races: list[dict[str, Any]]) -> str:
    payload = pprint.pformat(races, width=120, sort_dicts=False)
    return f"BASE_RACE_CATALOG: list[dict[str, Any]] = {payload}"


def _replace_base_race_catalog(path: Path, races: list[dict[str, Any]]) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines = source.splitlines(keepends=True)
    block_start: int | None = None
    block_end: int | None = None

    for node in tree.body:
        target_name: str | None = None
        if isinstance(node, ast.Assign):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "BASE_RACE_CATALOG":
                    target_name = "BASE_RACE_CATALOG"
                    break
        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name) and node.target.id == "BASE_RACE_CATALOG":
                target_name = "BASE_RACE_CATALOG"

        if target_name:
            block_start = node.lineno - 1
            block_end = node.end_lineno
            break

    if block_start is None or block_end is None:
        raise RuntimeError(f"BASE_RACE_CATALOG not found in {path}")

    replacement = _render_race_catalog_block(races)
    replacement_lines = [line + "\n" for line in replacement.splitlines()]
    new_lines = lines[:block_start] + replacement_lines + lines[block_end:]
    path.write_text("".join(new_lines), encoding="utf-8")


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
    catalog_path = _canonical_catalog_path()

    if not source_dir.is_dir():
        print(f"Catalog source dir not found: {source_dir}")
        return 1

    imported: list[dict[str, Any]] = []

    for article_dir in _iter_race_html_dirs(source_dir):
        race_id = _entry_id_from_dir(article_dir)
        if not race_id:
            continue
        page_html = _read_text(article_dir / "index.html")
        if not page_html:
            continue
        race_raw = _build_race_payload(page_html, race_id)
        race = _normalize_imported_race(race_raw)
        if race:
            imported.append(race)

    imported.sort(key=lambda item: str(item.get("key") or ""))
    merged, updated, added = _merge_canonical_races(canonical=BASE_RACE_CATALOG, imported=imported)
    _replace_base_race_catalog(catalog_path, merged)

    print(f"Imported races from HTML: {len(imported)}")
    print(f"Updated existing races:   {updated}")
    print(f"Added new races:         {added}")
    print(f"Canonical catalog path:  {catalog_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
