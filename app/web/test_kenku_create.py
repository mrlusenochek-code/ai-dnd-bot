from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from app.test_helpers.race_create_helpers import kenku_base_payload as _base_payload
from app.test_helpers.race_create_helpers import setup_basic_create_mocks
from app.web import http_routes


def _setup_create_mocks(monkeypatch) -> None:
    setup_basic_create_mocks(monkeypatch, session_title="Test Session")


def test_kenku_create_requires_two_valid_distinct_skills_and_persists_features(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    response = asyncio.run(http_routes.api_character_create(_base_payload()))
    assert response.status_code == 200

    character = json.loads(response.body).get("character") or {}
    stats = character.get("stats") or {}
    race_features = character.get("race_features") or {}

    assert int(stats.get("dex") or 0) == 60
    assert int(stats.get("wis") or 0) == 55

    assert (race_features.get("languages") or []) == ["common", "auran"]

    prof = race_features.get("proficiencies") or {}
    skills = [str(x).strip().lower() for x in (prof.get("skills") or [])]
    assert "stealth" in skills
    assert "deception" in skills

    features = race_features.get("features") or {}
    assert isinstance(features.get("expert_forgery"), dict)
    mimicry = features.get("mimicry") or {}
    assert isinstance(mimicry, dict)
    counter = mimicry.get("counter_check") or {}
    assert str(counter.get("ability") or "").strip().lower() == "wis"
    assert str(counter.get("skill") or "").strip().lower() == "insight"

    choices = race_features.get("choices") or {}
    assert (choices.get("skills") or []) == ["stealth", "deception"]


def test_kenku_create_rejects_invalid_skill_choices(monkeypatch) -> None:
    _setup_create_mocks(monkeypatch)

    payload_none = _base_payload()
    payload_none["race_choices"]["skills"] = []
    try:
        asyncio.run(http_routes.api_character_create(payload_none))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc)).lower()
        assert "skill" in detail

    payload_one = _base_payload()
    payload_one["race_choices"]["skills"] = ["stealth"]
    try:
        asyncio.run(http_routes.api_character_create(payload_one))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc)).lower()
        assert "skill" in detail or "exactly 2" in detail

    payload_dupes = _base_payload()
    payload_dupes["race_choices"]["skills"] = ["stealth", "stealth"]
    try:
        asyncio.run(http_routes.api_character_create(payload_dupes))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc)).lower()
        assert "distinct" in detail or "skill" in detail

    payload_bad = _base_payload()
    payload_bad["race_choices"]["skills"] = ["stealth", "arcana"]
    try:
        asyncio.run(http_routes.api_character_create(payload_bad))
        assert False, "Expected HTTPException"
    except Exception as exc:  # noqa: BLE001
        detail = str(getattr(exc, "detail", exc)).lower()
        assert "invalid skill choice" in detail or "skill" in detail


def test_kenku_ui_texts_present_in_session_template() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Обучение кенку: владение навыками" in template
    assert "Искусный подлог: вы умеете копировать почерк/рисунки" in template
    assert "Подражание: вы имитируете звуки/голоса" in template
