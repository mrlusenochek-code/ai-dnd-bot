from pathlib import Path


def test_loxodon_session_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert "Хобот: досягаемость 5 фт, переноска/толкать/тянуть, безоружный удар; нельзя держать оружие/щит, точные действия и соматику" in template
    assert "Спокойствие локсодонов: преимущество на спасброски от очарования/испуга" in template
