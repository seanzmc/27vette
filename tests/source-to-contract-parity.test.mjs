// Source-to-contract parity, for every workbook-promoted model.
//
// Spec `docs/superpowers/specs/2026-08-17-fast-layered-validation-suite.md`
// §4.2 and Checkpoint 2. A parity gate compares two independent paths:
//
//   expected: direct, simple read of authoritative workbook rows
//   actual:   generator -> runtime contract
//
// The expected side here is the §6.2 workbook-truth snapshot, built by
// `scripts/build_workbook_truth.py` from a read-only workbook handle, which
// imports no generation module (`tests/test_workbook_truth.py` asserts that
// boundary). The actual side is the promoted runtime contract each model's own
// `model_registry_promotion` row names.
//
// Nothing below is model-specific. The model list, its source sheets, its
// variants, and its contract path all come from the workbook, so promoting a
// seventh model widens this gate with no edit here — and every assertion states
// a relationship rather than a value, so a valid product change follows the
// workbook instead of failing a literal.
//
// Each relationship was measured against all six promoted models before it was
// written, and holds exactly in both directions. Where the workbook has a
// suppressor — an inactive row, an unresolvable reference, `display_behavior`
// hidden — the suppressor is named from workbook columns. What is deliberately
// NOT reimplemented here is generation: no status derivation, no rule
// derivation, no fallback, no cleanup. A rule this gate cannot state from
// workbook columns belongs to the candidate lane's own stages, not here.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import process from "node:process";
import test from "node:test";

import { cell, workbookRows, workbookTruth, workbookTruthy } from "./lib/workbook-truth.mjs";

const truth = workbookTruth();

// The candidate lane points this at its temporary root so the same gate proves
// the candidate contracts. Unset, it reads the promoted tracked artifacts.
const CONTRACT_ROOT = process.env.CORVETTE_CONTRACT_ROOT || ".";

// Interior sections are carried on the interior rows themselves and are not
// emitted as contract sections; the two context sections are synthesized by the
// contract rather than authored in section_master. Both are addressing facts
// about the contract shape, stated here so the section assertion below can be
// an equality rather than a containment.
const CONTEXT_SECTION_IDS = ["sec_context_body_style", "sec_context_trim_level"];

const promoted = truth.promotions.rows;
assert.ok(promoted.length > 0, "workbook promotes no model; parity would be vacuous");

function contractFor(promotion) {
  const path = resolve(CONTRACT_ROOT, promotion.artifact_path);
  return JSON.parse(readFileSync(path, "utf8"));
}

function sourceRows(modelKey, role) {
  const sheet = truth.models[modelKey].source_sheets[role];
  assert.ok(sheet, `${modelKey} registers no active ${role}`);
  return workbookRows(sheet);
}

/** Rows of a global sheet scoped to one model and active. */
function activeModelRows(sheetName, modelKey) {
  return workbookRows(sheetName).filter(
    (row) => row.model_key === modelKey && workbookTruthy(row.active),
  );
}

/**
 * An active variant override, where one exists, wins over the option row for
 * the three columns the writable `variant_overrides` contract lets it restate:
 * `selectable`, `display_behavior`, `section_id`. This is the override sheet's
 * own documented purpose, not a generation rule.
 */
function resolved(optionRow, overrideRow, column) {
  return cell(overrideRow?.[column]) || cell(optionRow?.[column]);
}

