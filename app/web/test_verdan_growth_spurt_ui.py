from pathlib import Path


def test_verdan_growth_spurt_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "Скачок роста: сейчас размер ${currentSizeRu || \"—\"}" in template
    assert "На ${growthAtLevel !== null ? growthAtLevel : 5} уровне станет ${growthToSizeRu}." in template
    assert "Ограниченная телепатия:" in template
    assert "Чёрная исцеляющая кровь" in template
