from pathlib import Path


TARGET_FUNCTIONS = (
    "_combat_outcome_summary_from_patch",
    "_merge_combat_patches",
    "_append_combat_patch_lines",
    "_build_combat_start_preamble_lines",
    "_maybe_apply_opening_combat_action",
    "_combat_participants_block",
    "_generate_combat_narration",
)


def _read_source(name: str) -> str:
    return Path(__file__).with_name(name).read_text(encoding="utf-8")


def test_combat_bridge_contains_extracted_functions():
    src = _read_source("combat_bridge.py")
    for fn_name in TARGET_FUNCTIONS:
        assert f"def {fn_name}(" in src or f"async def {fn_name}(" in src


def test_server_no_longer_contains_extracted_combat_bridge_bodies():
    src = _read_source("server.py")
    for fn_name in TARGET_FUNCTIONS:
        assert f"\ndef {fn_name}(" not in src
        assert f"\nasync def {fn_name}(" not in src
