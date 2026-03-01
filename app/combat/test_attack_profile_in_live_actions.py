import unittest

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import Combatant, end_combat, get_combat, start_combat


class AttackProfileInLiveActionsTests(unittest.TestCase):
    def test_combat_attack_adds_weapon_line_and_damage_line(self) -> None:
        session_id = "test_attack_profile_in_live_actions"
        state = start_combat(session_id)
        state.combatants["pc_attacker"] = Combatant(
            key="pc_attacker",
            name="Attacker",
            side="pc",
            hp_current=10,
            hp_max=10,
            ac=12,
            initiative=10,
            stats={"str": 50, "dex": 90},
            inventory=[{"id": "w1", "name": "Кинжал", "qty": 1, "def": "dagger"}],
            equip={"main_hand": "w1"},
        )
        state.combatants["enemy_target"] = Combatant(
            key="enemy_target",
            name="Target",
            side="enemy",
            hp_current=10,
            hp_max=10,
            ac=10,
            initiative=0,
        )
        state.order = ["pc_attacker", "enemy_target"]
        state.turn_index = 0

        try:
            patch, err = handle_live_combat_action("combat_attack", session_id)
            self.assertIsNone(err)
            self.assertIsNotNone(patch)
            assert patch is not None

            lines = patch.get("lines")
            self.assertIsInstance(lines, list)
            texts = [line.get("text") for line in lines if isinstance(line, dict) and isinstance(line.get("text"), str)]

            self.assertTrue(any(text.startswith("Оружие: 1d4 piercing") for text in texts))
            self.assertTrue(any(text.startswith("Урон: ") for text in texts))
        finally:
            if get_combat(session_id) is not None:
                end_combat(session_id)


if __name__ == "__main__":
    unittest.main()
