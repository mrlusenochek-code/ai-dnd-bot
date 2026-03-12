from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from app.test_helpers.race_create_helpers import loxodon_base_payload as _base_payload
from app.test_helpers.race_create_helpers import setup_basic_create_mocks
from app.web import http_routes


def _setup_create_mocks(monkeypatch) -> None:
    setup_basic_create_mocks(monkeypatch, session_title="Test Session")


def test_loxodon_create_persists_expected_race_features(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)
    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("con") or 0) == 60
    assert int(stats.get("wis") or 0) == 55
    assert (race_features.get("languages") or []) == ["common", "loxodon"]

    saves = race_features.get("saves") or {}
    adv_conditions = {str(x).strip().lower() for x in (saves.get("advantage_conditions") or [])}
    assert {"charmed", "frightened"}.issubset(adv_conditions)

    natural_armor = race_features.get("natural_armor") or {}
    assert str(natural_armor.get("ac_formula") or "").strip().lower() == "12 + con_mod"
    assert bool(natural_armor.get("shield_applies")) is True
    assert bool(natural_armor.get("allow_when_armored_if_better")) is True

    carry = race_features.get("carry") or {}
    assert bool(carry.get("powerful_build")) is True

    features = race_features.get("features") or {}
    serenity = features.get("serenity") or {}
    assert serenity.get("type") == "save_advantage_vs_condition"
    assert serenity.get("conditions") == ["charmed", "frightened"]
    assert isinstance(features.get("trunk"), dict)
    assert isinstance(features.get("keen_smell"), dict)


def test_loxodon_ui_texts_present_in_session_template() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Спокойствие локсодонов: преимущество на спасброски от очарования/испуга" in template
    assert "Природный доспех: без брони КД = 12 + модиф. ТЕЛ; можно использовать, если броня хуже; щит работает" in template
    assert "Хобот: досягаемость 5 фт, переноска/толкать/тянуть, безоружный удар; нельзя держать оружие/щит, точные действия и соматику" in template
    assert "Обострённый нюх: преимущество на проверки Восприятия/Выживания/Расследования, основанные на запахе" in template
