import unittest

from app.combat.state import (
    combatant_from_dict,
    combat_state_from_dict,
    combat_state_to_dict,
    end_combat,
    get_combat,
    start_combat,
    upsert_pc,
)


class CombatantPayloadSerializationTests(unittest.TestCase):
    def test_roundtrip_preserves_stats_inventory_and_equip(self) -> None:
        session_id = "test_state_combatant_payload"
        start_combat(session_id)

        try:
            upsert_pc(
                session_id,
                pc_key="pc_1",
                name="Alice",
                hp=12,
                hp_max=12,
                ac=14,
                initiative=3,
                level=5,
                stats={"str": 11, "dex": 16, "foo": 99},
                inventory=[
                    {
                        "id": "rope_50ft",
                        "name": "Rope",
                        "qty": 1,
                        "notes": "hemp",
                        "bad": "drop",
                    }
                ],
                equip={"main_hand": "sword_1", "slot": "shield_1"},
            )

            state = get_combat(session_id)
            self.assertIsNotNone(state)
            assert state is not None
            state.combatants["pc_1"].is_dead = True
            state.combatants["pc_1"].is_stable = True
            state.combatants["pc_1"].death_successes = 9
            state.combatants["pc_1"].death_failures = -3
            state.combatants["pc_1"].action_available = False
            state.combatants["pc_1"].bonus_action_available = False
            state.combatants["pc_1"].reaction_available = False
            state.combatants["pc_1"].move_remaining = 15

            payload = combat_state_to_dict(state)
            restored = combat_state_from_dict(payload)

            self.assertIsNotNone(restored)
            assert restored is not None

            combatant = restored.combatants.get("pc_1")
            self.assertIsNotNone(combatant)
            assert combatant is not None

            raw_combatant = payload["combatants"]["pc_1"]
            self.assertEqual(raw_combatant.get("level"), 5)
            self.assertFalse(raw_combatant.get("action_available"))
            self.assertFalse(raw_combatant.get("bonus_action_available"))
            self.assertFalse(raw_combatant.get("reaction_available"))
            self.assertEqual(raw_combatant.get("move_remaining"), 15)
            self.assertEqual(combatant.equip, {"main_hand": "sword_1", "slot": "shield_1"})
            self.assertIsInstance(combatant.stats, dict)
            assert combatant.stats is not None
            self.assertEqual(combatant.stats.get("dex"), 16)
            self.assertNotIn("foo", combatant.stats)

            self.assertIsInstance(combatant.inventory, list)
            assert combatant.inventory is not None
            self.assertEqual(combatant.inventory[0].get("id"), "rope_50ft")
            self.assertNotIn("bad", combatant.inventory[0])
            self.assertTrue(combatant.is_dead)
            self.assertTrue(combatant.is_stable)
            self.assertEqual(combatant.death_successes, 3)
            self.assertEqual(combatant.death_failures, 0)
            self.assertEqual(combatant.level, 5)
            self.assertFalse(combatant.action_available)
            self.assertFalse(combatant.bonus_action_available)
            self.assertFalse(combatant.reaction_available)
            self.assertEqual(combatant.move_remaining, 15)
        finally:
            end_combat(session_id)

    def test_combatant_from_dict_missing_level_defaults_to_one(self) -> None:
        raw = {
            "key": "pc_1",
            "name": "Alice",
            "side": "pc",
            "hp_current": 12,
            "hp_max": 12,
            "ac": 14,
            "initiative": 3,
        }
        combatant = combatant_from_dict(raw)
        self.assertIsNotNone(combatant)
        assert combatant is not None
        self.assertEqual(combatant.level, 1)

        raw_with_bad_level = dict(raw)
        raw_with_bad_level["level"] = "5"
        combatant_bad_level = combatant_from_dict(raw_with_bad_level)
        self.assertIsNotNone(combatant_bad_level)
        assert combatant_bad_level is not None
        self.assertEqual(combatant_bad_level.level, 1)

    def test_combatant_from_dict_missing_turn_resources_defaults(self) -> None:
        raw = {
            "key": "pc_1",
            "name": "Alice",
            "side": "pc",
            "hp_current": 12,
            "hp_max": 12,
            "ac": 14,
            "initiative": 3,
        }
        combatant = combatant_from_dict(raw)
        self.assertIsNotNone(combatant)
        assert combatant is not None
        self.assertTrue(combatant.action_available)
        self.assertTrue(combatant.bonus_action_available)
        self.assertTrue(combatant.reaction_available)
        self.assertEqual(combatant.move_remaining, 30)


if __name__ == "__main__":
    unittest.main()
