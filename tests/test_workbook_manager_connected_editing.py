"""Checkpoint 3C-3E frontend shell and contextual editor contracts.

The production frontend has no DOM test dependency. Behavioral helpers are
exercised through Node, while shell accessibility, renderer ownership, and
contextual-editor wiring are checked from the shipped source. Browser evidence
remains a separate gate.
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
        "{name:'key', control:{kind:'short_text', label:'Key', blank:'never_blank_key'}},"
        "{name:'notes', control:{kind:'long_text', label:'Notes', blank:'allowed'}}"
        "]};"
        "console.log(JSON.stringify({"
        "errors:api.validateDraft(schema,{name:'',key:'',notes:''}),"
        "validKey:api.validateField(schema.columns[1],'option-key'),"
        "unchanged:api.isDraftDirty(schema,{name:'A',key:'K',notes:null},{name:'A',key:'K',notes:''}),"
        "changed:api.isDraftDirty(schema,{name:'A',key:'K',notes:''},{name:'B',key:'K',notes:''})"
        "}));"
    )

    assert result == {
        "errors": {"name": "Name is required.", "key": "Key is required."},
        "validKey": "",
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
        "!focusable.includes(document.activeElement)",
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
    assert 'if (event.key === "Enter") event.preventDefault();' in source
    assert '["forbidden", "never_blank_key"].includes(control.blank)' in source


def test_shell_css_is_a_desktop_drawer_and_narrow_full_screen_sheet():
    source = (FRONTEND / "styles.css").read_text()

    assert ".editor-backdrop" in source
    assert "position: fixed" in source
    assert ".editor-shell" in source
    assert ".editor-footer" in source
    assert "position: sticky" in source
    assert "@media (max-width: 760px)" in source
    assert ".editor-shell { width: 100%; max-width: none; height: 100%;" in source


# ── Checkpoint 3D — contextual option editor (spec §16 subpass 4) ────────────


OPTION_EDITOR_MODULE = FRONTEND / "optionEditorModel.js"


def run_option_model(script: str):
    result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "--eval",
            (
                "import { pathToFileURL } from 'node:url';"
                f"const moduleUrl = pathToFileURL({json.dumps(str(OPTION_EDITOR_MODULE))}).href;"
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


CONNECTED_DETAIL = {
    "model_key": "stingray",
    "entity_type": "option",
    "destination": {
        "workspace": "options", "entity_type": "option", "entity_id": "opt_x_001",
    },
    "option": {
        "option_id": "opt_x_001", "rpo": "5ZU",
        "option_name": "Body-Color High Wing Spoiler", "name": "Body-Color High Wing Spoiler",
        "price": "625", "description": "Spoiler.", "detail_raw": "",
        "section_id": "sec_spoi_001", "selectable": "True",
        "display_order": "30", "active": "True", "display_behavior": "",
        "src_sheet": "stingray_options", "src_row": 12, "physical_key": "[\"opt_x_001\"]",
    },
    "section": {"section_id": "sec_spoi_001", "section_name": "Spoilers"},
    "availability": [],
    "exclusive_groups": [{"group_id": "g1", "member_count": 4}],
    "rule_groups": [],
    "rules": [{"rule_id": "r1"}, {"rule_id": "r2"}],
    "pricing": [],
    "variant_overrides": [{"override_id": "v1"}],
    "default_rules": [{"rule_id": "d1"}],
    "assets": [],
}


CONNECTED_SCHEMA = {
    "table": "options",
    "key": ["option_id"],
    "columns": [
        {"name": name, "control": {"kind": "short_text"}}
        for name in [
            "option_id", "rpo", "price", "option_name", "description",
            "detail_raw", "section_id", "selectable", "display_order",
            "display_behavior", "active",
        ]
    ],
}


def test_connected_option_detail_derives_a_prefilled_registry_draft():
    """The editor opens pre-filled from the connected detail, not a raw row."""
    result = run_option_model(
        "console.log(JSON.stringify(api.initialDraftFromDetail("
        + json.dumps(CONNECTED_DETAIL) + ", "
        + json.dumps(CONNECTED_SCHEMA)
        + ")));"
    )
    draft = result["draft"]

    # Every projected option field the operator edits is prefilled from the
    # connected detail; blank stays blank rather than the string "null".
    assert draft["option_id"] == "opt_x_001"
    assert draft["rpo"] == "5ZU"
    assert draft["option_name"] == "Body-Color High Wing Spoiler"
    assert draft["price"] == "625"
    assert draft["section_id"] == "sec_spoi_001"
    assert draft["selectable"] == "True"
    assert draft["display_order"] == "30"
    assert draft["active"] == "True"
    assert draft["display_behavior"] == ""

    assert result["target"]["table"] == "options"
    assert result["target"]["key"] == {"option_id": "opt_x_001"}
    assert result["target"]["model_id"] == "stingray"
    assert result["label"] == "5ZU — Body-Color High Wing Spoiler"
    assert result["lineage"]["source_sheet"] == "stingray_options"
    assert result["lineage"]["source_row"] == 12


def test_option_editor_fields_come_from_the_registry_schema_not_a_local_list():
    """The editable field set is the schema's, so registry additions are kept."""
    schema = {
        "columns": [
            {"name": "option_id", "control": {"kind": "immutable"}},
            {"name": "rpo", "control": {"kind": "short_text"}},
            {"name": "brand_new_registry_column", "control": {"kind": "short_text"}},
        ],
    }
    detail = {
        "model_key": "stingray",
        "option": {
            "option_id": "opt_x_001", "rpo": "5ZU", "src_sheet": "s",
            "src_row": 1, "physical_key": '["opt_x_001"]',
        },
    }
    result = run_option_model(
        "console.log(JSON.stringify(api.initialDraftFromDetail("
        + json.dumps(detail) + ", " + json.dumps(schema)
        + ")));"
    )

    # A column the registry added after this file was written is prefilled
    # from the projection rather than silently initialized to "" — a stale
    # local list here would erase its workbook value on an unrelated save.
    assert result["draft"]["brand_new_registry_column"] == ""
    assert set(result["draft"]) == {
        "option_id", "rpo", "brand_new_registry_column",
    }

    source = (FRONTEND / "optionEditorModel.js").read_text()
    assert "OPTION_FIELD_ORDER" not in source
    # No parallel field list may reappear: field names may only occur in the
    # generic helpers, never as an enumerated editable set.
    assert '"option_name"' not in source
    assert '"display_order"' not in source


