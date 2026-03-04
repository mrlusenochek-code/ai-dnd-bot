from pathlib import Path


def test_server_does_not_define_rewards_functions() -> None:
    server_path = Path(__file__).with_name("server.py")
    source = server_path.read_text(encoding="utf-8")

    assert "async def _grant_combat_rewards_once" not in source
    assert "async def _grant_defeat_outcome_once" not in source
    assert "async def _apply_defeat_effects_once" not in source
