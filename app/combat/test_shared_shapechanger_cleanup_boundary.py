from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from app.combat.live_actions import _revert_shapechanger_on_death
from app.combat.state import Combatant, _cleanup_battle_runtime, end_combat, start_combat
from app.web import ws_handlers


def _shapechanger_runtime() -> dict:
    return {
        "sentinel_top": "keep-top",
        "conditions": {"custom_marker": {"active": True, "tag": "keep-condition"}},
    }


def _shapechanger_features() -> dict:
    return {
        "features": {
            "shapechanger": {
                "action": True,
                "revert_on_death": True,
                "equipment_unchanged": True,
            }
        },
        "runtime": _shapechanger_runtime(),
    }


def test_shared_shapechanger_cleanup_boundary_battle_cleanup_keeps_active_shape_and_no_drift() -> None:
    session_id = "test_shared_shapechanger_cleanup_boundary_battle_cleanup_keeps_active_shape_and_no_drift"
    state = start_combat(session_id)
    actor_features = _shapechanger_features()
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Changeling",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        action_available=True,
        race_features=deepcopy(actor_features),
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    ch = SimpleNamespace(name="Changeling", race_features=deepcopy(actor_features))

    try:
        patch_apply, err_apply, changed_apply = ws_handlers._apply_shapechanger_in_combat(
            session_id,
            "pc_1",
            ch,
            active=True,
            persona="городской страж",
            voice="хриплый",
        )
        assert err_apply is None
        assert changed_apply is True
        assert patch_apply is not None

        runtime_before = deepcopy(((state.combatants["pc_1"].race_features or {}).get("runtime") or {}))
        shape_before = runtime_before.get("shapechanger") or {}

        assert runtime_before.get("sentinel_top") == "keep-top"
        assert (runtime_before.get("conditions") or {}).get("custom_marker", {}).get("tag") == "keep-condition"
        assert shape_before.get("active") is True
        assert shape_before.get("persona") == "городской страж"
        assert shape_before.get("voice") == "хриплый"
        assert isinstance(shape_before.get("changed_at_iso"), str) and shape_before.get("changed_at_iso")
        assert isinstance(runtime_before.get("shapechanger_history"), list)

        changed_first = _cleanup_battle_runtime(state)
        runtime_after_first = ((state.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert changed_first is False
        assert runtime_after_first == runtime_before

        changed_second = _cleanup_battle_runtime(state)
        runtime_after_second = ((state.combatants["pc_1"].race_features or {}).get("runtime") or {})
        assert changed_second is False
        assert runtime_after_second == runtime_before
    finally:
        end_combat(session_id)


def test_shared_shapechanger_cleanup_boundary_death_revert_differs_from_battle_cleanup() -> None:
    actor = Combatant(
        key="pc_1",
        name="Changeling",
        side="pc",
        hp_current=0,
        hp_max=20,
        ac=13,
        initiative=20,
        race_features=_shapechanger_features(),
    )
    runtime = ((actor.race_features or {}).get("runtime") or {})
    runtime["shapechanger"] = {
        "active": True,
        "persona": "городской страж",
        "voice": "хриплый",
        "changed_at_iso": "2026-03-13T00:00:00+00:00",
    }
    runtime["shapechanger_history"] = [{"persona": "городской страж"}]
    actor.race_features["runtime"] = runtime

    lines: list[dict[str, str]] = []
    reverted = _revert_shapechanger_on_death(actor, lines)
    runtime_after = ((actor.race_features or {}).get("runtime") or {})
    shape_after = runtime_after.get("shapechanger") or {}

    assert reverted is True
    assert any("Перевёртыш: смерть — возвращение в истинную форму." in str(item.get("text") or "") for item in lines)
    assert runtime_after.get("sentinel_top") == "keep-top"
    assert (runtime_after.get("conditions") or {}).get("custom_marker", {}).get("tag") == "keep-condition"
    assert shape_after.get("active") is False
    assert shape_after.get("persona") == ""
    assert shape_after.get("voice") == ""
    assert isinstance(shape_after.get("changed_at_iso"), str) and shape_after.get("changed_at_iso")
    assert runtime_after.get("shapechanger_history") == [{"persona": "городской страж"}]
