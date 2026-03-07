from __future__ import annotations

import json
from pathlib import Path

import pytest

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


def test_private_generated_races_have_ru_names() -> None:
    generated = Path("data_private/races_generated.json")
    if not generated.is_file():
        pytest.skip("data_private/races_generated.json not found")

    payload = json.loads(generated.read_text(encoding="utf-8"))
    assert isinstance(payload, list)

    for item in payload:
        assert isinstance(item, dict)
        race_id = str(item.get("id") or item.get("key") or "").strip()
        race_name_ru = str(item.get("name_ru") or "").strip()
        assert race_id
        assert race_name_ru