def test_editor_seeds_reopened_forms_from_the_coalesced_draft_operation():
    """Reopening or Keep-editing must not resubmit projected over drafted values."""
    projected = run_option_model(
        "const d = api.initialDraftFromDetail("
        + json.dumps(CONNECTED_DETAIL) + ", "
        + json.dumps(CONNECTED_SCHEMA) + ");"
        "console.log(JSON.stringify({"
        "target: d.target,"
        "seeded: api.applyDraftOverlay(d.draft, "
        + json.dumps({
            "final": {
                "price": 700,
                "option_name": "Drafted wing name",
                "detail_raw": None,
                "selectable": "",
            },
        })
        + ")"
        "}));"
    )
    seeded = projected["seeded"]

    # Drafted non-blank values win; NULL/blank final entries keep the
    # projected value because both render as "not specified / inherit".
    assert seeded["price"] == "700"
    assert seeded["option_name"] == "Drafted wing name"
    assert seeded["detail_raw"] == ""
    assert seeded["selectable"] == "True"

    operations = [
        {"id": 1, "source_sheet": "other_sheet", "physical_key": '["opt_z_009"]',
         "final": {"price": 999}},
        {"id": 2, "source_sheet": "stingray_options",
         "physical_key": '["opt_x_001"]', "final": {"price": 700}},
    ]
    match = run_option_model(
        "console.log(JSON.stringify(api.matchingDraftOperation("
        + json.dumps(operations) + ", "
        + json.dumps(projected["target"])
        + ")));"
    )
    assert match["id"] == 2

    no_match = run_option_model(
        "console.log(JSON.stringify(api.matchingDraftOperation("
        + json.dumps(operations[:1]) + ", "
        + json.dumps(projected["target"])
        + ")));"
    )
    assert no_match is None

    source = (FRONTEND / "components" / "OptionEditor.jsx").read_text()
    # The component seeds the form from durable evidence before allowing a save.
    assert "applyDraftOverlay" in source
    assert "matchingDraftOperation" in source


