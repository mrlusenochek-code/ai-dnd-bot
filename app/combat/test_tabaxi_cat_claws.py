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


def test_tabaxi_cat_claws_attack_has_named_log_and_damage(monkeypatch) -> None:
    session_id = "test_tabaxi_cat_claws_attack"
    state = start_combat(session_id)
    state.combatants["pc_1"] = Combatant(
        key="pc_1",
        name="Tabaxi",
        side="pc",
        hp_current=20,
        hp_max=20,
        ac=13,
        initiative=20,
        level=3,
        stats={"str": 60, "dex": 60},
        race_features={
            "race_key": "tabaxi",
            "features": {
                "cat_claws": {
                    "type": "natural_weapon",
                    "name": "cat_claws",
                    "damage_dice": "1d4",
                    "damage_type": "slashing",
                    "ability": "str",
                    "is_unarmed_replacement": True,
                }
            },
            "natural_weapons": [{"key": "cat_claws", "kind": "unarmed", "damage_dice": "1d4", "damage_type": "slashing", "ability": "str"}],
        },
    )
    state.combatants["enemy_1"] = Combatant(key="enemy_1", name="Bandit", side="enemy", hp_current=15, hp_max=15, ac=10, initiative=5)
    state.order = ["pc_1", "enemy_1"]
    state.turn_index = 0

    rolls = iter([18, 4])
    monkeypatch.setattr("app.combat.live_actions.random.randint", lambda _a, _b: next(rolls))
    try:
        patch, err = handle_live_combat_action("combat_cat_claws", session_id)
        assert err is None and patch is not None
        texts = _line_texts(patch)
        assert any("Когти кошки" in t for t in texts)
        assert any("slashing" in t for t in texts)
        assert any("= 5 slashing" in t for t in texts)
        enemy = get_combat(session_id).combatants["enemy_1"]  # type: ignore[union-attr]
        assert int(enemy.hp_current or 0) == 10
    finally:
        end_combat(session_id)
