from __future__ import annotations

from app.web import ws_handlers


def test_shared_save_advantage_pipeline_handles_condition_magic_and_ability_cases() -> None:
    fey_ancestry = {
        "features": {"fey_ancestry": {"type": "fey_ancestry", "advantage_on_saves_vs": ["charmed"]}},
        "saves": {"advantage_conditions": ["charmed"]},
    }
    brave = {
        "features": {"brave": {"type": "save_advantage_vs_condition", "conditions": ["frightened"]}},
        "saves": {"advantage_conditions": ["frightened"]},
    }
    gnome_cunning = {
        "features": {"gnome_cunning": {"type": "save_advantage_vs_magic", "abilities": ["int", "wis", "cha"]}},
        "saves": {"advantage_vs_magic": ["int", "wis", "cha"]},
    }
    magic_resistance = {
        "features": {"magic_resistance": {"type": "magic_resistance", "advantage_on_saves_vs": ["spells", "magical_effects"]}},
        "saves": {},
    }
    loxodon_serenity = {
        "features": {"serenity": {"type": "save_advantage_vs_condition", "conditions": ["charmed", "frightened"]}},
        "saves": {"advantage_conditions": ["charmed", "frightened"]},
    }
    leviathan_will = {
        "features": {"leviathan_will": {"type": "save_advantage_vs_condition", "conditions": ["frightened", "poisoned", "charmed", "stunned", "paralyzed", "sleep"]}},
        "saves": {"advantage_conditions": ["frightened", "poisoned", "charmed", "stunned", "paralyzed", "sleep"]},
    }
    dwarven_resilience = {
        "features": {"dwarven_resilience": {"type": "save_advantage_vs_condition", "conditions": ["poison", "poisoned"]}},
        "saves": {"advantage_conditions": ["poison"]},
    }
    plain = {"features": {}, "saves": {}}

    assert ws_handlers._effective_save_mode("normal", fey_ancestry, "wis", vs_tag="charmed") == "advantage"
    assert ws_handlers._effective_save_mode("normal", fey_ancestry, "wis", vs_tag="frightened") == "normal"
    assert ws_handlers._auto_save_advantage_reason(fey_ancestry, "wis", vs_tag="charmed") == "Fey Ancestry"

    assert ws_handlers._effective_save_mode("normal", brave, "cha", vs_tag="испуг") == "advantage"
    assert ws_handlers._effective_save_mode("normal", brave, "cha", vs_tag="charmed") == "normal"
    assert ws_handlers._auto_save_advantage_reason(brave, "wis", vs_tag="frightened") == "Brave"

    assert ws_handlers._effective_save_mode("normal", gnome_cunning, "int", vs_magic=True) == "advantage"
    assert ws_handlers._effective_save_mode("normal", gnome_cunning, "str", vs_magic=True) == "normal"
    assert ws_handlers._effective_save_mode("normal", gnome_cunning, "wis", vs_magic=False) == "normal"
    assert ws_handlers._auto_save_advantage_reason(gnome_cunning, "cha", vs_magic=True) == "Gnome Cunning"

    assert ws_handlers._effective_save_mode("normal", magic_resistance, "dex", vs_magic=True) == "advantage"
    assert ws_handlers._effective_save_mode("normal", magic_resistance, "dex", vs_magic=False) == "normal"
    assert ws_handlers._auto_save_advantage_reason(magic_resistance, "wis", vs_magic=True) == "Magic Resistance"

    assert ws_handlers._effective_save_mode("normal", loxodon_serenity, "wis", vs_tag="charmed") == "advantage"
    assert ws_handlers._effective_save_mode("normal", loxodon_serenity, "wis", vs_tag="frightened") == "advantage"
    assert ws_handlers._effective_save_mode("normal", loxodon_serenity, "wis", vs_tag="poison") == "normal"
    assert ws_handlers._auto_save_advantage_reason(loxodon_serenity, "wis", vs_tag="frightened") == "Loxodon Serenity"

    assert ws_handlers._effective_save_mode("normal", leviathan_will, "con", vs_tag="poison") == "advantage"
    assert ws_handlers._effective_save_mode("normal", leviathan_will, "wis", vs_tag="sleep") == "advantage"
    assert ws_handlers._effective_save_mode("normal", leviathan_will, "wis", vs_tag="disease") == "normal"
    assert ws_handlers._auto_save_advantage_reason(leviathan_will, "wis", vs_tag="sleep") == "Leviathan Will"

    assert ws_handlers._effective_save_mode("normal", dwarven_resilience, "con", vs_tag="poisoned") == "advantage"
    assert ws_handlers._effective_save_mode("normal", dwarven_resilience, "con", vs_tag="charmed") == "normal"
    assert ws_handlers._auto_save_advantage_reason(dwarven_resilience, "con", vs_tag="poison") == "Dwarven Resilience"

    assert ws_handlers._effective_save_mode("normal", plain, "wis", vs_tag="charmed") == "normal"
    assert ws_handlers._effective_save_mode("normal", plain, "wis", vs_magic=True) == "normal"
    assert ws_handlers._auto_save_advantage_reason(plain, "wis", vs_tag="charmed") == ""


def test_shared_save_advantage_pipeline_does_not_double_apply_or_override_explicit_modes() -> None:
    race_features = {
        "features": {"fey_ancestry": {"type": "fey_ancestry", "advantage_on_saves_vs": ["charmed"]}},
        "saves": {"advantage_conditions": ["charmed"]},
    }

    assert ws_handlers._effective_save_mode("advantage", race_features, "wis", vs_tag="charmed") == "advantage"
    assert ws_handlers._effective_save_mode("disadvantage", race_features, "wis", vs_tag="charmed") == "disadvantage"

