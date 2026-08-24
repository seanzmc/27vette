"""Checkpoint 3C frontend editor-shell contracts.

The production frontend has no DOM test dependency. Behavioral helpers are
exercised through Node, while shell accessibility and renderer ownership are
checked from the shipped source. Browser evidence remains a separate gate.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "workbook-manager" / "frontend" / "src"
VALIDATION_MODULE = FRONTEND / "editorValidation.js"


def run_validation(script: str):
    result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "--eval",
            (
                "import { pathToFileURL } from 'node:url';"
                f"const moduleUrl = pathToFileURL({json.dumps(str(VALIDATION_MODULE))}).href;"
                "const api = await import(moduleUrl);"
                + script
            ),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_finite_control_rejects_values_outside_registry_domain():
    result = run_validation(
        "console.log(JSON.stringify({"
        "valid: api.validateField({name:'active', control:{kind:'finite', "
        "blank:'forbidden', values:['yes','no']}}, 'yes'),"
        "invalid: api.validateField({name:'active', control:{kind:'finite', "
        "blank:'forbidden', values:['yes','no']}}, 'maybe')"
        "}));"
    )

    assert result == {
        "valid": "",
        "invalid": "Choose Active from the accepted values: yes, no.",
    }


def test_numeric_and_url_controls_apply_registered_constraints():
    result = run_validation(
        "const number={name:'order', control:{kind:'integer', blank:'forbidden', min:1, max:9, step:1}};"
        "const url={name:'image_url', control:{kind:'url', blank:'allowed'}};"
        "console.log(JSON.stringify({"
        "notInteger:api.validateField(number,'2.5'),"
        "tooLarge:api.validateField(number,'10'),"
        "validInteger:api.validateField(number,'2'),"
        "badUrl:api.validateField(url,'not a url'),"
        "validUrl:api.validateField(url,'https://example.com/a.jpg')"
        "}));"
    )

    assert result == {
        "notInteger": "Order must be a whole number.",
        "tooLarge": "Order must be no more than 9.",
        "validInteger": "",
        "badUrl": "Image url must be a complete http or https URL.",
        "validUrl": "",
    }


def test_reference_validation_rejects_stale_and_unavailable_values():
    result = run_validation(
        "const column={name:'section_id', control:{kind:'reference', label:'Section', blank:'forbidden'}};"
        "console.log(JSON.stringify({"
        "valid:api.validateField(column,'sec_good', {loaded:true,options:[{value:'sec_good'}]}),"
        "stale:api.validateField(column,'sec_old', {loaded:true,options:[{value:'sec_good'}]}),"
        "missing:api.validateField(column,'sec_old', {loaded:true,options:[]}),"
        "unavailable:api.validateField(column,'sec_good', {error:'lookup failed'})"
        "}));"
    )

    assert result == {
        "valid": "",
        "stale": "Current value is not valid for this field. Choose an available Section.",
        "missing": "Current value is not valid for this field. Choose an available Section.",
        "unavailable": "Section choices are unavailable: lookup failed",
    }


def test_draft_validation_and_dirty_state_are_deterministic():
    result = run_validation(
        "const schema={columns:["
        "{name:'name', control:{kind:'short_text', label:'Name', blank:'forbidden'}},"
        "{name:'notes', control:{kind:'long_text', label:'Notes', blank:'allowed'}}"
        "]};"
        "console.log(JSON.stringify({"
        "errors:api.validateDraft(schema,{name:'',notes:''}),"
        "unchanged:api.isDraftDirty(schema,{name:'A',notes:null},{name:'A',notes:''}),"
        "changed:api.isDraftDirty(schema,{name:'A',notes:''},{name:'B',notes:''})"
        "}));"
    )

    assert result == {
        "errors": {"name": "Name is required."},
        "unchanged": False,
        "changed": True,
    }


def test_reusable_shell_owns_dialog_focus_close_and_scroll_contracts():
    source = (FRONTEND / "components" / "EditorShell.jsx").read_text()

    for required in (
        'role="dialog"',
        'aria-modal="true"',
        'event.key !== "Tab"',
        'event.key === "Escape"',
        "document.body.style.overflow",
        "useLayoutEffect",
        "opener.focus()",
        "window.confirm",
        'className="editor-footer"',
    ):
        assert required in source


def test_record_form_has_an_explicit_renderer_for_every_registered_kind():
    source = (FRONTEND / "components" / "RecordForm.jsx").read_text()
    kinds = {
        "boolean", "finite", "reference", "integer", "money", "url",
        "structured_text", "short_text", "long_text", "immutable",
        "generated", "read_only",
    }

    for kind in kinds:
        assert f"{kind}:" in source
    assert "CONTROL_RENDERERS[control.kind]" in source
    assert "Unsupported control kind" in source
    assert "field_kind" not in source
    assert "api.referenceOptions" in source
    assert "limit: 100" in source


def test_record_form_validates_before_one_in_flight_draft_save():
    source = (FRONTEND / "components" / "RecordForm.jsx").read_text()

    assert "validateDraft(schema, draft, referenceStates)" in source
    assert "busyRef.current" in source
    assert "disabled={busy}" in source
    assert "firstInvalid.focus()" in source
    assert "dirty={dirty}" in source


def test_shell_css_is_a_desktop_drawer_and_narrow_full_screen_sheet():
    source = (FRONTEND / "styles.css").read_text()

    assert ".editor-backdrop" in source
    assert "position: fixed" in source
    assert ".editor-shell" in source
    assert ".editor-footer" in source
    assert "position: sticky" in source
    assert "@media (max-width: 760px)" in source
    assert ".editor-shell { width: 100%; max-width: none; height: 100%;" in source
