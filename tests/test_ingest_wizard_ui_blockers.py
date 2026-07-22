from pathlib import Path


WIZARD_JS = Path("visualizer/ingest-wizard/wizard.js")
WIZARD_CSS = Path("visualizer/ingest-wizard/wizard.css")
WIZARD_HTML = Path("visualizer/ingest-wizard/index.html")


def test_legacy_review_blocker_panel_is_absent() -> None:
    source = WIZARD_JS.read_text(encoding="utf-8")
    assert "blockerCollapsed" not in source
    assert 'class="blocker-panel"' not in source


def test_legacy_review_blocker_styling_is_absent() -> None:
    source = WIZARD_CSS.read_text(encoding="utf-8")
    assert ".blocker-summary" not in source
    assert ".blocker-toggle-hint" not in source
    assert ".blocker-body" not in source


def test_browser_has_no_plan_or_write_approval_copy() -> None:
    source = WIZARD_JS.read_text(encoding="utf-8")
    assert "plan_approved" not in source
    assert "dry_run_approved" not in source
    assert "Approve for dry-run evidence" not in source


def test_browser_does_not_offer_live_write_authority() -> None:
    source = WIZARD_JS.read_text(encoding="utf-8")
    assert "/write/approve" not in source
    assert "live-write" not in source


def test_static_plan_stage_is_absent() -> None:
    source = WIZARD_HTML.read_text(encoding="utf-8")
    assert 'id="stage-plan"' not in source
    assert 'id="stage-review"' not in source
    assert "Create ChangeSet" in source
