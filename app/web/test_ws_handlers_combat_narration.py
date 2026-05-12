from __future__ import annotations

from app.web import ws_handlers


def test_resolved_live_combat_action_skips_gm_narration() -> None:
    assert ws_handlers._should_skip_gm_narration_for_resolved_combat_action(
        "combat_attack",
        {"status": "ok", "open": True, "lines": [{"text": "Атака: Hero → Goblin"}]},
    ) is True


def test_quick_combat_narration_for_attack_and_auto_two_weapon() -> None:
    attack_patch = {
        "status": "ok",
        "open": True,
        "lines": [
            {"text": "Атака: фы → Разбойник"},
        ],
    }
    assert ws_handlers._quick_combat_narration_text("combat_attack", attack_patch, fallback_actor="фы") == "⚔ фы атакует Разбойник."

    twf_patch = {
        "status": "ok",
        "open": True,
        "lines": [
            {"text": "Атака: фы → Разбойник"},
            {"text": "Бой двумя оружиями: бонусная атака второй рукой выполнена автоматически.", "muted": True},
            {"text": "Бонусная атака второй рукой: фы → Разбойник"},
        ],
    }
    assert (
        ws_handlers._quick_combat_narration_text("combat_attack", twf_patch, fallback_actor="фы")
        == "⚔ фы атакует двумя оружиями: основной удар и удар второй рукой."
    )


def test_quick_combat_narration_suppressed_after_victory() -> None:
    victory_patch = {
        "status": "Бой завершён",
        "open": False,
        "lines": [
            {"text": "Атака: фы → Разбойник"},
            {"text": "Победа: противники повержены.", "muted": True},
        ],
    }
    assert ws_handlers._combat_patch_ends_battle(victory_patch) is True
    assert ws_handlers._quick_combat_narration_text("combat_attack", victory_patch, fallback_actor="фы") == ""
    assert ws_handlers._should_generate_post_victory_gm_narration("combat_attack", victory_patch) is True


def test_resolved_combat_attack_without_victory_does_not_request_post_victory_gm() -> None:
    attack_patch = {
        "status": "ok",
        "open": True,
        "lines": [
            {"text": "Атака: фы → Разбойник"},
        ],
    }
    assert ws_handlers._should_generate_post_victory_gm_narration("combat_attack", attack_patch) is False
    assert ws_handlers._quick_combat_narration_text("combat_attack", attack_patch, fallback_actor="фы") == "⚔ фы атакует Разбойник."


def test_quick_combat_narration_for_dodge_dash_and_end_turn() -> None:
    assert (
        ws_handlers._quick_combat_narration_text(
            "combat_dodge",
            {"lines": [{"text": "Уклонение: фы (до следующего хода)"}]},
            fallback_actor="фы",
        )
        == "🛡 фы уходит в защиту."
    )
    assert (
        ws_handlers._quick_combat_narration_text(
            "combat_dash",
            {"lines": [{"text": "Рывок: фы (до следующего хода)"}]},
            fallback_actor="фы",
        )
        == "🏃 фы делает рывок."
    )
    assert (
        ws_handlers._quick_combat_narration_text(
            "combat_end_turn",
            {"lines": [{"text": "Ход передан: Goblin", "muted": True}]},
            fallback_actor="фы",
        )
        == "⏭ фы завершает ход."
    )


def test_unrecognized_text_in_combat_does_not_force_skip() -> None:
    assert ws_handlers._should_skip_gm_narration_for_resolved_combat_action(
        "",
        {"status": "ok", "open": True, "lines": [{"text": "Что-то произошло"}]},
    ) is False
    assert ws_handlers._should_skip_gm_narration_for_resolved_combat_action(
        None,
        {"status": "ok", "open": True, "lines": [{"text": "Что-то произошло"}]},
    ) is False


def test_out_of_combat_or_missing_patch_does_not_force_skip() -> None:
    assert ws_handlers._should_skip_gm_narration_for_resolved_combat_action("combat_attack", None) is False
    assert ws_handlers._should_skip_gm_narration_for_resolved_combat_action(None, None) is False
    assert ws_handlers._combat_patch_ends_battle(None) is False
    assert ws_handlers._should_generate_post_victory_gm_narration("combat_attack", None) is False
    assert ws_handlers._quick_combat_narration_text(None, None, fallback_actor="фы") == ""