def test_relationship_impact_is_summarized_from_the_connected_detail():
    """Direct impact counts come from the same connected read, not new queries."""
    result = run_option_model(
        "console.log(JSON.stringify(api.relationshipImpact("
        + json.dumps(CONNECTED_DETAIL)
        + ")));"
    )

    # Counts only; §10.6 keeps relationships as semantic panels that link out.
    assert result == {
        "availability": 0,
        "groups": 1,
        "rules": 2,
        "pricingRules": 0,
        "variantOverrides": 1,
        "defaultRules": 1,
        "images": 0,
    }


def test_option_editor_target_binds_to_this_exact_projected_row():
    result = run_option_model(
        "console.log(JSON.stringify(api.editorTarget("
        + json.dumps(CONNECTED_DETAIL)
        + ")));"
    )
    assert result["table"] == "options"
    assert result["model_id"] == "stingray"
    assert result["key"] == {"option_id": "opt_x_001"}
    assert result["lineage"] == {
        "source_sheet": "stingray_options",
        "source_row": 12,
        "physical_key": '["opt_x_001"]',
    }


def test_contextual_option_editor_wires_the_shared_shell_and_registry_controls():
    source = (FRONTEND / "components" / "OptionEditor.jsx").read_text()
    explorer_source = (FRONTEND / "components" / "ConnectedExplorer.jsx").read_text()

    # The contextual drawer reuses the 3C shell and the schema-driven form;
    # it does not fork a second renderer map or bypass registry controls.
    assert "EditorShell" in source
    assert "RecordForm" in source
    assert "CONTROL_RENDERERS" not in source

    # Field headings are contextual, while renderer kinds and validation remain
    # owned by the registry controls RecordForm renders.
    assert "control.kind" not in source.replace("RecordForm", "")
    assert "Identity and customer copy" in source
    assert "Form placement and display" in source
    assert "Base pricing" in source

    # Opened from connected context, with the entity-specific §12 verb.
    assert "Save option change to draft" in source
    assert "api.schema" in source or "schema(table" in source
    assert "api.connectedOption" in explorer_source

    # After Save the drawer stays open on this entity's overlay/impact view
    # instead of closing back to the read-only detail.
    assert "overlay" in source.lower()
    assert "impact" in source.lower()


def test_explorer_offers_edit_only_for_mutable_options_in_context():
    explorer_source = (FRONTEND / "components" / "ConnectedExplorer.jsx").read_text()
    app_source = (FRONTEND / "App.jsx").read_text()

    # The edit affordance lives on the connected option detail and requires an
    # active mutable draft plus readiness; it never writes outside the draft lane.
    assert "OptionEditor" in explorer_source
    assert "draftMutable" in explorer_source
    assert "draftId" in explorer_source
    assert "onChanged" in explorer_source
    assert "draftId={draftId}" in explorer_source
    assert "draftMutable={draftMutable}" in explorer_source
    assert "api.saveDraftOperation" not in explorer_source
    assert "draftId={draftId}" in app_source
    assert "draftMutable={draftMutable}" in app_source
    # Saving must refresh draft evidence without toggling the app-level ready
    # state, which would unmount the connected explorer and lose the immediate
    # post-Save overlay required by 3D.
    assert "refreshDraftInPlace" in app_source
    connected_wiring = app_source[app_source.index("<ConnectedExplorer"):]
    assert "onChanged={refreshDraftInPlace}" in connected_wiring


# ── Checkpoint 3E — contextual group/member editor (spec §16 subpass 5) ─────


GROUP_EDITOR_MODULE = FRONTEND / "groupEditorModel.js"


