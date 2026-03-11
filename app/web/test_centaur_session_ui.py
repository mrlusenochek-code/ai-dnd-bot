from __future__ import annotations

from pathlib import Path


def test_centaur_session_ui_text_present() -> None:
    template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")

    assert "const chargeText = charge" in template
    assert "после ${chargeMoveFt} фт движения и попадания рукопашным оружием" in template
    assert 'bonus_attack) || "").trim().toLowerCase()' in template
    assert "Лошадиное телосложение: мощное телосложение; лазание стоит x${1 +" in template
