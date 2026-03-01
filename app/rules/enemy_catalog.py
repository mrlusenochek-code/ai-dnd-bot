from __future__ import annotations

import html
import re
from dataclasses import asdict, dataclass

_STAT_KEYS = ("str", "dex", "con", "int", "wis", "cha")
_TITLE_TO_STAT = {
    "сила": "str",
    "ловкость": "dex",
    "телосложение": "con",
    "интеллект": "int",
    "мудрость": "wis",
    "харизма": "cha",
}


@dataclass(frozen=True)
class EnemyDef:
    key: str
    name_ru: str
    name_en: str
    cr: str
    xp: int | None
    ac: int | None
    hp_avg: int | None
    hp_formula: str | None
    stats: dict[str, int]
    environments: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _strip_tags(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    unescaped = html.unescape(without_tags)
    return re.sub(r"\s+", " ", unescaped).strip()


def normalize_cr(value: str) -> str:
    normalized = html.unescape(value)
    normalized = normalized.replace("\\", "/")
    normalized = normalized.replace("−", "-")
    normalized = normalized.replace(",", ".")
    return re.sub(r"\s+", "", normalized).strip()


def parse_xp(value: str) -> int | None:
    match = re.search(r"(\d[\d\s]*)", html.unescape(value))
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    return int(digits) if digits else None


def normalize_dice(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = html.unescape(value)
    normalized = normalized.replace("К", "d").replace("к", "d")
    normalized = normalized.replace("−", "-")
    normalized = re.sub(r"\s+", " ", normalized).strip()
    normalized = re.sub(r"(\d)\s*[dD]\s*(\d)", r"\1d\2", normalized)
    return normalized or None


def split_environments(value: str | None) -> list[str]:
    if not value:
        return []
    parts = [part.strip() for part in html.unescape(value).split(",")]
    return [part for part in parts if part]


def _find_label_li(html_text: str, label: str) -> str | None:
    pattern = re.compile(
        rf"<li[^>]*>\s*<strong>\s*{re.escape(label)}\s*</strong>\s*(.*?)</li>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(html_text)
    return match.group(1) if match else None


def _extract_names(html_text: str) -> tuple[str, str]:
    title_match = re.search(r"data-copy=\"([^\"]+)\"", html_text)
    if title_match:
        copy_value = html.unescape(title_match.group(1)).strip()
        pair_match = re.match(r"^(.*?)\s*\[(.*?)\]\s*$", copy_value)
        if pair_match:
            return pair_match.group(1).strip(), pair_match.group(2).strip()
        if copy_value:
            return copy_value, ""

    meta_match = re.search(r"content=\"«\s*([^\(\"]+)\(([^\)\"]+)\)\s*»", html_text)
    if meta_match:
        return html.unescape(meta_match.group(1)).strip(), html.unescape(meta_match.group(2)).strip()

    return "", ""


def _extract_ac(html_text: str) -> int | None:
    raw = _find_label_li(html_text, "Класс Доспеха")
    if not raw:
        return None
    text = _strip_tags(raw)
    match = re.search(r"\d+", text)
    return int(match.group(0)) if match else None


def _extract_hp(html_text: str) -> tuple[int | None, str | None]:
    raw = _find_label_li(html_text, "Хиты")
    if not raw:
        return None, None

    text = _strip_tags(raw)
    avg_match = re.search(r"\d+", text)
    hp_avg = int(avg_match.group(0)) if avg_match else None

    formula_match = re.search(r"\(([^)]*)\)", text)
    hp_formula = normalize_dice(formula_match.group(1)) if formula_match else None
    return hp_avg, hp_formula


def _extract_cr_xp(html_text: str) -> tuple[str, int | None]:
    raw = _find_label_li(html_text, "Опасность")
    if not raw:
        return "", None

    text = _strip_tags(raw)
    cr_match = re.search(r"^\s*([^\s(]+)", text)
    cr = normalize_cr(cr_match.group(1)) if cr_match else ""

    xp_match = re.search(r"\(([^)]*опыта[^)]*)\)", text, flags=re.IGNORECASE)
    xp = parse_xp(xp_match.group(1)) if xp_match else None
    return cr, xp


def _extract_stats(html_text: str) -> dict[str, int]:
    stats = {key: 0 for key in _STAT_KEYS}
    abilities_match = re.search(r"<li[^>]*class=['\"][^'\"]*abilities[^'\"]*['\"][^>]*>(.*?)</li>", html_text, flags=re.DOTALL | re.IGNORECASE)
    if not abilities_match:
        return stats

    abilities_html = abilities_match.group(1)
    stat_matches = re.findall(
        r"<div\s+class=['\"]stat['\"][^>]*title=['\"]([^'\"]+)['\"][^>]*>\s*<div>.*?</div>\s*<div>\s*(\d+)",
        abilities_html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    for title, value in stat_matches:
        key = _TITLE_TO_STAT.get(title.strip().lower())
        if key:
            stats[key] = int(value)

    return stats


def _extract_environments(html_text: str) -> list[str]:
    raw = _find_label_li(html_text, "Местность обитания")
    if not raw:
        return []
    return split_environments(_strip_tags(raw))


def parse_enemy_html(html: str, *, key_hint: str) -> EnemyDef:
    name_ru, name_en = _extract_names(html)
    cr, xp = _extract_cr_xp(html)
    hp_avg, hp_formula = _extract_hp(html)

    return EnemyDef(
        key=key_hint,
        name_ru=name_ru,
        name_en=name_en,
        cr=cr,
        xp=xp,
        ac=_extract_ac(html),
        hp_avg=hp_avg,
        hp_formula=hp_formula,
        stats=_extract_stats(html),
        environments=_extract_environments(html),
    )
