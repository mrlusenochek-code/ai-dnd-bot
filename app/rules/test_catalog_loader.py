from __future__ import annotations

import json

from app.rules.catalog_loader import load_catalogs
from app.rules.character_catalog import BASE_CLASS_CATALOG, BASE_RACE_CATALOG


def test_catalog_loader_merges_private_data(tmp_path, monkeypatch) -> None:
    private_dir = tmp_path / "data_private"
    private_dir.mkdir(parents=True, exist_ok=True)
    (private_dir / "dndsu_races.json").write_text(
        json.dumps(
            [
                {
                    "id": "swiftling",
                    "name_ru": "Стремник",
                    "source": "test",
                    "speed_ft": 40,
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("DNDSU_PRIVATE_DATA_DIR", str(private_dir))
    classes, races = load_catalogs(
        base_classes=BASE_CLASS_CATALOG,
        base_races=BASE_RACE_CATALOG,
    )

    assert classes
    swiftling = next((item for item in races if item.get("key") == "swiftling"), None)
    assert swiftling is not None
    assert int(swiftling.get("speed_ft") or 0) == 40
