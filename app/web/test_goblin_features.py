from __future__ import annotations

from pathlib import Path

from app.rules.character_catalog import resolve_race
from app.web import http_routes
from app.web.ws_gameplay import _detect_chat_combat_action


def test_build_race_features_persists_goblin_markers() -> None:
    goblin = resolve_race("goblin")
    assert isinstance(goblin, dict)

    race_features = http_routes._build_race_features(goblin)
    features = race_features.get("features") or {}

    fury = features.get("fury_of_the_small") or {}
    assert isinstance(fury, dict)
    assert str(fury.get("amount") or "").strip().lower() == "level"
    assert str(fury.get("uses") or "").strip().lower() == "per_short_or_long_rest"
    assert features.get("nimble_escape") is True


def test_goblin_feature_texts_are_present_in_session_template() -> None:
    template_path = Path(__file__).resolve().parents[0] / "templates" / "session.html"
    template = template_path.read_text(encoding="utf-8")

    assert "Разъярённая мелкота: когда наносите урон существу больше вас" in template
    assert "Шустрый побег: бонусным действием каждый ваш ход: Отход или Засада" in template


def test_detect_chat_action_for_fury_of_small_phrases() -> None:
    assert _detect_chat_combat_action("разъярённая мелкота") == "combat_fury_of_small"
    assert _detect_chat_combat_action("ярость мелкоты") == "combat_fury_of_small"
    assert _detect_chat_combat_action("выпускаю ярость") == "combat_fury_of_small"
    assert _detect_chat_combat_action("fury of the small") == "combat_fury_of_small"


def test_detect_chat_action_for_goblin_hide_phrase() -> None:
    assert _detect_chat_combat_action("ухожу в засаду") == "combat_hide"
    assert _detect_chat_combat_action("прячусь") == "combat_hide"
