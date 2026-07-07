from pathlib import Path


WIZARD_JS = Path("visualizer/ingest-wizard/wizard.js")


def test_section_reference_ui_uses_ref_only_rpo_fallback() -> None:
    source = WIZARD_JS.read_text(encoding="utf-8")
    assert "const workbookRpo = candidate.rpo || candidate.refOnlyRpo;" in source
    assert "[c.rpo || c.refOnlyRpo]" in source
    assert "[candidate.rpo || candidate.refOnlyRpo]" in source
    assert "not selectable" in source
    assert "inactive" in source
    assert "const effectiveSelectable" in source
    assert "const effectiveActive" in source
    assert "data-selectable" in source
    assert "data-active" in source


def test_exclusive_group_pool_uses_ref_only_rpo_for_display_and_save() -> None:
    source = WIZARD_JS.read_text(encoding="utf-8")
    assert "const rpo = candidate.rpo || candidate.refOnlyRpo;" in source
    assert 'data-rpo="${escapeHtml(rpo)}"' in source
    assert '<td class="rpo">${escapeHtml(rpo)}</td>' in source
