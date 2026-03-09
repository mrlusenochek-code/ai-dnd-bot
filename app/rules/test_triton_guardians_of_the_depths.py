from app.rules.character_catalog import resolve_race
from app.web.http_routes import _build_race_features


def test_triton_guardians_of_the_depths_persist_cold_resistance_and_marker() -> None:
    triton = resolve_race("triton")
    assert isinstance(triton, dict)
    race_features = _build_race_features(triton)

    resistances = {str(x).strip().lower() for x in (race_features.get("resistances") or [])}
    assert "cold" in resistances

    features = race_features.get("features") or {}
    guardians = features.get("guardians_of_the_depths") or {}
    assert guardians.get("cold_resistance") is True
    assert guardians.get("deep_pressure_adapted") is True