for (const promotion of promoted) {
  const modelKey = promotion.model_key;
  const model = truth.models[modelKey];
  const contract = contractFor(promotion);

  const activeVariantIds = new Set(model.variants.map((variant) => variant.variant_id));
  const emittedSectionIds = new Set(contract.sections.map((section) => section.section_id));
  const optionRows = new Map(sourceRows(modelKey, "source_option_sheet").map((row) => [row.option_id, row]));
  // Only active rows. `variant_overrides` carries an `active` column and
  // generation reads the sheet through `active_rows`, so a deactivated
  // override restates nothing. Indexing every row instead would make this gate
  // reject a correctly generated candidate the moment an author turns one off.
  const overrideRows = new Map(
    sourceRows(modelKey, "variant_option_overrides_sheet")
      .filter((row) => workbookTruthy(row.active))
      .map((row) => [`${row.option_id}::${row.variant_id}`, row]),
  );

  const choicePairs = new Map(
    contract.choices.map((choice) => [`${choice.option_id}::${choice.variant_id}`, choice]),
  );

  const masterSectionIds = new Set(workbookRows("section_master").map((row) => row.section_id));

  // Which source rows the workbook says may reach the contract, and the section
  // each one resolves to. Stated once, from workbook columns only: the option
  // row is active, the variant is an active member of this model, the resolved
  // section exists in section_master, and the resolved display_behavior is not
  // `hidden`. Both the reverse-direction membership check and the emitted
  // section set are the same question, so neither may answer it from the
  // contract it is checking.
  const emittable = [];
  for (const row of sourceRows(modelKey, "status_sheet")) {
    const optionRow = optionRows.get(row.option_id);
    if (!optionRow || !workbookTruthy(optionRow.active)) continue;
    if (!activeVariantIds.has(row.variant_id)) continue;
    const overrideRow = overrideRows.get(`${row.option_id}::${row.variant_id}`);
    const sectionId = resolved(optionRow, overrideRow, "section_id");
    if (!masterSectionIds.has(sectionId)) continue;
    if (resolved(optionRow, overrideRow, "display_behavior") === "hidden") continue;
    emittable.push({ key: `${row.option_id}::${row.variant_id}`, sectionId });
  }

  // ── Model topology ────────────────────────────────────────────────────────

  test(`${modelKey}: emitted variants equal the workbook's active variant facts`, () => {
    const expected = model.variants
      .map((variant) => variant.variant_id)
      .sort();
    assert.deepEqual(
      contract.variants.map((variant) => variant.variant_id).sort(),
      expected,
      "emitted variants drifted from model_variants joined to variant_master",
    );

    const factByVariantId = new Map(model.variants.map((variant) => [variant.variant_id, variant]));
    for (const variant of contract.variants) {
      const fact = factByVariantId.get(variant.variant_id);
      assert.equal(cell(variant.body_style), fact.body_style, `${variant.variant_id} body_style`);
      // The one documented representation rule on this collection: trim level
      // is a display token and `inspection.py:651` upper-cases it. Stated as
      // the transform rather than compared case-insensitively, so dropping the
      // upper-casing fails here instead of passing quietly.
      assert.equal(
        cell(variant.trim_level),
        fact.trim_level.toUpperCase(),
        `${variant.variant_id} trim_level`,
      );
      assert.equal(cell(variant.base_price), fact.base_price, `${variant.variant_id} base_price`);
      assert.equal(cell(variant.model_year), fact.model_year, `${variant.variant_id} model_year`);
    }
  });

  test(`${modelKey}: emitted steps equal the active runtime_steps rows`, () => {
    const expected = activeModelRows("runtime_steps", modelKey);
    assert.ok(expected.length > 0, `${modelKey} declares no active runtime step`);
    assert.deepEqual(
      contract.steps.map((step) => step.step_key).sort(),
      expected.map((row) => row.step_key).sort(),
    );
    const orderByStepKey = new Map(expected.map((row) => [row.step_key, row.runtime_order]));
    for (const step of contract.steps) {
      assert.equal(
        cell(step.runtime_order),
        orderByStepKey.get(step.step_key),
        `${step.step_key} runtime_order`,
      );
    }
  });

  test(`${modelKey}: emitted sections equal the sections its emittable rows resolve to`, () => {
    // A section is emitted because a choice landed in it, so expected
    // membership is the resolved section of every emittable row plus the two
    // synthesized context sections. A section_master row nothing resolves to is
    // not expected, and an override that names a section no emittable row uses
    // does not conjure one.
    const referenced = new Set(CONTEXT_SECTION_IDS);
    for (const row of emittable) referenced.add(row.sectionId);
    assert.deepEqual(
      [...emittedSectionIds].sort(),
      [...referenced].sort(),
      "emitted sections drifted from the sections this model's emittable source rows resolve to",
    );

    // Presentation is an overlay, not a membership list. An active row for a
    // section this model never emits is inert — and it is allowed to stay
    // inert, because deleting it is a workbook write this specification does
    // not authorize (§11). What is NOT allowed is an orphaned row that carries
    // real overlay intent: that is a section the workbook expects to present
    // and the contract does not have. Stated as a rule over the overlay
    // columns, so it needs no list of which sections are currently orphaned.
    const OVERLAY_COLUMNS = [
      "step_key",
      "display_label",
      "display_behavior",
      "standard_equipment_bucket",
      "standard_equipment_group_type",
      "auto_added_bucket",
    ];
    for (const row of activeModelRows("section_presentation", modelKey)) {
      if (emittedSectionIds.has(row.section_id)) continue;
      for (const column of OVERLAY_COLUMNS) {
        assert.equal(
          cell(row[column]),
          "",
          `${modelKey} presents ${row.section_id} via ${column} but never emits that section`,
        );
      }
    }
  });

  // ── Choices and standard equipment ────────────────────────────────────────

  test(`${modelKey}: every emitted choice traces to one active option and OVS row`, () => {
    for (const [key, choice] of choicePairs) {
      const optionRow = optionRows.get(choice.option_id);
      assert.ok(optionRow, `${choice.choice_id} has no row in the model's option sheet`);
      assert.ok(
        workbookTruthy(optionRow.active),
        `${choice.choice_id} traces to an inactive option row`,
      );
      assert.equal(
        activeVariantIds.has(choice.variant_id),
        true,
        `${choice.choice_id} names a variant the model does not declare active`,
      );
      assert.equal(choice.choice_id, `${choice.variant_id}__${choice.option_id}`, `${key} choice_id shape`);
      assert.equal(cell(choice.rpo), cell(optionRow.rpo), `${choice.choice_id} rpo`);
      assert.equal(cell(choice.label), cell(optionRow.option_name), `${choice.choice_id} label`);
      assert.equal(cell(choice.base_price), cell(optionRow.price) || "0", `${choice.choice_id} base_price`);
    }
  });

  test(`${modelKey}: every emittable OVS row reaches the contract`, () => {
    // The reverse direction, and the one that catches silent loss. A source row
    // is not emitted only when the workbook says so: the option row is
    // inactive, the variant is not an active member, the resolved section is
    // absent from section_master, or the resolved display_behavior is `hidden`.
    // Every suppressor is a workbook column; the emittable set never reads the
    // contract it is checking.
    const expected = emittable.map((row) => row.key);

    assert.ok(expected.length > 0, `${modelKey} resolved no OVS row into the contract`);
    assert.deepEqual(
      [...choicePairs.keys()].sort(),
      expected.sort(),
      "emitted choices drifted from the emittable rows of the model's OVS sheet",
    );

    // Membership alone would not notice a choice landing in the wrong section
    // while both sections stay populated by other rows, which is exactly what a
    // mis-resolved override looks like.
    for (const row of emittable) {
      assert.equal(
        cell(choicePairs.get(row.key).section_id),
        row.sectionId,
        `${row.key} resolved section`,
      );
    }
  });

  test(`${modelKey}: emitted choice status equals its authored status`, () => {
    // Restricted to rows whose resolved display_behavior is blank. A non-blank
    // behavior means the workbook asked generation to derive the status, and
    // deriving it here too would make this gate agree with the generator by
    // construction. Those rows are still covered by membership above.
    let compared = 0;
    for (const row of sourceRows(modelKey, "status_sheet")) {
      const key = `${row.option_id}::${row.variant_id}`;
      const choice = choicePairs.get(key);
      if (!choice) continue;
      const overrideRow = overrideRows.get(key);
      if (resolved(optionRows.get(row.option_id), overrideRow, "display_behavior") !== "") continue;
      compared += 1;
      assert.equal(
        cell(choice.status),
        cell(row.status).toLowerCase(),
        `${choice.choice_id} status`,
      );
    }
    assert.ok(compared > 0, `${modelKey} compared no authored status`);
  });

  // Contract-internal, not source parity: both sides of this comparison come
  // from the artifact under test, so a generator that mis-derives status and
  // copies it into both collections stays green here. Authored status is
  // covered above, on the rows where the workbook states it. What this catches
  // is the two collections disagreeing with each other.
  test(`${modelKey}: standardEquipment agrees with the choices marked standard`, () => {
    const expected = [...choicePairs.values()]
      .filter((choice) => choice.status === "standard")
      .map((choice) => `${choice.option_id}::${choice.variant_id}`)
      .sort();
    assert.ok(expected.length > 0, `${modelKey} emits no standard choice`);
    assert.deepEqual(
      contract.standardEquipment.map((item) => `${item.option_id}::${item.variant_id}`).sort(),
      expected,
      "standardEquipment drifted from the emitted choices marked standard",
    );
  });

  // ── Rules, groups, prices ─────────────────────────────────────────────────

  test(`${modelKey}: emitted rules equal the resolvable rule_mapping rows`, () => {
    // A rule row is emitted when both of its endpoints exist in the model's
    // emitted id space, and dropped when either does not. Derived rows are the
    // one addition, and they must be visibly derived rather than silently
    // indistinguishable from authored ones.
    const emittedIds = new Set([
      ...contract.choices.map((choice) => choice.option_id),
      ...contract.standardEquipment.map((item) => item.option_id),
      ...contract.interiors.map((interior) => interior.interior_id),
    ]);
    const sourceRuleRows = sourceRows(modelKey, "rule_mapping_sheet");
    const expected = sourceRuleRows
      .filter((row) => emittedIds.has(row.source_id) && emittedIds.has(row.target_id))
      .map((row) => row.rule_id)
      .sort();
    const authoredIds = new Set(sourceRuleRows.map((row) => row.rule_id));
    const emitted = contract.rules.map((rule) => rule.rule_id);

    assert.ok(expected.length > 0, `${modelKey} resolved no rule row into the contract`);
    assert.deepEqual(
      emitted.filter((ruleId) => authoredIds.has(ruleId)).sort(),
      expected,
      "emitted authored rules drifted from the resolvable rows of the model's rule_mapping sheet",
    );
    for (const ruleId of emitted.filter((id) => !authoredIds.has(id))) {
      assert.match(ruleId, /^derived_/, `${ruleId} is neither authored nor marked derived`);
    }

    const byRuleId = new Map(sourceRuleRows.map((row) => [row.rule_id, row]));
    for (const rule of contract.rules) {
      const row = byRuleId.get(rule.rule_id);
      if (!row) continue;
      assert.equal(cell(rule.rule_type), cell(row.rule_type), `${rule.rule_id} rule_type`);
      assert.equal(cell(rule.source_id), cell(row.source_id), `${rule.rule_id} source_id`);
      assert.equal(cell(rule.target_id), cell(row.target_id), `${rule.rule_id} target_id`);
    }
  });

  test(`${modelKey}: emitted rule groups equal the active rule_groups rows`, () => {
    const expected = sourceRows(modelKey, "rule_groups_sheet").filter((row) => workbookTruthy(row.active));
    assert.ok(expected.length > 0, `${modelKey} declares no active rule group`);
    assert.deepEqual(
      contract.ruleGroups.map((group) => group.group_id).sort(),
      expected.map((row) => row.group_id).sort(),
    );

    const memberRows = sourceRows(modelKey, "rule_group_members_sheet").filter(
      (row) => workbookTruthy(row.active),
    );
    const sourceByGroup = new Map(expected.map((row) => [row.group_id, row]));
    const membersByGroup = new Map();
    for (const row of memberRows) {
      if (!membersByGroup.has(row.group_id)) membersByGroup.set(row.group_id, []);
      membersByGroup.get(row.group_id).push(row.target_id);
    }
    for (const group of contract.ruleGroups) {
      assert.equal(
        cell(group.display_label),
        cell(sourceByGroup.get(group.group_id)?.display_label),
        `${group.group_id} display_label`,
      );
      assert.deepEqual(
        [...group.target_ids].sort(),
        (membersByGroup.get(group.group_id) ?? []).sort(),
        `${group.group_id} members`,
      );
    }
  });

  test(`${modelKey}: emitted exclusive groups equal the active exclusive rows`, () => {
    const expected = sourceRows(modelKey, "exclusive_groups_sheet").filter((row) => workbookTruthy(row.active));
    assert.ok(expected.length > 0, `${modelKey} declares no active exclusive group`);
    assert.deepEqual(
      contract.exclusiveGroups.map((group) => group.group_id).sort(),
      expected.map((row) => row.group_id).sort(),
    );

    const memberRows = sourceRows(modelKey, "exclusive_group_members_sheet").filter(
      (row) => workbookTruthy(row.active),
    );
    const sourceByGroup = new Map(expected.map((row) => [row.group_id, row]));
    const membersByGroup = new Map();
    for (const row of memberRows) {
      if (!membersByGroup.has(row.group_id)) membersByGroup.set(row.group_id, []);
      membersByGroup.get(row.group_id).push(row.option_id);
    }
    for (const group of contract.exclusiveGroups) {
      assert.equal(
        cell(group.display_label),
        cell(sourceByGroup.get(group.group_id)?.display_label),
        `${group.group_id} display_label`,
      );
      assert.deepEqual(
        [...group.option_ids].sort(),
        (membersByGroup.get(group.group_id) ?? []).sort(),
        `${group.group_id} members`,
      );
    }
  });

  test(`${modelKey}: emitted price rules equal their source rows`, () => {
    const expected = sourceRows(modelKey, "price_rules_sheet");
    assert.ok(expected.length > 0, `${modelKey} declares no price rule`);
    assert.deepEqual(
      contract.priceRules.map((rule) => rule.price_rule_id).sort(),
      expected.map((row) => row.price_rule_id).sort(),
    );
    const byId = new Map(expected.map((row) => [row.price_rule_id, row]));
    for (const rule of contract.priceRules) {
      const row = byId.get(rule.price_rule_id);
      assert.equal(cell(rule.target_option_id), cell(row.target_option_id), `${rule.price_rule_id} target`);
      assert.equal(
        cell(rule.condition_option_id),
        cell(row.condition_option_id),
        `${rule.price_rule_id} condition`,
      );
      assert.equal(cell(rule.price_value), cell(row.price_value), `${rule.price_rule_id} price_value`);
    }
  });

  test(`${modelKey}: emitted default selection rules equal the active source rows`, () => {
    const expected = activeModelRows("default_selection_rules", modelKey);
    assert.ok(expected.length > 0, `${modelKey} declares no active default selection rule`);
    assert.deepEqual(
      contract.defaultSelectionRules.map((rule) => rule.rule_id).sort(),
      expected.map((row) => row.rule_id).sort(),
    );
    const byId = new Map(expected.map((row) => [row.rule_id, row]));
    for (const rule of contract.defaultSelectionRules) {
      const row = byId.get(rule.rule_id);
      assert.equal(cell(rule.target_option_id), cell(row.target_option_id), `${rule.rule_id} target`);
      assert.equal(cell(rule.condition_type), cell(row.condition_type), `${rule.rule_id} condition_type`);
      assert.equal(cell(rule.condition_id), cell(row.condition_id), `${rule.rule_id} condition_id`);
    }
  });

  // ── Interiors and colour overrides ────────────────────────────────────────

  test(`${modelKey}: emitted interiors equal the model's active interior scope`, () => {
    const expected = model.interior_scope.map((entry) => entry.interior_id);
    assert.ok(expected.length > 0, `${modelKey} scopes no interior`);
    assert.deepEqual(
      contract.interiors.map((interior) => interior.interior_id).sort(),
      [...new Set(expected)].sort(),
      "emitted interiors drifted from the active model_interior_scope rows",
    );

    const sourceIds = new Set(sourceRows(modelKey, "interior_source_sheet").map((row) => row.interior_id));
    for (const interior of contract.interiors) {
      assert.equal(
        sourceIds.has(interior.interior_id),
        true,
        `${interior.interior_id} is scoped but absent from the model's interior source sheet`,
      );
    }
  });

  test(`${modelKey}: emitted colour overrides equal their resolvable source rows`, () => {
    // The documented normalization: a shared-sheet row whose interior, option,
    // or added RPO is outside this model's emitted scope is not emitted.
    const interiorIds = new Set(contract.interiors.map((interior) => interior.interior_id));
    const optionIds = new Set(contract.choices.map((choice) => choice.option_id));
    const identity = (row) =>
      [row.interior_id, row.option_id, cell(row.rule_type).toLowerCase(), row.adds_rpo].join("::");

    const expected = sourceRows(modelKey, "color_overrides_sheet")
      .filter(
        (row) =>
          interiorIds.has(row.interior_id) &&
          optionIds.has(row.option_id) &&
          optionIds.has(row.adds_rpo),
      )
      .map(identity)
      .sort();
    assert.ok(expected.length > 0, `${modelKey} resolved no colour-override row into the contract`);
    assert.deepEqual(
      contract.colorOverrides.map(identity).sort(),
      expected,
      "emitted colorOverrides drifted from the resolvable rows of the model's colour-override sheet",
    );

    const overrideIds = contract.colorOverrides.map((override) => override.override_id);
    assert.equal(new Set(overrideIds).size, overrideIds.length, "override_id is not unique");
  });

  // ── Order summary ─────────────────────────────────────────────────────────

  test(`${modelKey}: emitted order summary equals its active source rows`, () => {
    const sections = activeModelRows("order_summary_sections", modelKey);
    assert.ok(sections.length > 0, `${modelKey} declares no order summary section`);
    assert.deepEqual(
      contract.orderSummary.sections.map((section) => section.section_key),
      sections
        .slice()
        .sort((left, right) => Number(left.display_order) - Number(right.display_order))
        .map((row) => row.section_key),
      "orderSummary sections drifted from order_summary_sections",
    );

    const stepMapRows = activeModelRows("step_order_summary_map", modelKey);
    const expectedPairs = stepMapRows.map((row) => `${row.step_key}::${row.section_key}`).sort();
    const actualPairs = Object.entries(contract.orderSummary.stepMap)
      .flatMap(([stepKey, sectionKeys]) =>
        (Array.isArray(sectionKeys) ? sectionKeys : [sectionKeys]).map((key) => `${stepKey}::${key}`),
      )
      .sort();
    assert.deepEqual(actualPairs, expectedPairs, "orderSummary stepMap drifted from step_order_summary_map");
  });

  // ── Assets ────────────────────────────────────────────────────────────────

  test(`${modelKey}: every emitted option asset equals its applicable asset_map row`, () => {
    // Checkpoint 1 proved this for Grand Sport against a per-gate reader. The
    // snapshot resolves wildcard/exact precedence once, for every model, so the
    // sweep now covers all six instead of the one that happened to own a
    // literal URL.
    const IMAGE_FIELDS = [
      "image_url",
      "image_alt",
      "image_fit",
      "image_position",
      "hover_image_url",
      "hover_image_alt",
      "hover_image_position",
    ];
    assert.deepEqual(truth.assetConflicts, [], "asset_map has unadjudicable duplicate rows");
    assert.deepEqual(
      truth.topologyConflicts,
      [],
      "a promotion or variant key the topology indexes uniquely has duplicate rows",
    );

    const applicable = truth.assets[modelKey] ?? {};
    const optionIds = new Set(contract.choices.map((choice) => choice.option_id));
    const mapped = Object.keys(applicable)
      .filter((target) => target.startsWith("option::"))
      .map((target) => target.slice("option::".length))
      .filter((optionId) => optionIds.has(optionId));

    assert.ok(mapped.length > 0, `asset_map declares no active option asset reaching ${modelKey}`);
    assert.ok(
      optionIds.size > mapped.length,
      `expected at least one unmapped ${modelKey} option, to prove assets are not applied blanket`,
    );

    for (const choice of contract.choices) {
      const expected = applicable[`option::${choice.option_id}`];
      for (const field of IMAGE_FIELDS) {
        if (expected) {
          assert.equal(choice[field], expected[field], `${choice.choice_id} ${field}`);
        } else {
          assert.equal(
            Object.hasOwn(choice, field),
            false,
            `${choice.choice_id} carries ${field} with no applicable active asset_map row`,
          );
        }
      }
    }
  });

  // ── Dataset binding ───────────────────────────────────────────────────────

  test(`${modelKey}: the contract names the workbook and sheet it was built from`, () => {
    assert.equal(contract.dataset.source_workbook, truth.workbook.name);
    assert.equal(contract.dataset.source_sheet, model.source_sheets.source_option_sheet);
    assert.equal(cell(contract.dataset.model_year), model.model_year);
    assert.equal(contract.dataset.status, "runtime_active");
  });
}
