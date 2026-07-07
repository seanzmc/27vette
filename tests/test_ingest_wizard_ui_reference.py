from pathlib import Path


WIZARD_JS = Path("visualizer/ingest-wizard/wizard.js")


def test_section_reference_ui_uses_ref_only_rpo_fallback() -> None:
    source = WIZARD_JS.read_text(encoding="utf-8")
    assert "const workbookRpo = candidate.rpo || candidate.refOnlyRpo;" in source
    assert "[c.rpo || c.refOnlyRpo]" in source
    assert "[candidate.rpo || candidate.refOnlyRpo]" in source
    assert "not selectable" in source
