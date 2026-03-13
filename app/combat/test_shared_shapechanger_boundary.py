from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from app.combat.live_actions import _revert_shapechanger_on_death, handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat
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


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    out: list[str] = []
    for item in lines:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            out.append(item["text"])
    return out


def test_shared_shapechanger_boundary_apply_and_explicit_revert_preserve_runtime() -> None:
    session_id = "test_shared_shapechanger_boundary_apply_and_explicit_revert_preserve_runtime"
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

        state_now = get_combat(session_id)
        assert state_now is not None
        actor = state_now.combatants["pc_1"]
        runtime = (actor.race_features or {}).get("runtime") or {}
        shape = runtime.get("shapechanger") or {}
        history = runtime.get("shapechanger_history") or []
        conditions = runtime.get("conditions") or {}

        assert runtime.get("sentinel_top") == "keep-top"
        assert (conditions.get("custom_marker") or {}).get("tag") == "keep-condition"
        assert shape.get("active") is True
        assert shape.get("persona") == "городской страж"
        assert shape.get("voice") == "хриплый"
        assert isinstance(shape.get("changed_at_iso"), str) and shape.get("changed_at_iso")
        assert isinstance(history, list) and history
        assert (history[-1] or {}).get("persona") == "городской страж"

        actor.action_available = True
        patch_revert, err_revert, changed_revert = ws_handlers._apply_shapechanger_in_combat(
            session_id,
            "pc_1",
            ch,
            active=False,
        )
        assert err_revert is None
        assert changed_revert is True
        assert patch_revert is not None

        state_after = get_combat(session_id)
        assert state_after is not None
        actor_after = state_after.combatants["pc_1"]
        runtime_after = (actor_after.race_features or {}).get("runtime") or {}
        shape_after = runtime_after.get("shapechanger") or {}
        conditions_after = runtime_after.get("conditions") or {}
        history_after = runtime_after.get("shapechanger_history") or []

        assert runtime_after.get("sentinel_top") == "keep-top"
        assert (conditions_after.get("custom_marker") or {}).get("tag") == "keep-condition"
        assert shape_after.get("active") is False
        assert shape_after.get("persona") == ""
        assert shape_after.get("voice") == ""
        assert isinstance(shape_after.get("changed_at_iso"), str) and shape_after.get("changed_at_iso")
        assert history_after == history
    finally:
        end_combat(session_id)


def test_shared_shapechanger_boundary_death_revert_preserves_runtime_and_no_drift(monkeypatch) -> None:
    session_id = "test_shared_shapechanger_boundary_death_revert_preserves_runtime_and_no_drift"
    state = start_combat(session_id)
    actor_features = _shapechanger_features()
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Changeling",
        side="pc",
        hp_current=1,
        hp_max=1,
        ac=10,
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
        action_available=True,
        stats={"str": 60},
        inventory=[{"id": "w1", "def": "longsword"}],
        equip={"main_hand": "w1"},
    )
    state.combatants["pc_2"] = Combatant(
        key="pc_2",
        name="Ally",
        side="pc",
        hp_current=10,
        hp_max=10,
        ac=12,
        initiative=5,
    )
    state.order = ["pc_1", "enemy_1", "pc_2"]
    state.turn_index = 0

    ch = SimpleNamespace(name="Changeling", race_features=deepcopy(actor_features))

    rolls = iter([15, 8])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

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

        state.turn_index = 1
        patch_attack, err_attack = handle_live_combat_action("combat_attack", session_id)
        assert err_attack is None
        assert patch_attack is not None
        assert any("Перевёртыш: смерть — возвращение в истинную форму." in t for t in _line_texts(patch_attack))

        state_after = get_combat(session_id)
        assert state_after is not None
        actor_after = state_after.combatants["pc_1"]
        runtime_after = (actor_after.race_features or {}).get("runtime") or {}
        shape_after = runtime_after.get("shapechanger") or {}
        conditions_after = runtime_after.get("conditions") or {}

        assert runtime_after.get("sentinel_top") == "keep-top"
        assert (conditions_after.get("custom_marker") or {}).get("tag") == "keep-condition"
        assert shape_after.get("active") is False
        assert shape_after.get("persona") == ""
        assert shape_after.get("voice") == ""
        assert isinstance(shape_after.get("changed_at_iso"), str) and shape_after.get("changed_at_iso")

        runtime_snapshot = deepcopy(runtime_after)
        lines: list[dict[str, str]] = []
        _revert_shapechanger_on_death(actor_after, lines)
        runtime_final = ((actor_after.race_features or {}).get("runtime") or {})
        assert runtime_final == runtime_snapshot
        assert lines == []
    finally:
        end_combat(session_id)
