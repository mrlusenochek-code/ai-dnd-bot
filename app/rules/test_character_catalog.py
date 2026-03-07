from app.rules.character_catalog import CLASS_CATALOG, PHB_CLASS_KEYS, PHB_RACE_KEYS, RACE_CATALOG
from app.rules.character_catalog import EXTERNAL_RACE_CATALOG


def test_class_catalog_keys_unique_and_contains_phb() -> None:
    keys = [str(item.get("key") or "") for item in CLASS_CATALOG]
    assert all(keys), "Every class entry must have non-empty key"
    assert len(keys) == len(set(keys)), "Class keys must be unique"
    assert set(PHB_CLASS_KEYS).issubset(set(keys)), "All PHB classes must exist in catalog"


def test_artificer_exists_with_expected_hit_die() -> None:
    artificer = next((item for item in CLASS_CATALOG if str(item.get("key") or "") == "artificer"), None)
    assert artificer is not None
    assert int(artificer.get("hit_die") or 0) == 8


def test_race_catalog_keys_unique_and_contains_phb() -> None:
    keys = [str(item.get("key") or "") for item in RACE_CATALOG]
    assert all(keys), "Every race entry must have non-empty key"
    assert len(keys) == len(set(keys)), "Race keys must be unique"
    assert set(PHB_RACE_KEYS).issubset(set(keys)), "All PHB races must exist in catalog"


def test_imported_races_have_non_empty_name_ru() -> None:
    for race in EXTERNAL_RACE_CATALOG:
        assert str(race.get("name_ru") or "").strip(), f"Imported race has empty name_ru: {race.get('key')}"
