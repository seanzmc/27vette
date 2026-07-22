from pathlib import Path


WIZARD_JS = Path("visualizer/ingest-wizard/wizard.js")


def test_retired_broad_review_reference_authoring_is_absent() -> None:
    source = WIZARD_JS.read_text(encoding="utf-8")
    for retired in (
        "const workbookRpo = candidate.rpo || candidate.refOnlyRpo;",
        "const effectiveSelectable",
        "const effectiveActive",
        "data-selectable",
        "data-active",
    ):
        assert retired not in source


def test_current_path_ends_at_changeset_emission() -> None:
    source = WIZARD_JS.read_text(encoding="utf-8")
    assert 'const STAGES = ["files", "sheets", "candidates", "models", "compile", "exceptions", "changeset"];' in source
    assert '$("#compile-changeset-btn").addEventListener' in source
    assert "/changeset" in source
