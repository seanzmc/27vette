// Structural workbook conformance, driven entirely by the shared registry.
//
// AGENTS.md §3: `workbook_domain/registry.py` owns registered sheet families,
// writable columns, and shared enums. This gate asserts the canonical workbook
// conforms to that ownership — it does not maintain a second copy of it.
//
// What changed and why (Stage A rewrite): the retired version hardcoded three
// canonical source sheets, a 25-entry "future model" sheet list, and a
// three-model expectation block naming z06/zr1/zr1x with literal variant ids
// and eleven literal sheet names each. Six models are now workbook-active, so
// every one of those lists was a stale subset that reported green while
// covering less than the workbook contained. Everything structural now derives
// from `registered_sheet_families()` and `model_sheet_registry()`.
//
// A derived assertion cannot detect a change to the thing it derives from, so
// each derived sweep is paired with a named expectation that pins the shape the
// derivation must produce. Where those two disagree, the gate fails.
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import { workbookRegistrySnapshot } from "./lib/workbook-registry-snapshot.mjs";

// Approved one-source blocker clusters. A source option that blocks many
// targets is authored as one `excludes_any` rule group rather than a spray of
// direct excludes rows. Named here, not derived from the rows being checked.
const BLOCKER_CLUSTER_RPOS = {
  stingray: ["PCX", "PDV", "R88", "SFZ", "CF8"],
  grand_sport: ["R88", "SFZ", "CF8", "SHT"],
  z06: ["R88", "SFZ", "CF8", "SHT", "GBA"],
};

const snapshot = workbookRegistrySnapshot({ blockerClusterRpos: BLOCKER_CLUSTER_RPOS });

// Named expectations. These are the "what should be true" side of every
// derived sweep below; a derived set is never compared only against itself.
const EXPECTED_MODEL_KEYS = [
  "grand_sport",
  "grand_sport_x",
  "stingray",
  "z06",
  "zr1",
  "zr1x",
];

// Every generatable model must register all eleven generation source roles.
// Named here rather than derived from the same rows the check reads, so
// deleting a role row fails instead of quietly shrinking the expected set.
const EXPECTED_SOURCE_ROLES = [
  "color_overrides_sheet",
  "exclusive_group_members_sheet",
  "exclusive_groups_sheet",
  "interior_source_sheet",
  "price_rules_sheet",
  "rule_group_members_sheet",
  "rule_groups_sheet",
  "rule_mapping_sheet",
  "source_option_sheet",
  "status_sheet",
  "variant_option_overrides_sheet",
];

function liveRegistry() {
  const source = fs.readFileSync("form-app/data.js", "utf8");
  const json = source
    .split("window.CORVETTE_FORM_DATA = ", 2)[1]
    .split(";\nwindow.STINGRAY_FORM_DATA", 1)[0];
  return JSON.parse(json);
}

// Checkpoint 1 of the fast layered validation suite (spec §9) removed the
// duplicate schema invocation that stood here. This gate re-ran
// `scripts/validate_workbook_schema.py stingray_master.xlsx`, which the
// documented validation lane already runs directly, and that one call was
// 59.5% of the measured fourteen-gate node readiness lane. The schema command
// remains the single schema authority (catalog gate `cmd.workbook_schema`);
// this file owns only the structural conformance the command does not check.

test("every workbook-active model is registered with the full generation source role set", () => {
  const modelKeys = Object.keys(snapshot.models).sort();
  assert.deepEqual(
    modelKeys,
    EXPECTED_MODEL_KEYS,
    "model_master membership changed; update EXPECTED_MODEL_KEYS deliberately",
  );

  // The registry's own role vocabulary must still be the eleven roles the
  // per-model check below asserts against.
  assert.deepEqual(
    Object.keys(snapshot.source_role_families).sort(),
    EXPECTED_SOURCE_ROLES,
    "SOURCE_ROLE_FAMILIES drifted from the generation role contract",
  );

  for (const modelKey of EXPECTED_MODEL_KEYS) {
    const model = snapshot.models[modelKey];
    assert.ok(model, `${modelKey} missing model_master row`);
    assert.equal(model.active, true, `${modelKey} should be workbook-active`);
    assert.ok(model.registry_key, `${modelKey} missing registry_key`);
    assert.ok(model.model_label, `${modelKey} missing model_label`);

    assert.deepEqual(
      Object.keys(model.source_roles).sort(),
      EXPECTED_SOURCE_ROLES,
      `${modelKey} does not register every generation source role`,
    );

    // A registered sheet must actually exist, and must resolve to the family
    // its role declares. This is what catches a role pointed at a typo.
    for (const [role, sheetName] of Object.entries(model.source_roles)) {
      assert.ok(
        snapshot.sheetnames.includes(sheetName),
        `${modelKey}.${role} points at missing sheet ${sheetName}`,
      );
      assert.equal(
        snapshot.registered_sheet_families[sheetName],
        snapshot.source_role_families[role],
        `${modelKey}.${role} sheet ${sheetName} resolves to the wrong family`,
      );
    }
  }
});

