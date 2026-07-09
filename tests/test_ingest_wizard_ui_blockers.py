from pathlib import Path


WIZARD_JS = Path("visualizer/ingest-wizard/wizard.js")
WIZARD_CSS = Path("visualizer/ingest-wizard/wizard.css")
WIZARD_HTML = Path("visualizer/ingest-wizard/index.html")


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


def test_plan_approval_copy_is_diagnostic_only_for_legacy_and_current_states() -> None:
    source = WIZARD_JS.read_text(encoding="utf-8")
    assert '"plan_approved": "Legacy plan approval — diagnostic dry-run evidence only."' in source
    assert '"dry_run_approved": "Approved for dry-run evidence — no workbook write authority."' in source
    assert (
        '"dry_run_validated_write_blocked": "Diagnostic dry run complete — workbook write remains blocked."'
        in source
    )
    assert "Approve for dry-run evidence" in source
    assert "Approved — ready for the Pass D apply step." not in source
    assert "approve to sign off for apply" not in source


def test_browser_does_not_offer_live_write_authority() -> None:
    source = WIZARD_JS.read_text(encoding="utf-8")
    assert "/write/approve" not in source
    assert "live-write" not in source


def test_static_plan_stage_copy_is_diagnostic_only() -> None:
    source = WIZARD_HTML.read_text(encoding="utf-8")
    assert "Diagnostic plan" in source
    assert "dry-run evidence only" in source
    assert "Approve for dry-run evidence" in source
    assert "Apply plan" not in source
    assert "sign-off for the write step" not in source
    assert "Approve plan for apply" not in source
