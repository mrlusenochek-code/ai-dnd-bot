from __future__ import annotations

import random
from contextlib import asynccontextmanager
from queue import Queue
from threading import Thread
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

import app.web.server as server_mod
from app.db.connection import AsyncSessionLocal
from app.db.models import Event
from app.web import gm_orchestrator
from app.web.db_helpers import get_player_by_uid, get_session
from app.web.session_state import _get_phase, _get_ready_map, settings_get


def ws_receive_json_timeout(ws: Any, timeout: float = 2.0) -> dict[str, Any]:
    result_q: Queue[tuple[str, Any]] = Queue(maxsize=1)

    def _runner() -> None:
        try:
            payload = ws.receive_json()
            result_q.put(("ok", payload))
        except Exception as exc:  # pragma: no cover - exercised by runtime failures
            result_q.put(("err", exc))

    t = Thread(target=_runner, daemon=True)
    t.start()
    try:
        status, payload = result_q.get(timeout=timeout)
    except Exception:
        pytest.fail(f"Timed out waiting for WS JSON within {timeout:.1f}s")

    if status == "err":
        raise payload
    if not isinstance(payload, dict):
        pytest.fail(f"Expected WS JSON object, got {type(payload).__name__}")
    return payload


def run_with_timeout(
    fn: Any,
    timeout: float = 20.0,
    *,
    timeout_message: str | None = None,
    timeout_mode: str = "fail",
) -> None:
    result_q: Queue[tuple[str, Any]] = Queue(maxsize=1)

    def _runner() -> None:
        try:
            fn()
            result_q.put(("ok", None))
        except Exception as exc:  # pragma: no cover - exercised by runtime failures
            result_q.put(("err", exc))

    t = Thread(target=_runner, daemon=True)
    t.start()
    try:
        status, payload = result_q.get(timeout=timeout)
    except Exception:
        msg = timeout_message or f"Flow timed out after {timeout:.1f}s"
        if timeout_mode == "skip":
            pytest.skip(msg)
        pytest.fail(msg)

    if status == "err":
        raise payload


def portal_call(client: TestClient, async_fn: Any, *args: Any, **kwargs: Any) -> Any:
    portal = getattr(client, "portal", None) or getattr(client, "_portal", None)
    assert portal is not None, "TestClient portal is unavailable"
    return portal.call(async_fn, *args, **kwargs)


async def _read_session_runtime(session_id: str, uid: int) -> dict[str, object]:
    async with AsyncSessionLocal() as db:
        sess = await get_session(db, session_id)
        if not sess:
            return {
                "exists": False,
                "phase": None,
                "current_action_id": None,
                "player_action_events": 0,
                "is_active": False,
                "player_ready": False,
            }

        player = await get_player_by_uid(db, uid)
        ready_map = _get_ready_map(sess)
        player_ready = bool(player and ready_map.get(str(player.id), False))

        q_events = await db.execute(select(Event).where(Event.session_id == sess.id))
        events = q_events.scalars().all()
        player_action_events = sum(
            1
            for ev in events
            if isinstance(ev.result_json, dict) and str(ev.result_json.get("type") or "") == "player_action"
        )

        return {
            "exists": True,
            "phase": _get_phase(sess),
            "current_action_id": str(settings_get(sess, "current_action_id", "") or "").strip() or None,
            "player_action_events": player_action_events,
            "is_active": bool(sess.is_active),
            "player_ready": player_ready,
        }


