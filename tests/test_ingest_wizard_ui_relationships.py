from pathlib import Path


WIZARD_JS = Path("visualizer/ingest-wizard/wizard.js")


def _source() -> str:
    return WIZARD_JS.read_text(encoding="utf-8")


def test_retired_broad_relationship_authoring_is_absent() -> None:
    source = _source()
    for retired in (
        "RELATIONSHIP_KIND_CHOICES",
        "RELATIONSHIP_KIND_ALIASES",
        "group-product-decision",
        "selectedRelationshipKind",
        "setRelationshipKind",
        "Save relationship",
    ):
        assert retired not in source


def test_typed_exception_relationship_resolution_remains() -> None:
    source = _source()
    assert "renderDecisionOutcomes" in source
    assert "decisionEffectView" in source
    assert "Preview effect" in source
    assert "The live workbook is not being written." in source
