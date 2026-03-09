from __future__ import annotations

from app.web import ws_handlers


def test_loxodon_keen_smell_grants_advantage_for_smell_tagged_supported_checks() -> None:
    race_features = {
        "features": {
            "keen_smell": {
                "checks": ["perception_smell", "survival_smell", "investigation_smell"],
            }
        }
    }
    assert (
        ws_handlers._mode_with_keen_smell_advantage(
            "normal",
            race_features,
            check_name="perception",
            check_tag="smell",
        )
        == "advantage"
    )
    assert (
        ws_handlers._mode_with_keen_smell_advantage(
            "normal",
            race_features,
            check_name="investigation",
            check_tag="smell",
        )
        == "advantage"
    )


def test_loxodon_keen_smell_does_not_force_advantage_without_smell_or_for_other_checks() -> None:
    race_features = {
        "features": {
            "keen_smell": {
                "checks": ["perception_smell", "survival_smell", "investigation_smell"],
            }
        }
    }
    assert (
        ws_handlers._mode_with_keen_smell_advantage(
            "normal",
            race_features,
            check_name="perception",
            check_tag="",
        )
        == "normal"
    )
    assert (
        ws_handlers._mode_with_keen_smell_advantage(
            "normal",
            race_features,
            check_name="stealth",
            check_tag="smell",
        )
        == "normal"
    )
    assert (
        ws_handlers._mode_with_keen_smell_advantage(
            "disadvantage",
            race_features,
            check_name="perception",
            check_tag="smell",
        )
        == "normal"
    )
