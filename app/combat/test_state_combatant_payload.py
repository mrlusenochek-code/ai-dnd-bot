import unittest

from app.combat.state import (
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

            payload = combat_state_to_dict(state)
            restored = combat_state_from_dict(payload)

            self.assertIsNotNone(restored)
            assert restored is not None

            combatant = restored.combatants.get("pc_1")
            self.assertIsNotNone(combatant)
            assert combatant is not None

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
        finally:
            end_combat(session_id)


if __name__ == "__main__":
    unittest.main()
