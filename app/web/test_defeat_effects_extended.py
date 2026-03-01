from dataclasses import dataclass

from app.web import server


@dataclass
class _FakeCharacter:
    hp: int
    is_alive: bool


def test_left_for_dead_revives_only_leader_with_min_uid() -> None:
    chars_by_uid = {
        7: _FakeCharacter(hp=-5, is_alive=False),
        3: _FakeCharacter(hp=0, is_alive=False),
        10: _FakeCharacter(hp=4, is_alive=False),
    }

    leader_uid = server._apply_left_for_dead_character_state(chars_by_uid)

    assert leader_uid == 3
    assert chars_by_uid[3].hp == 1
    assert chars_by_uid[7].hp == 0
    assert chars_by_uid[10].hp == 4
    assert chars_by_uid[3].is_alive is True
    assert chars_by_uid[7].is_alive is True
    assert chars_by_uid[10].is_alive is True