test("model variant topology matches its declared count and active fact rows", () => {
  for (const modelKey of EXPECTED_MODEL_KEYS) {
    const model = snapshot.models[modelKey];

    assert.equal(
      model.variant_ids.length,
      model.expected_variant_count,
      `${modelKey} active model_variants rows disagree with expected_variant_count`,
    );

    // Display order must be a dense 1..N set; a gap or duplicate reorders or
    // collides in the customer-facing trim selector. Compared as a sorted set
    // because physical row order is not a contract — grand_sport_x stores its
    // rows body-style-interleaved while the others store them trim-major, and
    // both are valid.
    assert.deepEqual(
      [...model.variant_display_orders].sort((a, b) => a - b),
      model.variant_ids.map((_, index) => index + 1),
      `${modelKey} variant display_order is not a dense 1..N set`,
    );

    assert.deepEqual(
      model.variants_missing_active_fact,
      [],
      `${modelKey} references variant_master rows that are absent or inactive`,
    );
  }
});

test("registered sheets conform to their family's declared cell types", () => {
  // Guard the sweep itself: if the derivation stops finding typed columns,
  // an empty violation list would be meaningless.
  assert.ok(
    snapshot.typed_columns_checked >= 100,
    `expected the registry to declare types on 100+ populated columns, saw ${snapshot.typed_columns_checked}`,
  );

  // Known pre-existing drift, recorded rather than suppressed. These sheets
  // store text "True"/"10" where the registry declares bool/int. Generation
  // reads them through `workbook.clean()`, which stringifies everything, so
  // they are tolerated today — but they are real registry non-conformance and
  // the editor's own coercion path expects the declared type.
  //
  // Pinned exactly. A tenth violation, or drift in any currently-clean column,
  // fails this test. Fixing these requires a workbook write, which the
  // owning cleanup spec (§6) does not authorize.
  const KNOWN_TYPE_DRIFT = [
    "context_section_master.active",
    "context_section_master.is_required",
    "default_selection_rules.priority",
    "interior_components.active",
    "interior_components.display_order",
    "model_interior_scope.active",
    "model_master.model_year",
    "runtime_steps.active",
    "section_presentation.active",
  ];

  const found = snapshot.type_violations
    .map((violation) => `${violation.sheet}.${violation.column}`)
    .sort();
  assert.deepEqual(
    found,
    KNOWN_TYPE_DRIFT,
    "registry-declared cell types drifted; new entries are regressions, removed entries mean the pin is stale",
  );
});

test("no explicit excludes duplicates an active exclusive-group relationship", () => {
  // Two members of the same active exclusive group already exclude each other
  // through the group. An additional explicit `excludes` row is not redundant
  // decoration — `app.js` skips same-group peers when scanning rules that
  // TARGET a choice (`sameExclusiveGroupPeer`, disableReasonForChoice) but has
  // no such guard when scanning rules the choice is the SOURCE of, so the
  // duplicate blocks exactly one direction of a choose-one swap.
  //
  // Measured on the published registry: with T0F selected, clicking 5ZV does
  // nothing; delete the row and the same click swaps the aero choice.
  assert.deepEqual(
    snapshot.duplicate_group_excludes,
    [],
    "duplicate excludes rows shadow their exclusive group and break one direction of the group swap",
  );
});

test("active direct rules never both block and require or include the same target", () => {
  const conflicts = [];

  for (const [modelKey, entry] of Object.entries(liveRegistry().models)) {
    const typesByEdge = new Map();
    for (const rule of entry.data.rules.filter((row) => row.active === "True")) {
      const edge = [
        rule.source_id,
        rule.target_type,
        rule.target_id,
        rule.body_style_scope || "",
      ].join("::");
      if (!typesByEdge.has(edge)) typesByEdge.set(edge, new Set());
      typesByEdge.get(edge).add(rule.rule_type);
    }

    for (const [edge, types] of typesByEdge) {
      if (types.has("excludes") && (types.has("requires") || types.has("includes"))) {
        conflicts.push(`${modelKey}:${edge}:${[...types].sort().join(",")}`);
      }
    }
  }

  assert.deepEqual(
    conflicts,
    [],
    "a direct rule edge cannot simultaneously block and positively require the same target",
  );
});

test("active direct rules do not duplicate active grouped relationships", () => {
  const duplicates = [];

  for (const [modelKey, entry] of Object.entries(liveRegistry().models)) {
    const groupedEdges = new Map();
    for (const group of entry.data.ruleGroups.filter((row) => row.active === "True")) {
      // Direct rules have no trim- or variant-scope fields, so only an
      // unscoped group (with the same body-style scope) can duplicate one.
      if (group.trim_level_scope || group.variant_scope) continue;

      const directType = {
        excludes_any: "excludes",
        requires_any: "requires",
      }[group.group_type];
      if (!directType) continue;

      for (const targetId of group.target_ids) {
        const edge = [
          group.source_id,
          directType,
          targetId,
          group.body_style_scope || "",
        ].join("::");
        if (!groupedEdges.has(edge)) groupedEdges.set(edge, []);
        groupedEdges.get(edge).push(group.group_id);
      }
    }

    for (const rule of entry.data.rules.filter((row) => row.active === "True")) {
      const edge = [
        rule.source_id,
        rule.rule_type,
        rule.target_id,
        rule.body_style_scope || "",
      ].join("::");
      if (groupedEdges.has(edge)) {
        duplicates.push(
          `${modelKey}:${rule.rule_id}:${groupedEdges.get(edge).sort().join(",")}`,
        );
      }
    }
  }

  assert.deepEqual(
    duplicates,
    [],
    "a grouped relationship must not retain a competing direct-rule owner",
  );
});

