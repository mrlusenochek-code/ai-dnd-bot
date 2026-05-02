from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.web import server_impl, ws_handlers


def _rogue_class_features(*, explicit_choices=None) -> dict:
    payload = {
        "features": [
            {
                "key": "expertise",
                "mechanics": {
                    "type": "expertise",
                    "count": 2,
                    "allowed_kinds": ["skill", "tool"],
                    "default_choices": ["stealth", "tool:thieves_tools"],
                },
            }
        ],
        "runtime": {},
    }
    if explicit_choices is not None:
        payload["choices"] = {"expertise": explicit_choices}
    return payload


def test_compute_check_mod_applies_rogue_expertise_to_stealth() -> None:
    character = SimpleNamespace(
        id=uuid.uuid4(),
        level=1,
        stats={"dex": 70, "wis": 70},
        class_features=_rogue_class_features(),
    )
    skill_mods_by_char = {
        character.id: {
            "stealth": 2,
            "perception": 2,
            "athletics": 0,
        }
    }

    stealth_mod = server_impl._compute_check_mod({"kind": "skill", "name": "stealth"}, character, skill_mods_by_char)
    perception_mod = server_impl._compute_check_mod({"kind": "skill", "name": "perception"}, character, skill_mods_by_char)
    athletics_mod = server_impl._compute_check_mod({"kind": "skill", "name": "athletics"}, character, skill_mods_by_char)

    assert stealth_mod == 6
    assert perception_mod == 4
    assert athletics_mod == 0


def test_compute_check_mod_applies_expertise_inside_composite_skill_checks() -> None:
    character = SimpleNamespace(
        id=uuid.uuid4(),
        level=1,
        stats={"dex": 70, "wis": 50},
        class_features=_rogue_class_features(),
    )
    skill_mods_by_char = {
        character.id: {
            "stealth": 2,
            "perception": 2,
        }
    }

    mod = server_impl._compute_check_mod({"kind": "skill", "name": "perception|stealth"}, character, skill_mods_by_char)
    assert mod == 6


def test_effective_toolcheck_mod_uses_double_proficiency_for_expertise() -> None:
    rogue = SimpleNamespace(level=1, class_features=_rogue_class_features())
    non_expert = SimpleNamespace(level=1, class_features={"features": [], "runtime": {}})

    assert ws_handlers._effective_toolcheck_mod(rogue, "thieves_tools") == 4
    assert ws_handlers._effective_toolcheck_mod(rogue, "herbalism_kit") == 2
    assert ws_handlers._effective_toolcheck_mod(non_expert, "thieves_tools") == 2
