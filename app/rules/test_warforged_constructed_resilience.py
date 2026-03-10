from app.rules.character_catalog import resolve_race
from app.web import http_routes, ws_handlers


def test_warforged_constructed_resilience_persists_hooks_and_markers() -> None:
    warforged = resolve_race("warforged")
    assert isinstance(warforged, dict)

    race_features = http_routes._build_race_features(warforged)
    resistances = {str(x).strip().lower() for x in (race_features.get("resistances") or [])}
    assert "poison" in resistances

    immunities = race_features.get("immunities") or {}
    immunity_conditions = {str(x).strip().lower() for x in (immunities.get("conditions") or [])}
    assert "diseased" in immunity_conditions
    assert "magic_sleep" in immunity_conditions

    needs = race_features.get("needs") or {}
    assert {str(x).strip().lower() for x in (needs.get("no_need") or [])} == {"eat", "drink", "breathe", "sleep"}

    features = race_features.get("features") or {}
    resilience = features.get("constructed_resilience") or {}
    assert resilience.get("cannot_be_magically_slept") is True

    assert ws_handlers._effective_save_mode("normal", race_features, "con", vs_tag="poisoned") == "advantage"
