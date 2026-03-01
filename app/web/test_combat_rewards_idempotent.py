import asyncio
from dataclasses import dataclass

from app.web.server import (
    COMBAT_STATE_KEY,
    _compute_rewards_from_combat_state_payload,
    _grant_combat_rewards_once,
)


def test_compute_rewards_payload_xp_and_seeded_loot_stable() -> None:
    payload = {
        "started_at_iso": "2026-03-01T10:00:00+00:00",
        "order": ["pc_101", "enemy_bandit", "pc_202"],
        "combatants": {
            "pc_101": {"side": "pc", "hp_max": 20},
            "pc_202": {"side": "pc", "hp_max": 22},
            "band1": {"side": "enemy", "hp_max": 18},
        },
    }

    pc_uids, leader_uid, xp_each, loot_dict = _compute_rewards_from_combat_state_payload(payload)
    pc_uids_second, leader_uid_second, xp_each_second, loot_dict_second = _compute_rewards_from_combat_state_payload(payload)

    assert pc_uids == [101, 202]
    assert leader_uid == 101
    assert xp_each == 45
    assert loot_dict == {"dagger": 1, "longsword": 1}
    assert (pc_uids_second, leader_uid_second, xp_each_second, loot_dict_second) == (
        pc_uids,
        leader_uid,
        xp_each,
        loot_dict,
    )


@dataclass
class _FakeSession:
    settings: dict


def test_grant_rewards_blocked_when_already_granted_for_started_at() -> None:
    started_at = "2026-03-01T10:00:00+00:00"
    sess = _FakeSession(
        settings={
            COMBAT_STATE_KEY: {
                "started_at_iso": started_at,
                "order": ["pc_101", "pc_202"],
                "combatants": {
                    "pc_101": {"side": "pc", "hp_max": 20},
                    "pc_202": {"side": "pc", "hp_max": 22},
                    "band1": {"side": "enemy", "hp_max": 18},
                },
            },
            "combat_rewards_granted_for": started_at,
        }
    )
    patch = {
        "status": "Бой завершён",
        "lines": [{"text": "Победа: враг повержен"}],
    }

    granted = asyncio.run(_grant_combat_rewards_once(None, sess, patch))

    assert granted is False
    assert sess.settings["combat_rewards_granted_for"] == started_at
