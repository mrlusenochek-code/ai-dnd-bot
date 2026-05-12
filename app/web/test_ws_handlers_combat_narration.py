from __future__ import annotations

import asyncio
from types import SimpleNamespace

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


def test_sanitize_gm_response_text_strips_machine_lines_for_player_text() -> None:
    raw = (
        "Ты добиваешься ответа от собеседника.\n"
        "@@INV_ADD(uid=1, name=\"Coin\")\n"
        "@@ZONE_SET(uid=1, zone=\"street\")\n"
        "@@CHECK {\"actor_uid\":1,\"kind\":\"skill\",\"name\":\"persuasion\",\"dc\":12}\n"
        "@@CHECK_RESULT {\"success\":true}\n"
        "Что делаете дальше?"
    )

    cleaned = ws_handlers._sanitize_gm_response_text(raw)

    assert "@@INV_ADD" not in cleaned
    assert "@@ZONE_SET" not in cleaned
    assert "@@CHECK" not in cleaned
    assert "@@CHECK_RESULT" not in cleaned
    assert "Ты добиваешься ответа от собеседника." in cleaned
    assert "Что делаете дальше?" in cleaned


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


def test_post_victory_gm_generation_sets_and_clears_processing_flag(monkeypatch) -> None:
    sess = SimpleNamespace(id="sess-1", title="Battle", settings={"phase": "turns", "story": {}}, is_active=True)
    player = SimpleNamespace(id="player-1", display_name="Игрок")
    character = SimpleNamespace(name="фы", stats={})
    broadcasts: list[tuple[str, str | None]] = []
    events: list[dict[str, object]] = []
    commits: list[str] = []

    class _FakeDb:
        async def commit(self) -> None:
            commits.append(str(sess.settings.get("phase")))

    async def _fake_get_character(_db, _sess_id, _player_id):
        return character

    async def _fake_generate(**_kwargs) -> str:
        assert sess.settings.get("phase") == "gm_pending"
        assert sess.settings.get("gm_pending_context") == "post_victory"
        return "Поле боя стихает."

    async def _fake_add_system_event(_db, _sess, text, **kwargs):
        events.append({"text": text, "result_json": kwargs.get("result_json")})

    async def _fake_broadcast_state(session_id, **_kwargs):
        broadcasts.append((session_id, sess.settings.get("phase")))

    monkeypatch.setattr(ws_handlers, "get_character", _fake_get_character)
    monkeypatch.setattr(ws_handlers, "_generate_combat_narration", _fake_generate)
    monkeypatch.setattr(ws_handlers, "add_system_event", _fake_add_system_event)
    monkeypatch.setattr(ws_handlers, "broadcast_state", _fake_broadcast_state)

    asyncio.run(
        ws_handlers._emit_post_victory_gm_narration(
            db=_FakeDb(),
            sess=sess,
            player=player,
            session_id="combat-victory",
            combat_action="combat_attack",
            combat_patch={"status": "Бой завершён", "open": False, "lines": [{"text": "Победа: враги повержены."}]},
            actor_label="фы",
            state_for_prompt=None,
        )
    )

    assert broadcasts[0] == ("combat-victory", "gm_pending")
    assert len(events) == 1
    assert events[0]["text"] == "🧙 GM: Поле боя стихает."
    result_json = events[0]["result_json"] or {}
    assert result_json.get("type") == "combat_chat_gm_reply"
    assert result_json.get("post_victory") is True
    assert sess.settings.get("phase") == "turns"
    assert sess.settings.get("gm_pending_context") is None
    assert broadcasts[-1] == ("combat-victory", "turns")


def test_combat_start_pending_context_is_exposed_and_can_be_cleared() -> None:
    sess = SimpleNamespace(settings={"phase": "turns"})

    ws_handlers.settings_set(sess, "gm_pending_context", "combat_start")
    ws_handlers._set_phase(sess, "gm_pending")
    assert ws_handlers._get_phase(sess) == "gm_pending"
    assert sess.settings.get("gm_pending_context") == "combat_start"

    ws_handlers.settings_set(sess, "gm_pending_context", None)
    ws_handlers._set_phase(sess, "turns")
    assert ws_handlers._get_phase(sess) == "turns"
    assert sess.settings.get("gm_pending_context") is None
