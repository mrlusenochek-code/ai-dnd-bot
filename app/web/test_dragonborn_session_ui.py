from pathlib import Path


def test_dragonborn_ui_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Драконье наследие: ${draconicColorRu} — ${draconicDamageRu}, дыхание ${draconicAreaText}, спасбросок ${draconicSaveRu}" in session_template
    assert "Драконья стойкость: сопротивление урону (${draconicDamageRu})" in session_template