test("retired lifecycle columns stay absent from every registered sheet", () => {
  // The retired gate checked two named rule sheets. This sweeps all 73
  // registered sheets, so a reintroduction anywhere is caught — including in
  // a model sheet that did not exist when those columns were removed.
  assert.deepEqual(
    snapshot.retired_column_sightings,
    [],
    "retired lifecycle/review columns reappeared in a registered sheet",
  );
});

test("interior source sheets shared across models keep identical headers", () => {
  const sheets = Object.keys(snapshot.interior_headers).sort();
  assert.ok(sheets.length >= 2, `expected multiple interior sheets, saw ${sheets.join(", ")}`);

  // Every interiors-role sheet must carry the same header set: models share
  // these by role, so a column present in one and missing from another is a
  // silent per-model data loss.
  const [reference, ...others] = sheets;
  for (const sheet of others) {
    assert.deepEqual(
      snapshot.interior_headers[sheet],
      snapshot.interior_headers[reference],
      `${sheet} headers diverged from ${reference}`,
    );
  }
});

test("replace excludes stay limited to true default-replacement rows", () => {
  // A `runtime_action=replace` row between two members of one exclusive group
  // is a hand-stacked closure row; generation-time derivation owns those
  // (rule_derivation.py). A legitimate replace row crosses group boundaries.
  const stacked = snapshot.replace_excludes.filter((rule) => rule.shared_groups.length > 0);
  assert.deepEqual(
    stacked,
    [],
    "replace rows between exclusive-group peers belong to rule_derivation.py, not the workbook",
  );

  // Guard the filter: if the sweep stops finding replace rows at all, the
  // emptiness above would prove nothing.
  assert.ok(
    snapshot.replace_excludes.length >= 10,
    `expected the workbook to author replace rows, saw ${snapshot.replace_excludes.length}`,
  );
});

test("approved one-source blocker clusters use excludes_any groups", () => {
  assert.deepEqual(
    snapshot.ungrouped_blocker_excludes,
    [],
    "blocker-cluster sources should author one excludes_any group, not direct excludes rows",
  );
});

test("retired sheets and draft provenance stay out of the source graph and published data", () => {
  for (const retired of ["category_master", "archive_category_master"]) {
    assert.equal(
      snapshot.sheetnames.includes(retired),
      false,
      `${retired} should stay extracted to archive/stingray_archive.xlsx`,
    );
  }

  // Draft-only provenance must never reach the browser payload.
  const DRAFT_ONLY_CHOICE_FIELDS = [
    "choice_mode",
    "selection_mode",
    "selection_mode_label",
    "source_description",
    "source_detail_raw",
    "source_option_name",
    "text_cleanup_notes",
  ];

  const registry = liveRegistry();
  const publishedModels = Object.keys(registry.models);
  assert.ok(publishedModels.length > 0, "published registry has no models");

  for (const [modelKey, entry] of Object.entries(registry.models)) {
    assert.equal("draftMetadata" in entry.data, false, `${modelKey} leaked draftMetadata`);

    for (const choice of entry.data.choices) {
      for (const field of DRAFT_ONLY_CHOICE_FIELDS) {
        assert.equal(
          field in choice,
          false,
          `${modelKey} ${choice.choice_id} leaked ${field}`,
        );
      }
    }
    for (const row of entry.data.standardEquipment) {
      assert.equal(
        "source_detail_raw" in row,
        false,
        `${modelKey} ${row.equipment_id} leaked source_detail_raw`,
      );
    }

    // The same names are legitimate section/group metadata. Asserting they
    // survive is what keeps the strip above from being widened into them.
    assert.ok(
      entry.data.sections.some((section) => section.selection_mode),
      `${modelKey} lost section selection_mode`,
    );
    assert.ok(
      entry.data.sections.some((section) => section.choice_mode),
      `${modelKey} lost section choice_mode`,
    );
    assert.ok(
      entry.data.sections.some((section) => section.selection_mode_label),
      `${modelKey} lost section selection_mode_label`,
    );
    assert.ok(
      entry.data.exclusiveGroups.some((group) => group.selection_mode),
      `${modelKey} lost group selection_mode`,
    );
  }
});

test("promotion artifact vocabulary stays narrowed to runtime_contract", () => {
  // Pass 3 requirement 7 removed `current_generation` and `draft_artifact`.
  // Pinned here because the snapshot reads the live registry tuple: widening
  // it again would silently re-open the publish-an-unvalidated-artifact path.
  assert.deepEqual(snapshot.promotion_artifact_types, ["runtime_contract"]);
});