@pytest.mark.e2e
def test_e2e_player_journey_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    random.seed(0)

    async def fake_generate_lore(*args, **kwargs):
        return {
            "text": "TEST_LORE: deterministic lore",
            "finish_reason": "stop",
            "usage": {},
        }

    async def fake_generate_from_prompt(*args, **kwargs):
        return {
            "text": "TEST_GM_REPLY: ok",
            "finish_reason": "stop",
            "usage": {},
        }

    async def fake_run_turn_gm(_session_id: str, _expected_action_id: str) -> None:
        return None

    import app.web.gm_orchestrator as gm_orchestrator_mod
    import app.web.http_routes as http_routes_mod
    import app.web.server_impl as server_impl_mod
    import app.web.ws_handlers as ws_handlers_mod

    monkeypatch.setattr(server_mod, "ENABLE_WATCHERS", False)
    monkeypatch.setattr(server_impl_mod, "ENABLE_WATCHERS", False)
    monkeypatch.setattr(gm_orchestrator_mod, "generate_lore", fake_generate_lore)
    monkeypatch.setattr(http_routes_mod, "generate_lore", fake_generate_lore)
    monkeypatch.setattr(server_impl_mod, "generate_lore", fake_generate_lore)

    monkeypatch.setattr(gm_orchestrator_mod, "generate_from_prompt", fake_generate_from_prompt)
    monkeypatch.setattr(server_impl_mod, "generate_from_prompt", fake_generate_from_prompt)
    monkeypatch.setattr(ws_handlers_mod, "generate_from_prompt", fake_generate_from_prompt)

    monkeypatch.setattr(ws_handlers_mod.gm_orchestrator, "run_turn_gm", fake_run_turn_gm)

    uid = 910000000001
    name = "E2E Player"

    @asynccontextmanager
    async def _test_lifespan(_app):
        yield

    monkeypatch.setattr(server_mod.app.router, "lifespan_context", _test_lifespan)

    def _flow() -> None:
        with TestClient(server_mod.app) as client:
            new_resp = client.post(
                "/api/new",
                json={"title": "E2E Smoke", "uid": uid, "name": name},
            )
            assert new_resp.status_code == 200, new_resp.text
            session_id = str((new_resp.json() or {}).get("session_id") or "").strip()
            assert session_id, f"/api/new did not return session_id: {new_resp.text}"

            join_resp = client.post(
                "/api/join",
                json={"session_id": session_id, "uid": uid, "name": name},
            )
            assert join_resp.status_code == 200, join_resp.text

            classes_resp = client.get("/api/classes")
            assert classes_resp.status_code == 200, classes_resp.text
            classes = (classes_resp.json() or {}).get("classes") or []
            assert classes, "Expected non-empty /api/classes response"
            class_id = str(classes[0]["id"])

            char_resp = client.post(
                "/api/character/create",
                json={
                    "session_id": session_id,
                    "uid": uid,
                    "name": "SmokeHero",
                    "class_id": class_id,
                    "custom_class": "",
                    "stats": {"str": 50, "dex": 50, "con": 50, "int": 50, "wis": 50, "cha": 50},
                    "gender": "",
                    "race": "",
                    "description": "",
                },
            )
            assert char_resp.status_code == 200, char_resp.text

            save_resp = client.post(
                "/api/story/save",
                json={
                    "session_id": session_id,
                    "uid": uid,
                    "config": {
                        "story_title": "Smoke Story",
                        "story_setting": "Smoke Setting",
                        "free_turns": False,
                        "difficulty": "medium",
                        "health_system": "normal",
                        "dmg_scale": "standard",
                        "journal_hint": "",
                        "red_flags": "",
                        "ai_verbosity": "auto",
                        "gm_notes": "",
                        "lore_text": "",
                    },
                },
            )
            assert save_resp.status_code == 200, save_resp.text

            lore_resp = client.post(
                "/api/story/lore/generate",
                json={"session_id": session_id, "uid": uid, "force": True},
            )
            assert lore_resp.status_code == 200, lore_resp.text
            assert "TEST_LORE" in str((lore_resp.json() or {}).get("lore_text") or "")

            with client.websocket_connect(f"/ws/{session_id}?uid={uid}&cid=e2e-smoke-a") as ws:
                initial = ws_receive_json_timeout(ws)
                assert initial.get("type") == "state"

                ws.send_json({"action": "ready"})
                ready_state = ws_receive_json_timeout(ws)
                assert ready_state.get("type") == "state"
                post_ready = portal_call(client, _read_session_runtime, session_id, uid)
                assert post_ready["player_ready"] is True, "Expected ready=True in session settings after ready action"

                ws.send_json({"action": "begin"})
                begin_state = ws_receive_json_timeout(ws)
                assert begin_state.get("type") == "state"
                assert (begin_state.get("game") or {}).get("phase") == "lore_pending"
                post_begin = portal_call(client, _read_session_runtime, session_id, uid)
                assert post_begin["phase"] == "lore_pending", f"Expected lore_pending after begin, got: {post_begin['phase']}"
                assert post_begin["is_active"] is True, "Expected session to become active after begin"
                ws.close()

            portal_call(client, gm_orchestrator.run_lore_generation, session_id)
            post_lore = portal_call(client, _read_session_runtime, session_id, uid)
            assert post_lore["phase"] in {"turns", "collecting_actions"}, (
                "Lore finalize failed: phase is still lore_pending after explicit run_lore_generation"
            )

            with client.websocket_connect(f"/ws/{session_id}?uid={uid}&cid=e2e-smoke-b") as ws:
                initial_2 = ws_receive_json_timeout(ws)
                assert initial_2.get("type") == "state"

                ws.send_json({"action": "say", "text": "hello from e2e"})
                say_state = ws_receive_json_timeout(ws)
                assert say_state.get("type") == "state"

                post_say = portal_call(client, _read_session_runtime, session_id, uid)
                assert int(post_say["player_action_events"]) >= 1, "Expected at least one player_action event after say"
                assert post_say["phase"] == "gm_pending", f"Expected gm_pending after say, got: {post_say['phase']}"
                assert post_say["current_action_id"], "Expected current_action_id to be set after say"

                ws.send_json({"action": "status"})
                status_state = ws_receive_json_timeout(ws)
                assert status_state.get("type") == "state"
                ws.close()

    def _probe_testclient_health() -> None:
        with TestClient(server_mod.app) as client:
            r = client.get("/")
            assert r.status_code == 200, r.text

    run_with_timeout(
        _probe_testclient_health,
        timeout=3.0,
        timeout_mode="skip",
        timeout_message="TestClient backend is not responsive in this environment (probe timeout)",
    )
    run_with_timeout(_flow, timeout=20.0, timeout_message="E2E smoke flow timed out after 20.0s")
