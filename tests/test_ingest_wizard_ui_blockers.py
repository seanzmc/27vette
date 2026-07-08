from pathlib import Path


WIZARD_JS = Path("visualizer/ingest-wizard/wizard.js")
WIZARD_CSS = Path("visualizer/ingest-wizard/wizard.css")


def test_blocker_panel_is_collapsible_and_stateful() -> None:
    source = WIZARD_JS.read_text(encoding="utf-8")
    assert 'blockerCollapsed: false' in source
    assert '<details class="blocker-panel"' in source
    assert 'const openAttr = reviewState.blockerCollapsed ? "" : " open";' in source
    assert 'reviewState.blockerCollapsed = !panel.open;' in source


def test_blocker_panel_has_collapsible_styling() -> None:
    source = WIZARD_CSS.read_text(encoding="utf-8")
    assert ".blocker-summary" in source
    assert ".blocker-toggle-hint" in source
    assert ".blocker-body" in source
