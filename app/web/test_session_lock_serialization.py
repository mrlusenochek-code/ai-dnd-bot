import asyncio

import app.web.state_builder as sb


def test_get_session_lock_identity():
    from app.web.session_lock import get_session_lock

    a1 = get_session_lock("sess_a")
    a2 = get_session_lock("sess_a")
    b1 = get_session_lock("sess_b")

    assert a1 is a2
    assert a1 is not b1


def test_broadcast_state_serialized_per_session(monkeypatch):
    async def scenario():
        first_started = asyncio.Event()
        allow_first_finish = asyncio.Event()
        second_entered = asyncio.Event()

        async def fake_unlocked(session_id: str, combat_log_ui_patch=None):
            # Первый вызов держим, второй должен ждать lock
            if not first_started.is_set():
                first_started.set()
                await allow_first_finish.wait()
                return
            second_entered.set()

        monkeypatch.setattr(sb, "_broadcast_state_unlocked", fake_unlocked, raising=True)

        t1 = asyncio.create_task(sb.broadcast_state("sess_one"))
        await first_started.wait()

        t2 = asyncio.create_task(sb.broadcast_state("sess_one"))
        await asyncio.sleep(0.01)

        # Пока первый не отпустили — второй не должен войти
        assert not second_entered.is_set()

        allow_first_finish.set()
        await asyncio.gather(t1, t2)

        assert second_entered.is_set()

    asyncio.run(scenario())


def test_broadcast_state_not_global_lock(monkeypatch):
    async def scenario():
        first_started = asyncio.Event()
        allow_first_finish = asyncio.Event()
        other_entered = asyncio.Event()

        async def fake_unlocked(session_id: str, combat_log_ui_patch=None):
            if session_id == "sess_one":
                first_started.set()
                await allow_first_finish.wait()
                return
            if session_id == "sess_two":
                other_entered.set()
                return

        monkeypatch.setattr(sb, "_broadcast_state_unlocked", fake_unlocked, raising=True)

        t1 = asyncio.create_task(sb.broadcast_state("sess_one"))
        await first_started.wait()

        # Другая сессия должна проходить параллельно (другой lock)
        t2 = asyncio.create_task(sb.broadcast_state("sess_two"))
        await asyncio.sleep(0.01)
        assert other_entered.is_set()

        allow_first_finish.set()
        await asyncio.gather(t1, t2)

    asyncio.run(scenario())