from __future__ import annotations

from copy import deepcopy

from app.rules.character_catalog import resolve_race
from app.web.http_routes import _build_race_features


def _effective_aasimar_with_subrace(subrace_key: str) -> dict:
    race = resolve_race("aasimar")
    assert race is not None
    base = deepcopy(race)
    subrace = next(
        (
            item
            for item in (base.get("subraces") or [])
            if isinstance(item, dict) and str(item.get("key") or "").strip().lower() == subrace_key
        ),
        None,
    )
    assert subrace is not None

    eff = dict(base)
    eff["traits"] = [*(base.get("traits") or []), *((subrace.get("traits") or []))]
    eff["asi"] = [*(base.get("asi") or []), *((subrace.get("asi") or []))]
    return eff


def test_protector_and_fallen_aasimar_persist_transformation_metadata() -> None:
    protector_features = _build_race_features(_effective_aasimar_with_subrace("aasimar_protector"))
    protector_transform = (protector_features.get("features") or {}).get("aasimar_transformation") or {}
    assert protector_transform.get("kind") == "protector"
    assert protector_transform.get("uses") == "per_long_rest"
    assert protector_transform.get("uses_max") == 1
    assert int(protector_transform.get("min_level") or 0) == 3
    assert int(protector_transform.get("fly_speed_ft") or 0) == 30
    assert ((protector_transform.get("bonus_damage") or {}).get("type") or "") == "radiant"
    assert "radiant" in {str(x).strip().lower() for x in (protector_features.get("resistances") or [])}
    assert "necrotic" in {str(x).strip().lower() for x in (protector_features.get("resistances") or [])}

    fallen_features = _build_race_features(_effective_aasimar_with_subrace("aasimar_fallen"))
    fallen_transform = (fallen_features.get("features") or {}).get("aasimar_transformation") or {}
    assert fallen_transform.get("kind") == "fallen"
    assert fallen_transform.get("uses") == "per_long_rest"
    assert fallen_transform.get("uses_max") == 1
    assert int(fallen_transform.get("min_level") or 0) == 3
    assert ((fallen_transform.get("bonus_damage") or {}).get("type") or "") == "necrotic"
    fear_cfg = fallen_transform.get("fear_on_transform") or {}
    assert int(fear_cfg.get("radius_ft") or 0) == 10
    assert str(fear_cfg.get("save_ability") or "").strip().lower() == "cha"


def test_scourge_aasimar_persists_structured_transformation_without_breaking_resistance() -> None:
    scourge_features = _build_race_features(_effective_aasimar_with_subrace("aasimar_scourge"))
    scourge_transform = (scourge_features.get("features") or {}).get("aasimar_transformation") or {}
    assert scourge_transform.get("kind") == "scourge"
    assert scourge_transform.get("uses") == "per_long_rest"
    assert scourge_transform.get("uses_max") == 1
    assert ((scourge_transform.get("end_of_turn_aura_damage") or {}).get("type") or "") == "radiant"
    assert ((scourge_transform.get("self_damage") or {}).get("type") or "") == "radiant"
    assert "radiant" in {str(x).strip().lower() for x in (scourge_features.get("resistances") or [])}
    assert "necrotic" in {str(x).strip().lower() for x in (scourge_features.get("resistances") or [])}
