from __future__ import annotations

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


def _line_texts(patch) -> list[str]:
    lines = patch.get("lines") if isinstance(patch, dict) else []
    if not isinstance(lines, list):
        return []
    out: list[str] = []
    for item in lines:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            out.append(item["text"])
    return out


def _rogue_stroke_of_luck_features() -> dict:
    return {
        "features": [
            {
                "key": "stroke_of_luck",
                "mechanics": {
                    "type": "stroke_of_luck",
                    "uses": "per_short_or_long_rest",
                    "uses_max": 1,
                    "attack_miss_to_hit": True,
                    "failed_check_d20_to_20": True,
                },
            }
        ],
        "runtime": {},
    }


def _build_state(session_id: str, *, with_feature: bool = True) -> None:
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Rogue",
        side="pc",
        hp_current=30,
        hp_max=30,
        ac=15,
        initiative=20,
        level=20,
        action_available=True,
        bonus_action_available=True,
        reaction_available=True,
        stats={"str": 50, "dex": 50, "con": 60},
        inventory=[{"id": "w1", "def": "longsword", "name": "Длинный меч", "qty": 1}],
        equip={"main_hand": "w1"},
        class_features=_rogue_stroke_of_luck_features() if with_feature else {"features": [], "runtime": {}},
    )
    state.combatants["enemy_1"] = Combatant(
        key="enemy_1",
        name="Bandit",
        side="enemy",
        hp_current=20,
        hp_max=20,
        ac=12,
        initiative=10,
        stats={"con": 50},
    )
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0
    state.round_no = 1


def test_stroke_of_luck_turns_pending_miss_into_hit_and_marks_use(monkeypatch) -> None:
    session_id = "test_stroke_of_luck_turns_pending_miss_into_hit_and_marks_use"
    _build_state(session_id)
    rolls = iter([5, 4])  # miss attack, stored damage roll
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        miss_patch, miss_err = handle_live_combat_action("combat_attack", session_id)
        assert miss_err is None
        assert miss_patch is not None
        miss_lines = _line_texts(miss_patch)
        assert any("промах" in t.lower() for t in miss_lines)
        assert any("удачный удар" in t.lower() for t in miss_lines)

        state_now = get_combat(session_id)
        assert state_now is not None
        rogue = state_now.combatants["pc_1"]
        runtime = (rogue.class_features or {}).get("runtime") or {}
        assert isinstance(runtime.get("stroke_of_luck_pending_miss"), dict)

        enemy_before = state_now.combatants["enemy_1"].hp_current
        hit_patch, hit_err = handle_live_combat_action("combat_stroke_of_luck", session_id)
        assert hit_err is None
        assert hit_patch is not None
        hit_lines = _line_texts(hit_patch)
        assert any("Удачный удар: промах превращён в попадание." in t for t in hit_lines)

        state_after = get_combat(session_id)
        assert state_after is not None
        rogue_after = state_after.combatants["pc_1"]
        enemy_after = state_after.combatants["enemy_1"]
        runtime_after = (rogue_after.class_features or {}).get("runtime") or {}
        assert enemy_after.hp_current < enemy_before
        assert runtime_after.get("stroke_of_luck_used") is True
        assert "stroke_of_luck_pending_miss" not in runtime_after
    finally:
        end_combat(session_id)


def test_stroke_of_luck_cannot_repeat_before_rest() -> None:
    session_id = "test_stroke_of_luck_cannot_repeat_before_rest"
    _build_state(session_id)
    state = get_combat(session_id)
    assert state is not None
    state.combatants["pc_1"].class_features["runtime"] = {"stroke_of_luck_used": True}

    try:
        patch, err = handle_live_combat_action("combat_stroke_of_luck", session_id)
        assert patch is None
        assert err == "Удачный удар уже использован до короткого или долгого отдыха."
    finally:
        end_combat(session_id)


def test_stroke_of_luck_requires_pending_miss() -> None:
    session_id = "test_stroke_of_luck_requires_pending_miss"
    _build_state(session_id)

    try:
        patch, err = handle_live_combat_action("combat_stroke_of_luck", session_id)
        assert patch is None
        assert err == "Нет промаха атакой, к которому можно применить «Удачный удар»."
    finally:
        end_combat(session_id)


def test_stroke_of_luck_requires_feature() -> None:
    session_id = "test_stroke_of_luck_requires_feature"
    _build_state(session_id, with_feature=False)

    try:
        patch, err = handle_live_combat_action("combat_stroke_of_luck", session_id)
        assert patch is None
        assert err == "Удачный удар недоступен вашему классу."
    finally:
        end_combat(session_id)


def test_stroke_of_luck_does_not_turn_critical_miss_into_critical_hit(monkeypatch) -> None:
    session_id = "test_stroke_of_luck_does_not_turn_critical_miss_into_critical_hit"
    _build_state(session_id)
    rolls = iter([1, 4])  # nat 1 miss, stored normal damage roll
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        miss_patch, miss_err = handle_live_combat_action("combat_attack", session_id)
        assert miss_err is None
        assert miss_patch is not None

        hit_patch, hit_err = handle_live_combat_action("combat_stroke_of_luck", session_id)
        assert hit_err is None
        assert hit_patch is not None
        hit_lines = _line_texts(hit_patch)
        assert all("крит" not in t.lower() for t in hit_lines)

        state_after = get_combat(session_id)
        assert state_after is not None
        enemy_after = state_after.combatants["enemy_1"]
        assert enemy_after.hp_current == 16
    finally:
        end_combat(session_id)


def test_stroke_of_luck_fails_if_target_missing_or_dead(monkeypatch) -> None:
    session_id = "test_stroke_of_luck_fails_if_target_missing_or_dead"
    _build_state(session_id)
    rolls = iter([5, 4])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))

    try:
        miss_patch, miss_err = handle_live_combat_action("combat_attack", session_id)
        assert miss_err is None
        assert miss_patch is not None

        state_now = get_combat(session_id)
        assert state_now is not None
        state_now.combatants["enemy_1"].hp_current = 0

        hit_patch, hit_err = handle_live_combat_action("combat_stroke_of_luck", session_id)
        assert hit_patch is None
        assert hit_err == "Цель для «Удачного удара» недоступна."
    finally:
        end_combat(session_id)
