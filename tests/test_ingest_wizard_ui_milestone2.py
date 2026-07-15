from pathlib import Path


WIZARD_HTML = Path("visualizer/ingest-wizard/index.html")
WIZARD_JS = Path("visualizer/ingest-wizard/wizard.js")
WIZARD_CSS = Path("visualizer/ingest-wizard/wizard.css")


def test_forward_stepper_uses_compile_and_exception_stages() -> None:
    html = WIZARD_HTML.read_text(encoding="utf-8")
    js = WIZARD_JS.read_text(encoding="utf-8")

    assert 'data-stage="compile"' in html
    assert 'data-stage="exceptions"' in html
    assert 'id="stage-compile"' in html
    assert 'id="stage-exceptions"' in html
    assert 'const STAGES = ["files", "sheets", "candidates", "models", "compile", "exceptions"];' in js
    assert 'const LEGACY_STAGES = ["review", "plan"];' in js
    assert 'renderReconciliation();' not in js[js.index('$("#confirm-models-btn")'):js.index('function renderReconciliation')]
    assert 'await enterCompile();' in js[js.index('$("#confirm-models-btn")'):js.index('function renderReconciliation')]


def test_compile_summary_uses_compact_api_and_separate_readiness_gates() -> None:
    js = WIZARD_JS.read_text(encoding="utf-8")

    assert "async function enterCompile()" in js
    assert "async function runCompile()" in js
    assert "function renderCompilerSummary(summary)" in js
    assert "`/api/wizard/sessions/${state.session.runId}/compile`" in js
    assert '"compileReady"' in js
    assert '"planReady"' in js
    assert '"writeReady"' in js
    assert '"deploymentReady"' in js
    assert '$("#compile-btn").addEventListener("click", runCompile);' in js
    assert '$("#review-exceptions-btn").addEventListener("click", enterExceptions);' in js


def test_exception_cards_use_typed_controls_evidence_and_lifecycle_api() -> None:
    html = WIZARD_HTML.read_text(encoding="utf-8")
    js = WIZARD_JS.read_text(encoding="utf-8")
    css = WIZARD_CSS.read_text(encoding="utf-8")

    assert "async function enterExceptions()" in js
    assert "async function loadExceptions(" in js
    assert "function renderExceptionCard(item)" in js
    assert "function exceptionActionForm(item)" in js
    for action in (
        "choose_section",
        "choose_relationship",
        "retain_existing",
        "provide_typed_value",
        "approve_removal",
        "mark_not_applicable",
        "record_allowed_deferral",
    ):
        assert f'case "{action}"' in js
    assert "/exceptions/resolve`" in js
    assert "/exceptions/reopen`" in js
    assert "Raw source evidence" in js
    assert "Existing workbook rows" in js
    assert "Already-derived rows" in js
    assert "Shared context — not written by this decision" in js
    assert "Exact decision effect" in js
    assert "Comparator context" in js
    assert "Proposal to evaluate — not workbook rows" in js
    assert "Target workbook state" not in js
    assert "Proposed canonical rows" not in js
    assert "Gate impact" in js
    assert '$("#exception-reviewer").value.trim()' in js
    assert "Object.entries(rawCells)" in js
    assert 'evidenceValues(row, ["values", "signature"])' in js
    assert 'evidenceValues(fact, ["values", "payload", "signature"])' in js
    assert 'id="exception-decision"' in html
    assert 'id="exception-sheet"' in html
    assert 'id="exception-family"' not in html
    assert 'id="exception-reason"' not in html
    assert 'id="exception-severity"' not in html
    assert 'decisionType: $("#exception-decision").value' in js
    assert 'sheet: $("#exception-sheet").value' in js
    assert 'reviewState: $("#exception-review-state").value' in js
    assert 'id="exception-review-state"' in html
    assert 'q: $("#exception-q").value.trim()' in js
    assert "/exceptions/preview`" in js
    assert "Preview exact workbook effect" in js
    assert "Confirm and save this exact effect" in js
    assert "Reject entire proposal — write no rows" in js
    assert 'name="rejectWholeProposal" required' in js
    assert "Why this target fact is not applicable" not in js
    assert 'name="priceScope"' in js
    assert "choices.priceScopes" in js
    assert "variantScope: scope.variantScope" in js
    assert "result.variantScope = selectedScope.variantScope" in js
    assert ".exception-card .card-head > div" in css
    assert "overflow-wrap: anywhere" in css
    assert 'name="bodyStyleScope"' not in js
    assert 'name="trimLevelScope"' not in js
    assert 'name="selectionMode"' in js
    assert "choices.exclusiveSelectionModes" in js
    assert 'name="priority" type="number" min="0" step="1" required' in js
    assert 'name="defaultDisplayBehavior"' in js
    assert 'displayBehavior: displayBehavior === "__blank__" ? "" : displayBehavior' in js
    assert 'reasonCode === "comparator_only_price_rule_proposal"' in js


def test_exception_layout_has_mobile_single_column_fallback() -> None:
    css = WIZARD_CSS.read_text(encoding="utf-8")

    assert ".exception-card" in css
    assert ".evidence-grid" in css
    assert ".typed-grid" in css
    mobile = css[css.index("@media (max-width: 720px)") :]
    assert ".evidence-grid" in mobile
    assert "grid-template-columns: 1fr" in mobile


def test_visible_resume_routes_current_and_historical_states() -> None:
    html = WIZARD_HTML.read_text(encoding="utf-8")
    js = WIZARD_JS.read_text(encoding="utf-8")

    assert 'id="run-list"' in html
    assert "async function loadSessions()" in js
    assert "async function resumeSession(runId)" in js
    assert 'class="primary resume-run"' in js
    assert 'case "models_selected":' in js
    assert 'case "compiled_ready":' in js
    assert 'case "compiled_with_exceptions":' in js
    assert "await enterCompile();" in js
    assert 'case "decisions_in_progress":' in js
    assert "await enterReview();" in js


def test_forward_flow_has_keyboard_and_status_accessibility_hooks() -> None:
    html = WIZARD_HTML.read_text(encoding="utf-8")
    js = WIZARD_JS.read_text(encoding="utf-8")
    css = WIZARD_CSS.read_text(encoding="utf-8")

    assert '<nav aria-label="Ingest progress">' in html
    assert '<ol class="stepper" id="stepper">' in html
    assert 'role="alert"' in html
    assert 'aria-current", "step"' in js
    assert 'type="button" class="file-row file-choice' in js
    assert "button:focus-visible" in css
