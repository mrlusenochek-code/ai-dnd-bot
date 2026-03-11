from pathlib import Path


def test_firbolg_hidden_step_ui_status_texts_present_in_session_template() -> None:
    session_template = (Path(__file__).resolve().parents[0] / "templates" / "session.html").read_text(encoding="utf-8")
    assert 'const hiddenStepStatus = hiddenStepActive' in session_template
    assert 'восстановится после короткого/долгого отдыха' in session_template
    assert 'активен до начала вашего следующего хода или до атаки/урона/принуждения к спасброску' in session_template
    assert 'Незримая поступь: ${hiddenStepStatus}.' in session_template
