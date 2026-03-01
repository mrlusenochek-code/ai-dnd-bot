import unittest

from app.combat.live_actions import handle_live_combat_action
from app.combat.state import add_enemy, current_turn_label, end_combat, get_combat, start_combat, upsert_pc


class SkipDeadTurnsTests(unittest.TestCase):
    def test_skips_dead_current_combatant_and_moves_turn_to_living(self) -> None:
        session_id = "test_skip_dead_turns"
        start_combat(session_id)
        upsert_pc(
            session_id,
            pc_key="pc_dead",
            name="Павший",
            hp=0,
            hp_max=10,
            ac=12,
            initiative=20,
        )
        upsert_pc(
            session_id,
            pc_key="pc_alive",
            name="Живой",
            hp=10,
            hp_max=10,
            ac=13,
            initiative=10,
        )
        add_enemy(session_id, name="Гоблин", hp=8, ac=11)

        try:
            patch, err = handle_live_combat_action("combat_end_turn", session_id)
            self.assertIsNone(err)
            self.assertIsNotNone(patch)
            assert patch is not None

            lines = patch.get("lines")
            self.assertIsInstance(lines, list)
            line_texts = [line.get("text") for line in lines if isinstance(line, dict)]
            self.assertIn("Ход пропущен: Павший (0 HP).", line_texts)

            state = get_combat(session_id)
            self.assertIsNotNone(state)
            assert state is not None
            self.assertEqual(current_turn_label(state), "Живой")
        finally:
            end_combat(session_id)


if __name__ == "__main__":
    unittest.main()
