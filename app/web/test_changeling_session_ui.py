from pathlib import Path


def test_changeling_shapechanger_texts_present_in_session_template() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert 'const shapechangerTraitText = shapechangerFeature' in template
    assert 'Перевёртыш: можете менять внешний вид и голос' in template
    assert 'одежда и снаряжение не меняются автоматически' in template
    assert 'Облик: естественная форма' in template
