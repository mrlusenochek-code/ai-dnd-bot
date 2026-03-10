from __future__ import annotations

from types import SimpleNamespace

from app.web import ws_handlers


def _character(*tools: str) -> SimpleNamespace:
    return SimpleNamespace(
        race_features={
            "proficiencies": {
                "tools": list(tools),
            }
        }
    )


def test_parse_toolcheck_command_variants() -> None:
    assert ws_handlers._parse_toolcheck_command("toolcheck thieves_tools") == ("normal", "thieves_tools", None, None)
    assert ws_handlers._parse_toolcheck_command("toolcheck adv thieves_tools") == ("advantage", "thieves_tools", None, None)
    assert ws_handlers._parse_toolcheck_command("toolcheck dis thieves_tools dc 15") == ("disadvantage", "thieves_tools", 15, None)
    assert ws_handlers._parse_toolcheck_command("toolcheck herbalism_kit dc12") == ("normal", "herbalism_kit", 12, None)


def test_parse_toolcheck_command_reports_clear_errors() -> None:
    _mode, _tool, _dc, err_usage = ws_handlers._parse_toolcheck_command("toolcheck")
    assert err_usage is not None and "Использование" in err_usage

    _mode, _tool, _dc, err_dc = ws_handlers._parse_toolcheck_command("toolcheck thieves_tools dc")
    assert err_dc is not None and "dc" in err_dc.lower()

    _mode, _tool, _dc, err_bad_dc = ws_handlers._parse_toolcheck_command("toolcheck thieves_tools dc -1")
    assert err_bad_dc == "DC должен быть не меньше 0"


def test_toolcheck_access_requires_known_tool_and_proficiency() -> None:
    ch = _character("thieves_tools")

    unknown = ws_handlers._toolcheck_access_error(ch, "unknown_tools")
    assert unknown == "Неизвестный инструмент: unknown_tools"

    missing = ws_handlers._toolcheck_access_error(ch, "alchemists_supplies")
    assert missing == "У персонажа нет владения инструментом: Принадлежности алхимика"

    assert ws_handlers._toolcheck_access_error(ch, "thieves_tools") is None


def test_toolcheck_uses_human_readable_tool_name() -> None:
    assert ws_handlers._tool_label_ru("thieves_tools") == "Воровские инструменты"
