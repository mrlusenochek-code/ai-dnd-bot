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
            out.append(str(item.get("text")))
    return out


def test_leonin_claws_use_shared_combat_attack_profile(monkeypatch) -> None:
    session_id = "test_leonin_claws_use_shared_combat_attack_profile"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Leonin",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=3,
        stats={"str": 60, "dex": 50},
        race_features={
            "race_key": "leonin",
            "features": {
                "claws_leonin": {
                    "type": "natural_weapon",
                    "name": "claws_leonin",
                    "name_ru": "Когти",
                    "damage_dice": "1d4",
                    "damage_type": "slashing",
                    "ability": "str",
                    "kind": "unarmed",
                }
            },
            "natural_weapons": [
                {"key": "claws_leonin", "kind": "unarmed", "damage_dice": "1d4", "damage_type": "slashing", "ability": "str"}
            ],
        },
    )
    state.combatants["enemy_1"] = Combatant(key="enemy_1", name="Bandit", side="enemy", hp_current=15, hp_max=15, ac=10, initiative=5)
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    rolls = iter([18, 4])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))
    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None and patch is not None
        texts = _line_texts(patch)
        assert any(text == "Оружие: 1d4 slashing" for text in texts)
        assert any(text == "Результат: попадание" for text in texts)
        assert any(text == "Урон: 4 + 1 = 5" for text in texts)
        enemy = get_combat(session_id).combatants["enemy_1"]  # type: ignore[union-attr]
        assert int(enemy.hp_current or 0) == 10
    finally:
        end_combat(session_id)


def test_non_leonin_unarmed_attack_regression_stays_bludgeoning(monkeypatch) -> None:
    session_id = "test_non_leonin_unarmed_attack_regression_stays_bludgeoning"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Commoner",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=10,
        initiative=20,
        level=3,
        stats={"str": 60, "dex": 50},
        race_features={"race_key": "human", "features": {}},
    )
    state.combatants["enemy_1"] = Combatant(key="enemy_1", name="Bandit", side="enemy", hp_current=15, hp_max=15, ac=10, initiative=5)
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    rolls = iter([18, 4])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))
    try:
        patch, err = handle_live_combat_action("combat_attack", session_id)
        assert err is None and patch is not None
        texts = _line_texts(patch)
        assert any(text == "Оружие: 1d4 bludgeoning" for text in texts)
        assert any(text == "Урон: 4 + 1 = 5" for text in texts)
        enemy = get_combat(session_id).combatants["enemy_1"]  # type: ignore[union-attr]
        assert int(enemy.hp_current or 0) == 10
    finally:
        end_combat(session_id)
