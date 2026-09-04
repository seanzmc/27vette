"""Checkpoint 3C-3F frontend shell and contextual editor contracts.

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
NAVIGATION_MODULE = FRONTEND / "navigationState.js"
GRAPH_OPERATIONS_MODULE = FRONTEND / "graphOperationsModel.js"


def run_navigation(script: str):
    result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "--eval",
            (
                "import { pathToFileURL } from 'node:url';"
                f"const moduleUrl = pathToFileURL({json.dumps(str(NAVIGATION_MODULE))}).href;"
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


def run_graph_operations(script: str):
    result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "--eval",
            (
                "import { pathToFileURL } from 'node:url';"
                f"const moduleUrl = pathToFileURL({json.dumps(str(GRAPH_OPERATIONS_MODULE))}).href;"
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


def test_guided_option_plan_requires_explicit_status_for_every_active_variant():
    result = run_graph_operations(
        "const option={table:'options',model_id:'z06',op:'add',"
        "key:{option_id:'opt_new'},record:{option_id:'opt_new',rpo:'NEW'}};"
        "const variants=[{variant_id:'coupe'},{variant_id:'convertible'}];"
        "const incomplete=api.optionCreationPlan(option,variants,{coupe:'available'});"
        "const complete=api.optionCreationPlan(option,variants,{"
        "coupe:'available',convertible:'unavailable'});"
        "console.log(JSON.stringify({incomplete,complete}));"
    )
    assert result["incomplete"]["complete"] is False
    assert result["incomplete"]["missing_variant_ids"] == ["convertible"]
    assert result["incomplete"]["operations"] == []
    assert result["complete"]["complete"] is True
    assert result["complete"]["missing_variant_ids"] == []
    assert result["complete"]["operations"][0]["table"] == "options"
    assert [operation["key"]["variant_id"] for operation in result["complete"]["operations"][1:]] == [
        "coupe", "convertible",
    ]
    assert [operation["record"]["status"] for operation in result["complete"]["operations"][1:]] == [
        "available", "unavailable",
    ]


def test_dependency_plan_emits_only_explicit_complete_selection():
    result = run_graph_operations(
        "const root={table:'options',model_id:'stingray',key:{option_id:'opt_x'}};"
        "const deps=["
        "{table:'option_availability',model_id:'stingray',entity_key:{option_id:'opt_x',variant_id:'v1'}},"
        "{table:'rule_groups',model_id:'stingray',entity_key:{group_id:'g1'},allowed_actions:['keep','delete','deactivate']}];"
        "const incomplete=api.dependencyDeletionOperations(root,deps,{'0':'delete'});"
        "const complete=api.dependencyDeletionOperations(root,deps,{'0':'delete','1':'deactivate'});"
        "console.log(JSON.stringify({incomplete,complete}));"
    )
    assert result["incomplete"]["complete"] is False
    assert result["incomplete"]["operations"] == []
    assert result["complete"]["complete"] is True
    assert result["complete"]["operations"][-1]["table"] == "options"
    assert result["complete"]["operations"][0]["op"] == "delete"
    assert result["complete"]["operations"][1]["record"] == {"active": "False"}


def test_checkpoint_2a_raw_ui_wires_confirmation_undo_and_context_preservation():
    operations = (FRONTEND / "components" / "ModelOperations.jsx").read_text()
    api_source = (FRONTEND / "api.js").read_text()
    app_source = (FRONTEND / "App.jsx").read_text()

    for phrase in (
        "Set availability for every active variant",
        "Delete plan",
        "Nothing is selected automatically",
        "Confirm delete",
        "Undo delete",
    ):
        assert phrase in operations
    assert "api.guidedOptionContext" in operations
    assert "api.dependencyPlan" in operations
    assert "api.saveDraftOperationPlan" in operations
    assert "api.discardDraftOperation" in operations
    assert "disabled={!guidedPlan?.complete}" in operations
    assert "restoreScrollPosition(scrollTop)" in operations
    assert operations.count("const scrollTop = window.scrollY") >= 4
    assert "navigation={navigation}" in app_source
    assert "onNavigationChange={commitNavigation}" in app_source
    assert "onChanged={refreshDraftInPlace}" in app_source
    assert "/api/graph/option-create/" in api_source
    assert "/dependency-plan" in api_source
    assert "/operation-plan" in api_source


def test_undo_delete_matches_prior_operations_by_model_identity():
    source = (FRONTEND / "components" / "ModelOperations.jsx").read_text()
    scope = (FRONTEND / "operationScope.js").read_text()

    # Codex P2 (PR 69): entity keys such as option_id collide across models
    # in model-scoped collections, so the undo prior-operation lookup must
    # also match the stored model identity instead of restoring another
    # model's operation for the same key.
    assert "const scopedModel = operationModelId(schema, row, modelKey)" in source
    assert 'String(candidate.model_id ?? "") === scopedModel' in source
    assert "model_id: scopedModel" in source
    assert "context.source === \"row_model_key\"" in scope


def test_advanced_navigation_round_trips_collection_query_offset_and_editor_context():
    result = run_navigation(
        "const parsed=api.parseNavigation('?model=z06&workspace=advanced&'"
        "+'collection=option_availability&query=carbon&offset=200&editor=opt_c1');"
        "console.log(JSON.stringify({parsed,serialized:api.serializeNavigation(parsed)}));"
    )
    assert result == {
        "parsed": {
            "model": "z06",
            "workspace": "advanced",
            "type": "",
            "id": "",
            "query": "carbon",
            "collection": "option_availability",
            "offset": 200,
            "editor": "opt_c1",
        },
        "serialized": (
            "?model=z06&workspace=advanced&query=carbon&collection=option_availability"
            "&offset=200&editor=opt_c1"
        ),
    }


def test_navigation_state_round_trips_only_canonical_reloadable_context():
    result = run_navigation(
        "const parsed=api.parseNavigation('?model=grand_sport_x&workspace=groups&'"
        "+'type=exclusive_group&id=group_x&query=engine');"
        "const normalized=api.navigationForDestination(parsed,{"
        "workspace:'groups',entity_type:'group',entity_id:'rule:rule_y'});"
        "console.log(JSON.stringify({"
        "parsed,"
        "serialized:api.serializeNavigation(parsed),"
        "normalized"
        "}));"
    )

    assert result == {
        "parsed": {
            "model": "grand_sport_x",
            "workspace": "groups",
            "type": "exclusive_group",
            "id": "group_x",
            "query": "engine",
        },
        "serialized": (
            "?model=grand_sport_x&workspace=groups&type=exclusive_group"
            "&id=group_x&query=engine"
        ),
        "normalized": {
            "model": "grand_sport_x",
            "workspace": "groups",
            "type": "rule_group",
            "id": "rule_y",
            "query": "engine",
        },
    }


def test_detail_clears_cross_model_selection_before_the_next_load():
    source = (FRONTEND / "components" / "ConnectedExplorer.jsx").read_text()

    # Codex P1 (PR 50): when modelKey changes with a detail open, the stale
    # detail must stop rendering immediately instead of staying interactive
    # until the replacement request resolves.
    assert (
        "setSelected((current) => (current?.model_key === modelKey ? current : null))"
        in source
    )
    load_effect = source.index("const generation = ++detailRequest.current;")
    guard = source.index("current?.model_key === modelKey")
    assert 0 < guard - load_effect < 800


def test_checkpoint_3a_navigation_round_trips_index_search_and_diagnostics_modes():
    result = run_navigation(
        "const index=api.parseNavigation('?model=z06&workspace=groups&group_type=rule&offset=24');"
        "const search=api.parseNavigation('?model=z06&workspace=groups&query=Z51');"
        "const diagnostic=api.parseNavigation('?model=z06&workspace=groups&diagnostic=missing_required_images');"
        "console.log(JSON.stringify({index,search,diagnostic,serialized:api.serializeNavigation(diagnostic)}));"
    )
    assert result["index"]["group_type"] == "rule"
    assert result["index"]["offset"] == 24
    assert result["search"]["query"] == "Z51"
    assert result["diagnostic"]["diagnostic"] == "missing_required_images"
    assert result["serialized"].endswith("diagnostic=missing_required_images")


def test_checkpoint_3a_explorer_has_distinct_index_search_and_diagnostics_presentations():
    source = (FRONTEND / "components" / "ConnectedExplorer.jsx").read_text()
    api_source = (FRONTEND / "api.js").read_text()

    assert "api.explorerGroups" in source
    assert "Group type" in source
    assert "No groups match this model and group type." in source
    assert "Match reasons" in source
    assert "Diagnostics" in source
    assert "result.diagnostic.label" in source
    assert "explorerGroups:" in api_source


def test_groups_workspace_search_is_scoped_server_side_before_pagination():
    source = (FRONTEND / "components" / "ConnectedExplorer.jsx").read_text()
    api_source = (FRONTEND / "api.js").read_text()

    # The Groups workspace requests entity scoping from the backend, so the
    # page slice and pagination metadata describe the matching groups instead
    # of a combined ranking where other entity types can crowd them out.
    assert "entityType: mode === \"groups\" ? \"group\" : \"\"" in source
    assert "entity_type=${encodeURIComponent(entityType)}" in api_source


def test_explorer_guards_group_index_against_stale_responses():
    source = (FRONTEND / "components" / "ConnectedExplorer.jsx").read_text()

    # The group-index loader carries a generation check like the search and
    # detail loaders: a superseded response (model, group type, or page
    # switched mid-flight) must never overwrite groupPage or error.
    assert "groupRequest = useRef(0)" in source
    assert "const generation = ++groupRequest.current" in source
    assert source.count("generation !== groupRequest.current") == 2
    assert "if (generation !== groupRequest.current) return;" in source


def test_diagnostic_back_to_results_restores_retained_prediagnostic_navigation():
    source = (FRONTEND / "components" / "ConnectedExplorer.jsx").read_text()

    # runDiagnostic retains the exact pre-diagnostic navigation; the
    # diagnostic screen's "Back to results" restores it with replace so the
    # prior index/search returns exactly and no extra history entry is added.
    assert "preDiagnostic.current = navigation;" in source
    assert "onClick={backToIndex}" in source
    assert "onNavigationChange({ ...preDiagnostic.current }, { replace: true })" in source
    assert source.count("preDiagnostic.current = null;") == 2


def test_app_owns_native_history_and_reuses_lifecycle_for_the_draft_tray():
    app_source = (FRONTEND / "App.jsx").read_text()
    explorer_source = (FRONTEND / "components" / "ConnectedExplorer.jsx").read_text()
    api_source = (FRONTEND / "api.js").read_text()
    styles = (FRONTEND / "styles.css").read_text()

    assert "parseNavigation(window.location.search)" in app_source
    assert "window.history.pushState" in app_source
    assert "window.history.replaceState" in app_source
    assert 'window.addEventListener("popstate"' in app_source
    assert "}, [selectDraft, setTab]);" in app_source
    assert 'className="draft-tray"' in app_source
    assert 'className="model-context"' in app_source
    assert "value={modelKey}" in app_source
    assert "setModelKey(e.target.value)" in app_source
    assert "model.label" in app_source
    assert "draftLifecycle?.draft" in app_source
    assert "navigation={navigation}" in app_source
    assert "draftId" in explorer_source
    assert "navigation.type" in explorer_source
    assert "navigation.id" in explorer_source
    assert "connectedOption(modelKey, navigation.id, draftId)" in explorer_source
    assert "api.explorerSearch(modelKey, query," in explorer_source
    assert "draftRevision" in explorer_source
    assert "draft_overlay" in explorer_source
    assert "detailError" in explorer_source
    assert "focusKey" in explorer_source
    assert "[data-focus-key" in explorer_source
    assert "draft_id" in api_source
    assert ".draft-tray" in styles
    assert ".draft-tray { width: 100%;" in styles
    assert ".entity-link > strong { grid-column: 1; overflow-wrap: anywhere; }" in styles
    assert ".entity-link > svg { grid-column: 2; grid-row: 1 / span 3; }" in styles


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
        "group_id_field": "group_id",
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


def test_blank_member_orders_are_normalized_before_add():
    detail = json.loads(json.dumps(CONNECTED_GROUP_DETAIL))
    detail["members"][0]["display_order"] = ""
    detail["members"][1]["display_order"] = None
    result = run_group_model(
        "const normalized=api.effectiveMembers(" + json.dumps(detail) + ", []);"
        "const added=api.addMember(normalized," + json.dumps(detail)
        + ",'opt_c','C3 — Carbon wheel');"
        "console.log(JSON.stringify({normalized,added}));"
    )

    assert [row["display_order"] for row in result["normalized"]] == [10, 20]
    assert [row["display_order"] for row in result["added"]] == [10, 20, 30]


def test_parent_dependencies_use_the_draft_effective_member_set():
    dependents = [
        {"table": "exclusive_group_members", "key": {"option_id": "opt_a"}},
        {"table": "exclusive_group_members", "key": {"option_id": "opt_b"}},
        {"table": "rule_mappings", "key": {"rule_id": "rule_1"}},
    ]
    result = run_group_model(
        "console.log(JSON.stringify({"
        "afterDeletes:api.groupDependencyCounts(" + json.dumps(dependents) + ","
        + json.dumps(CONNECTED_GROUP_DETAIL) + ",[]),"
        "oneMember:api.groupDependencyCounts(" + json.dumps(dependents) + ","
        + json.dumps(CONNECTED_GROUP_DETAIL) + ",[{member_id:'opt_b'}])"
        "}));"
    )

    assert result["afterDeletes"] == [{"table": "rule_mappings", "count": 1}]
    assert result["oneMember"] == [
        {"table": "exclusive_group_members", "count": 1},
        {"table": "rule_mappings", "count": 1},
    ]


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
    assert "Save membership changes before removing the parent group" in source
    assert "hasSubmitted ? savedOperation" in source
    assert "Move up" in source
    assert "Move down" in source
    assert "Proposed final order" in source
    assert "Add existing member" in source
    assert "Add group" not in source
    assert "GroupEditor" in explorer_source
    assert "draftMutable" in explorer_source
    assert "api.saveDraftOperation" not in explorer_source


# ── Checkpoint 2C: one draft-effective overlay across connected surfaces ──────

DRAFT_OVERLAY_MODULE = FRONTEND / "draftOverlayModel.js"


def run_draft_overlay_model(script: str):
    result = subprocess.run(
        [
            "node",
            "--input-type=module",
            "--eval",
            (
                "import { pathToFileURL } from 'node:url';"
                f"const moduleUrl = pathToFileURL({json.dumps(str(DRAFT_OVERLAY_MODULE))}).href;"
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


MODIFIED_OVERLAY = {
    "draft_id": "d1", "draft_revision": 7, "state": "modified",
    "operation": {"id": 7, "action": "update", "table_name": "options"},
    "base": {"option_name": "Authored", "price": "625"},
    "proposed": {"option_name": "Proposed", "price": "625"},
    "effective": {"option_name": "Proposed", "price": "625"},
    "changed_fields": {"option_name": {"before": "Authored", "after": "Proposed"}},
    "direct_impact": {"rules": 2},
    "conflicts": [],
}


def test_draft_overlay_helpers_never_replace_authored_values_when_blocked_or_deleting():
    """EFFECTIVE-02/04: only modified/added overlays surface a proposed value;
    pending deletion and conflicted overlays keep the authored value and expose
    the exact blocking reason. The helpers read the adapter's shape and never
    re-diff rows."""
    conflicted = {
        **MODIFIED_OVERLAY, "state": "conflicted", "effective": None,
        "conflicts": [{"code": "draft_binding_stale",
                       "message": "The draft is bound to a different workbook import."}],
    }
    deleting = {**MODIFIED_OVERLAY, "state": "pending_deletion", "effective": None,
                "proposed": None}
    unchanged = {**MODIFIED_OVERLAY, "state": "unchanged", "operation": None,
                 "changed_fields": {}}
    result = run_draft_overlay_model(
        "const m=" + json.dumps(MODIFIED_OVERLAY) + ";"
        "const c=" + json.dumps(conflicted) + ";"
        "const d=" + json.dumps(deleting) + ";"
        "const u=" + json.dumps(unchanged) + ";"
        "console.log(JSON.stringify({"
        "modified: api.effectiveValue(m,'option_name','Authored'),"
        "untouched: api.effectiveValue(m,'price','625'),"
        "conflicted: api.effectiveValue(c,'option_name','Authored'),"
        "deleting: api.effectiveValue(d,'option_name','Authored'),"
        "blockReason: api.overlayBlockReason(c),"
        "noBlock: api.overlayBlockReason(m),"
        "labels: [m,c,d,u].map(api.overlayStateLabel),"
        "active: [m,c,d,u].map(api.hasDraftOverlay),"
        "change: api.fieldChange(m,'option_name'),"
        "opLabel: api.operationLabel(m),"
        "}));"
    )
    assert result["modified"] == "Proposed"
    assert result["untouched"] == "625"
    assert result["conflicted"] == "Authored"
    assert result["deleting"] == "Authored"
    assert result["blockReason"] == "The draft is bound to a different workbook import."
    assert result["noBlock"] == ""
    assert result["labels"] == [
        "Draft modified", "Draft blocked", "Draft deletion pending", "",
    ]
    assert result["active"] == [True, True, True, False]
    assert result["change"] == {"before": "Authored", "after": "Proposed"}
    assert result["opLabel"] == "operation 7 · update · options"


def test_saved_operation_projects_into_the_same_overlay_shape_as_the_backend():
    """An editor's post-Save panel renders the POST response through the same
    shape the detail routes return, so both go through one DraftOverlay."""
    operation = {
        "id": 12, "draft_id": "d1", "action": "delete", "table_name": "options",
        "family": "options", "model_id": "stingray", "source_sheet": "stingray_options",
        "source_row": 12, "physical_key": '["opt_x_001"]',
        "entity_key": {"option_id": "opt_x_001"},
        "original": {"option_name": "Authored"}, "final": None,
        "changed_fields": {"option_name": {"before": "Authored", "after": None}},
    }
    result = run_draft_overlay_model(
        "console.log(JSON.stringify(api.operationOverlay("
        + json.dumps(operation) + ", {rules: 2})));"
    )
    assert result["state"] == "pending_deletion"
    assert result["effective"] is None
    assert result["base"] == {"option_name": "Authored"}
    assert result["operation"]["id"] == 12
    assert result["operation"]["physical_key"] == '["opt_x_001"]'
    assert result["direct_impact"] == {"rules": 2}
    assert sorted(result) == sorted(MODIFIED_OVERLAY)


def test_section_heading_field_follows_the_owning_table():
    """Context-section edits change `section_name`, presentation edits change
    `display_label`; the heading lookup must follow the overlay's own
    operation, so context-section titles also show authored → proposed."""
    context_overlay = {
        **MODIFIED_OVERLAY,
        "operation": {
            **MODIFIED_OVERLAY["operation"], "table_name": "context_sections",
        },
        "changed_fields": {
            "section_name": {"before": "Authored title", "after": "Proposed title"},
        },
    }
    presentation_overlay = {
        **MODIFIED_OVERLAY,
        "operation": {
            **MODIFIED_OVERLAY["operation"], "table_name": "section_presentation",
        },
    }
    membership_overlay = {
        **MODIFIED_OVERLAY,
        "operation": None,
        "changed_fields": {"options": {"before": 9, "after": 11}},
    }
    result = run_draft_overlay_model(
        "const c=" + json.dumps(context_overlay) + ";"
        "const p=" + json.dumps(presentation_overlay) + ";"
        "const m=" + json.dumps(membership_overlay) + ";"
        "console.log(JSON.stringify({"
        "context: api.sectionHeadingField(c),"
        "presentation: api.sectionHeadingField(p),"
        "membership: api.sectionHeadingField(m),"
        "none: api.sectionHeadingField(null),"
        "}));"
    )
    assert result["context"] == "section_name"
    assert result["presentation"] == "display_label"
    assert result["membership"] == "display_label"
    assert result["none"] == "display_label"


def test_effective_text_keeps_display_semantics_and_backend_authored_values():
    """F1: the struck-through side must be the authored value. Structure nodes
    arrive already mutated to their effective value, so when the caller's
    `authored` prop provably mirrors `pair.after`, EffectiveText falls back to
    the backend-owned `pair.before` (Proposed → Proposed was the defect); props
    with their own display semantics (Yes/No, fallbacks) keep them."""
    shared = (FRONTEND / "components" / "DraftOverlay.jsx").read_text()
    # The mutated-node fallback and its guard are present in the one shared
    # renderer, so no surface can reintroduce the independent patch.
    assert "String(authored) === String(pair.after)" in shared
    assert "pair.before" in shared
    assert '<s className="authored-value">{authoredValue}</s>' in shared


def test_every_connected_surface_renders_the_one_shared_draft_overlay():
    """§7 2C item 1: no surface patches headings or diffs independently."""
    components = FRONTEND / "components"
    shared = (components / "DraftOverlay.jsx").read_text()
    assert "changedFieldEntries" in shared
    assert "overlayBlockReason" in shared
    assert "Authored" in shared and "Proposed" in shared

    for name in (
        "ConnectedExplorer.jsx", "SectionsLayout.jsx", "FormStructure.jsx",
        "OptionEditor.jsx", "GroupEditor.jsx", "AssetManager.jsx",
    ):
        source = (components / name).read_text()
        assert 'from "./DraftOverlay.jsx"' in source, name
        # The retired local renderers must not come back.
        assert "function DraftOverlay(" not in source, name
        assert "function FieldDiff(" not in source, name
        assert "<h3>Draft overlay</h3>" not in source, name
        assert ".replaceAll(\"_\", \" \")}</strong>" not in source.replace(
            "behavior?.replaceAll", "").replace("display_behavior.replaceAll", ""
        ).replace("rule_type?.replaceAll", "").replace("base_status.replaceAll", ""), name

    explorer = (components / "ConnectedExplorer.jsx").read_text()
    # Headings and facts read the draft-effective value, not only the authored one.
    assert 'field="option_name"' in explorer or 'effectiveValue(overlay, "option_name"' in explorer
    assert 'field="display_label"' in explorer
    assert "editDisabledReason(draftMutable, overlay)" in explorer
    structure = (components / "FormStructure.jsx").read_text()
    assert "api.structure(key, draftId)" in structure
    assert "draftRevision" in structure
    assets = (components / "AssetManager.jsx").read_text()
    assert "overlayBlockReason(item.draft_overlay)" in assets
    assert "canResolve" in assets
