from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from app.rules.enemy_catalog import EnemyDef, parse_enemy_html


def _stable_key_from_dirname(dirname: str) -> str:
    match = re.match(r"^(\d+)-(.+)$", dirname)
    if not match:
        raise ValueError(f"Unexpected bestiary directory name: {dirname}")

    monster_id = match.group(1)
    raw_slug = match.group(2)
    slug = raw_slug.replace("-", "_")
    slug = re.sub(r"[^a-zA-Z0-9_]+", "_", slug)
    slug = re.sub(r"_+", "_", slug).strip("_").lower()
    return f"dndsu_{monster_id}_{slug}"


def _build_catalog(src_root: Path) -> list[EnemyDef]:
    bestiary_root = src_root / "bestiary"
    enemies: list[EnemyDef] = []

    for html_path in sorted(bestiary_root.glob("*/index.html")):
        dirname = html_path.parent.name
        key = _stable_key_from_dirname(dirname)
        html_text = html_path.read_text(encoding="utf-8")
        enemies.append(parse_enemy_html(html_text, key_hint=key))

    return enemies


def main() -> int:
    parser = argparse.ArgumentParser(description="Build compact DnD.su enemy catalog JSON")
    parser.add_argument("--src", required=True, help="Path to dnd.su root directory")
    parser.add_argument("--out", required=True, help="Output JSON file path")
    args = parser.parse_args()

    src_root = Path(args.src)
    out_path = Path(args.out)

    enemies = _build_catalog(src_root)
    payload = [enemy.to_dict() for enemy in enemies]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    print(f"Built {len(payload)} enemies -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