def run_group_model(script: str):
    result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "--eval",
            (
                "import { pathToFileURL } from 'node:url';"
                f"const moduleUrl = pathToFileURL({json.dumps(str(GROUP_EDITOR_MODULE))}).href;"
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


CONNECTED_GROUP_DETAIL = {
    "model_key": "stingray",
    "entity_type": "group",
    "group_type": "exclusive",
    "group_id": "excl_wheels",
    "label": "Wheel selection",
    "group": {
        "group_id": "excl_wheels", "display_label": "Wheel selection",
        "selection_mode": "single_within_group", "active": "True", "notes": "",
        "src_sheet": "exclusive_groups", "src_row": 12,
        "physical_key": '["excl_wheels"]',
    },
    "members": [
        {
            "group_id": "excl_wheels", "option_id": "opt_a", "rpo": "A1",
            "option_name": "Alpha wheel", "display_order": "10", "active": "True",
            "src_sheet": "exclusive_group_members", "src_row": 20,
            "physical_key": '["excl_wheels","opt_a"]',
        },
        {
            "group_id": "excl_wheels", "option_id": "opt_b", "rpo": "B2",
            "option_name": "Bravo wheel", "display_order": "20", "active": "True",
            "src_sheet": "exclusive_group_members", "src_row": 21,
            "physical_key": '["excl_wheels","opt_b"]',
        },
    ],
    "editor": {
        "group_table": "exclusive_groups",
        "member_table": "exclusive_group_members",
        "member_id_field": "option_id",
        "member_group_field": "group_id",
        "member_order_field": "display_order",
        "member_active_field": "active",
    },
    "technical": {"lineage": {"source_sheet": "exclusive_groups"}},
}

CONNECTED_GROUP_SCHEMA = {
    "table": "exclusive_groups",
    "key": ["group_id"],
    "columns": [
        {"name": name, "control": {"kind": "short_text"}}
        for name in ["group_id", "display_label", "selection_mode", "active", "notes"]
    ],
}


def test_connected_group_detail_derives_registry_group_draft_and_semantic_targets():
    result = run_group_model(
        "console.log(JSON.stringify(api.initialGroupDraft("
        + json.dumps(CONNECTED_GROUP_DETAIL) + ", "
        + json.dumps(CONNECTED_GROUP_SCHEMA)
        + ")));"
    )

    assert result["draft"] == {
        "group_id": "excl_wheels",
        "display_label": "Wheel selection",
        "selection_mode": "single_within_group",
        "active": "True",
        "notes": "",
    }
    assert result["target"] == {
        "table": "exclusive_groups",
        "model_id": "stingray",
        "key": {"group_id": "excl_wheels"},
    }
    assert result["member_table"] == "exclusive_group_members"
    assert result["member_id_field"] == "option_id"
    assert result["member_group_field"] == "group_id"
    assert result["member_order_field"] == "display_order"
    assert result["member_active_field"] == "active"


def test_group_editor_reopens_from_the_coalesced_parent_operation():
    operation = {
        "table_name": "exclusive_groups",
        "source_sheet": "exclusive_groups",
        "physical_key": '["excl_wheels"]',
        "final": {
            "group_id": "excl_wheels", "display_label": "Draft wheel choices",
            "selection_mode": "required_single_within_group", "active": "True",
            "notes": None,
        },
    }
    result = run_group_model(
        "const initial=api.initialGroupDraft("
        + json.dumps(CONNECTED_GROUP_DETAIL) + ", "
        + json.dumps(CONNECTED_GROUP_SCHEMA) + ");"
        "const operation=api.matchingGroupOperation("
        + json.dumps([operation]) + ", "
        + json.dumps(CONNECTED_GROUP_DETAIL) + ");"
        "console.log(JSON.stringify(api.applyGroupDraftOverlay(initial.draft,operation)));"
    )

    assert result["display_label"] == "Draft wheel choices"
    assert result["selection_mode"] == "required_single_within_group"
    assert result["notes"] == ""


def test_durable_member_overlay_produces_one_deterministic_final_order():
    operations = [
        {
            "table_name": "exclusive_group_members", "action": "update",
            "entity_key": {"group_id": "excl_wheels", "option_id": "opt_a"},
            "final": {"group_id": "excl_wheels", "option_id": "opt_a",
                      "display_order": 20, "active": "True"},
        },
        {
            "table_name": "exclusive_group_members", "action": "update",
            "entity_key": {"group_id": "excl_wheels", "option_id": "opt_b"},
            "final": {"group_id": "excl_wheels", "option_id": "opt_b",
                      "display_order": 10, "active": "True"},
        },
        {
            "table_name": "exclusive_group_members", "action": "add",
            "entity_key": {"group_id": "excl_wheels", "option_id": "opt_c"},
            "final": {"group_id": "excl_wheels", "option_id": "opt_c",
                      "display_order": 30, "active": "True"},
        },
    ]
    result = run_group_model(
        "console.log(JSON.stringify(api.effectiveMembers("
        + json.dumps(CONNECTED_GROUP_DETAIL) + ", "
        + json.dumps(operations) + ", {opt_c:'C3 — Carbon wheel'}"
        + ")));"
    )

    assert [row["member_id"] for row in result] == ["opt_b", "opt_a", "opt_c"]
    assert [row["display_order"] for row in result] == [10, 20, 30]
    assert result[2]["label"] == "C3 — Carbon wheel"


def test_member_move_and_operation_plan_are_bounded_and_reversible():
    result = run_group_model(
        "const original=api.effectiveMembers("
        + json.dumps(CONNECTED_GROUP_DETAIL) + ", []);"
        "const moved=api.moveMember(original,'opt_b',-1);"
        "const plan=api.membershipOperations(original,moved,"
        + json.dumps(CONNECTED_GROUP_DETAIL) + ");"
        "const restored=api.moveMember(moved,'opt_b',1);"
        "console.log(JSON.stringify({moved,plan,restoredPlan:api.membershipOperations(original,restored,"
        + json.dumps(CONNECTED_GROUP_DETAIL) + ")}));"
    )

    assert [row["member_id"] for row in result["moved"]] == ["opt_b", "opt_a"]
    assert [row["display_order"] for row in result["moved"]] == [10, 20]
    assert len(result["plan"]) == 2
    assert {row["op"] for row in result["plan"]} == {"update"}
    assert result["restoredPlan"] == []


def test_member_planning_uses_backend_relationship_field_metadata():
    detail = json.loads(json.dumps(CONNECTED_GROUP_DETAIL))
    detail["editor"].update({
        "member_id_field": "choice_key",
        "member_group_field": "parent_key",
        "member_order_field": "sequence",
        "member_active_field": "enabled",
    })
    detail["members"] = [{
        "parent_key": "excl_wheels", "choice_key": "opt_a", "sequence": 5,
        "enabled": True, "option_name": "Alpha",
    }]
    result = run_group_model(
        "const original=api.effectiveMembers(" + json.dumps(detail) + ", []);"
        "const desired=[...original,{parent_key:'excl_wheels',choice_key:'opt_b',"
        "sequence:15,enabled:true,member_id:'opt_b',label:'Beta'}];"
        "console.log(JSON.stringify({original,plan:api.membershipOperations(original,desired,"
        + json.dumps(detail) + ")}));"
    )

    assert result["original"][0]["display_order"] == 5
    assert result["original"][0]["active"] is True
    assert result["plan"] == [{
        "table": "exclusive_group_members",
        "model_id": "stingray",
        "op": "add",
        "key": {
            "parent_key": "excl_wheels",
            "choice_key": "opt_b",
        },
        "record": {
            "parent_key": "excl_wheels",
            "choice_key": "opt_b",
            "sequence": 15,
            "enabled": True,
        },
    }]


def test_group_editor_wires_existing_draft_dependency_and_registry_contracts():
    source = (FRONTEND / "components" / "GroupEditor.jsx").read_text()
    explorer_source = (FRONTEND / "components" / "ConnectedExplorer.jsx").read_text()

    assert "RecordForm" in source
    assert "EditorShell" in source
    assert "CONTROL_RENDERERS" not in source
    assert "api.schema" in source
    assert "api.referenceOptions" in source
    assert "api.saveDraftOperation" in source
    assert "api.dependencies" in source
    assert "hasSubmitted ? savedOperation" in source
    assert "Move up" in source
    assert "Move down" in source
    assert "Proposed final order" in source
    assert "Add existing member" in source
    assert "Add group" not in source
    assert "GroupEditor" in explorer_source
    assert "draftMutable" in explorer_source
    assert "api.saveDraftOperation" not in explorer_source
