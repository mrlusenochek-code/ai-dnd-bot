from app.rules.character_catalog import CLASS_CATALOG, PHB_CLASS_KEYS, PHB_RACE_KEYS, RACE_CATALOG


def test_class_catalog_keys_unique_and_contains_phb() -> None:
    keys = [str(item.get("key") or "") for item in CLASS_CATALOG]
    assert all(keys), "Every class entry must have non-empty key"
    assert len(keys) == len(set(keys)), "Class keys must be unique"
    assert set(PHB_CLASS_KEYS).issubset(set(keys)), "All PHB classes must exist in catalog"


def test_race_catalog_keys_unique_and_contains_phb() -> None:
    keys = [str(item.get("key") or "") for item in RACE_CATALOG]
    assert all(keys), "Every race entry must have non-empty key"
    assert len(keys) == len(set(keys)), "Race keys must be unique"
    assert set(PHB_RACE_KEYS).issubset(set(keys)), "All PHB races must exist in catalog"
