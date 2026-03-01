from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.rules.enemy_catalog import EnemyDef, parse_enemy_html


def _normalize_slug(raw_slug: str) -> str:
    slug = raw_slug.replace("-", "_")
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_").lower()
    return slug or "unknown"


def _stable_key_from_dirname(dirname: str, html_text: str) -> str:
    match = re.match(r"^(\d+)-(.+)$", dirname)
    if match:
        monster_id = match.group(1)
        slug = _normalize_slug(match.group(2))
        return f"dndsu_{monster_id}_{slug}"

    id_only_match = re.match(r"^(\d+)$", dirname)
    if not id_only_match:
        raise ValueError(f"Unexpected bestiary directory name: {dirname}")

    monster_id = id_only_match.group(1)
    slug_match = re.search(rf"/(?:homebrew/)?bestiary/{monster_id}-([a-zA-Z0-9_-]+)/", html_text)
    slug = _normalize_slug(slug_match.group(1)) if slug_match else f"id_{monster_id}"
    return f"dndsu_{monster_id}_{slug}"


def _build_catalog(src_root: Path) -> list[EnemyDef]:
    bestiary_root = src_root / "bestiary"
    enemies: list[EnemyDef] = []

    for html_path in sorted(bestiary_root.glob("*/index.html")):
        dirname = html_path.parent.name
        html_text = html_path.read_text(encoding="utf-8")

        # быстрый фильтр “похоже на карточку монстра”
        if "data-copy=" not in html_text or "Класс Доспеха" not in html_text or "Опасность" not in html_text:
            continue

        key = _stable_key_from_dirname(dirname, html_text)
        enemies.append(parse_enemy_html(html_text, key_hint=key))

    return enemies


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DnD.su enemy catalog JSON")
    parser.add_argument("--src", required=True, help="Path to dnd.su root directory")
    parser.add_argument("--out", required=True, help="Output JSON file path")
    args = parser.parse_args()

    src_root = Path(args.src)
    out_path = Path(args.out)

    enemies = _build_catalog(src_root)
    payload = [enemy.to_dict() for enemy in enemies]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")

    print(f"Built {len(payload)} enemies -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
