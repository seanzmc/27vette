// Runtime state matrix: generic §4.3 invariants over every promoted model
// and declared active variant.
//
// Spec `docs/superpowers/specs/2026-08-17-fast-layered-validation-suite.md`
// §4.3 and Checkpoint 3. Cases come from the workbook-truth snapshot, not
// from the payload under test — a registry that dropped a variant must fail
// membership, not silently shrink the sweep.
//
// The candidate lane points the harness at a temporary registry through
// CORVETTE_FORM_DATA_JS. This module does not read the workbook generator.
import assert from "node:assert/strict";

import { workbookTruth } from "./workbook-truth.mjs";
import { loadDataWindow, loadRuntime } from "./runtime-harness.mjs";

export const INVARIANTS = [
  "model_activation",
  "variant_resolution",
  "reset_fixed_point",
  "reconcile_idempotent",
  "selected_options_exist",
  "selected_not_disabled",
  "exclusive_single_selection",
  "required_satisfied_or_reported",
  "rule_contracts",
  "order_totals",
  "model_switch_clears_prior",
  "payload_identity",
];

export function promotedMatrixCases(options = {}) {
  const truth = workbookTruth(options);
  const cases = [];
  for (const promotion of truth.promotions.rows) {
    const model = truth.models[promotion.model_key];
    assert.ok(model, `${promotion.model_key} is promoted but absent from the snapshot`);
    assert.ok(model.registry_key, `${promotion.model_key} has no registry_key`);
    assert.ok(model.variants.length > 0, `${promotion.model_key} declares no active variant`);
    for (const variant of model.variants) {
      cases.push({
        modelKey: model.model_key,
        registryKey: model.registry_key,
        exportSlug: model.export_slug,
        modelLabel: model.model_label,
        modelYear: String(model.model_year || ""),
        variantId: variant.variant_id,
        bodyStyle: variant.body_style,
        trimLevel: String(variant.trim_level || "").toUpperCase(),
        basePrice: Number(variant.base_price || 0),
      });
    }
  }
  assert.ok(cases.length > 0, "workbook promotes no model/variant; the matrix would be vacuous");
  return cases;
}

export function casesByRegistryKey(options = {}) {
  const grouped = new Map();
  for (const matrixCase of promotedMatrixCases(options)) {
    if (!grouped.has(matrixCase.registryKey)) grouped.set(matrixCase.registryKey, []);
    grouped.get(matrixCase.registryKey).push(matrixCase);
  }
  return grouped;
}

export function snapshotState(runtime) {
  const autoAdded = runtime.computeAutoAdded();
  return {
    selected: [...runtime.state.selected].sort(),
    userSelected: [...runtime.state.userSelected].sort(),
    selectedInterior: runtime.state.selectedInterior || "",
    bodyStyle: runtime.state.bodyStyle,
    trimLevel: runtime.state.trimLevel,
    autoAdded: [...autoAdded.keys()].sort(),
    missingRequired: [...runtime.missingRequired()].sort(),
  };
}

export function activateVariant(runtime, matrixCase) {
  if (runtime.activeModelKey !== matrixCase.registryKey) {
    runtime.activateModel(matrixCase.registryKey);
  }
  runtime.state.bodyStyle = matrixCase.bodyStyle;
  runtime.state.trimLevel = matrixCase.trimLevel;
  runtime.resetDefaults();
  runtime.reconcileSelections();
}

function currentVariant(runtime) {
  return runtime.variants.find(
    (variant) => variant.body_style === runtime.state.bodyStyle && variant.trim_level === runtime.state.trimLevel,
  );
}

function lockedOrIncluded(runtime, optionId) {
  const choice = runtime.activeChoiceRows().find((row) => row.option_id === optionId);
  if (!choice) return false;
  if (runtime.computeAutoAdded().has(optionId)) return true;
  if (choice.display_behavior === "display_only" || choice.display_behavior === "auto_only") return true;
  if (choice.selectable !== "True") return true;
  return false;
}

function singleSelectGroups(runtime) {
  return (runtime.data.exclusiveGroups || []).filter((group) => {
    if (group.active && group.active !== "True") return false;
    return ["single_within_group", "required_single_within_group"].includes(group.selection_mode);
  });
}

function modelDataFingerprint(data) {
  return JSON.stringify({
    source_sheet: data?.dataset?.source_sheet || "",
    name: data?.dataset?.name || "",
    variants: (data?.variants || []).map((variant) => variant.variant_id).sort(),
  });
}

export function assertModelActivation(runtime, matrixCase, registry) {
  assert.equal(runtime.activeModelKey, matrixCase.registryKey, `${matrixCase.registryKey} should be the active model`);
  const published = registry.models[matrixCase.registryKey];
  assert.ok(published, `${matrixCase.registryKey} is missing from the registry under test`);
  // The harness and the catalog load the registry in separate VMs, so object
  // identity is not a contract. The bound dataset must still be that model's.
  assert.equal(
    modelDataFingerprint(runtime.data),
    modelDataFingerprint(published.data),
    `${matrixCase.registryKey} should bind only that model's registry data`,
  );
  const allowed = new Set((published.data.variants || []).map((variant) => variant.variant_id));
  for (const choice of runtime.activeChoiceRows()) {
    assert.ok(
      allowed.has(choice.variant_id),
      `${matrixCase.registryKey} active choice ${choice.option_id} belongs to ${choice.variant_id}, which is not this model's variant`,
    );
  }
}

export function assertVariantResolution(runtime, matrixCase) {
  const variant = currentVariant(runtime);
  assert.ok(variant, `${matrixCase.registryKey} ${matrixCase.bodyStyle}/${matrixCase.trimLevel} did not resolve to a variant`);
  assert.equal(variant.variant_id, matrixCase.variantId, `${matrixCase.registryKey} resolved the wrong variant`);
  assert.equal(variant.body_style, matrixCase.bodyStyle, `${matrixCase.registryKey} ${matrixCase.variantId} body_style`);
  assert.equal(variant.trim_level, matrixCase.trimLevel, `${matrixCase.registryKey} ${matrixCase.variantId} trim_level`);
  assert.equal(
    runtime.activeChoiceRows().every((choice) => choice.variant_id === matrixCase.variantId),
    true,
    `${matrixCase.registryKey} ${matrixCase.variantId} still has choices from another variant`,
  );
}

export function assertResetFixedPoint(runtime) {
  const first = snapshotState(runtime);
  runtime.reconcileSelections();
  assert.deepEqual(snapshotState(runtime), first, "reset plus reconciliation is not a stable fixed point");
}

export function assertReconcileIdempotent(runtime) {
  const first = snapshotState(runtime);
  runtime.reconcileSelections();
  runtime.reconcileSelections();
  assert.deepEqual(snapshotState(runtime), first, "a second reconciliation is not idempotent");
}

export function assertSelectedOptionsExist(runtime) {
  const rows = new Map(runtime.activeChoiceRows().map((choice) => [choice.option_id, choice]));
  const autoAdded = runtime.computeAutoAdded();
  const ids = new Set([...runtime.state.selected, ...autoAdded.keys()]);
  for (const optionId of ids) {
    const choice = rows.get(optionId);
    assert.ok(choice, `selected/auto-added ${optionId} does not exist on the current variant`);
    assert.equal(choice.active, "True", `${optionId} is selected but inactive`);
    assert.notEqual(choice.status, "unavailable", `${optionId} is selected but unavailable`);
    assert.notEqual(choice.display_behavior, "hidden", `${optionId} is selected but hidden`);
  }
  if (runtime.state.selectedInterior) {
    const interior = runtime.data.interiors.find((row) => row.interior_id === runtime.state.selectedInterior);
    assert.ok(interior, `selected interior ${runtime.state.selectedInterior} is not in this model`);
    assert.equal(interior.trim_level, runtime.state.trimLevel, `selected interior ${interior.interior_id} is the wrong trim`);
  }
}

export function assertSelectedNotDisabled(runtime) {
  for (const optionId of runtime.state.selected) {
    const choice = runtime.activeChoiceRows().find((row) => row.option_id === optionId);
    if (!choice) continue;
    if (lockedOrIncluded(runtime, optionId)) continue;
    const reason = runtime.disableReasonForChoice(choice, { includeSelectedRequirements: false });
    assert.equal(reason, "", `selected ${optionId} remains disabled: ${reason}`);
  }
}

export function assertExclusiveSingleSelection(runtime) {
  const selected = new Set([...runtime.state.selected, ...runtime.computeAutoAdded().keys()]);
  for (const group of singleSelectGroups(runtime)) {
    const picked = (group.option_ids || []).filter((optionId) => selected.has(optionId));
    assert.ok(
      picked.length <= 1,
      `${group.group_id} has ${picked.length} selected peers: ${picked.join(", ")}`,
    );
  }
}

export function assertRequiredSatisfiedOrReported(runtime) {
  const missing = new Set(runtime.missingRequired());
  const selected = new Set([...runtime.state.selected, ...runtime.computeAutoAdded().keys()]);
  const rows = runtime.activeChoiceRows();

  const requiredSections = new Map();
  for (const choice of rows) {
    const section = (runtime.data.sections || []).find((row) => row.section_id === choice.section_id);
    if (!section || section.selection_mode !== "single_select_req") continue;
    if (choice.step_key === "base_interior") continue;
    if (choice.active !== "True" || choice.status === "unavailable" || choice.display_behavior === "hidden") continue;
    if (!requiredSections.has(section.section_id)) requiredSections.set(section.section_id, section);
  }
  for (const section of requiredSections.values()) {
    const satisfied = rows.some(
      (choice) => choice.section_id === section.section_id && selected.has(choice.option_id),
    );
    assert.ok(
      satisfied || missing.has(section.section_name),
      `required section ${section.section_id} (${section.section_name}) is unsatisfied and unreported`,
    );
  }

  for (const group of singleSelectGroups(runtime)) {
    if (group.selection_mode !== "required_single_within_group") continue;
    const visible = (group.option_ids || []).some((optionId) =>
      rows.some((choice) => choice.option_id === optionId && choice.active === "True" && choice.status !== "unavailable"),
    );
    if (!visible) continue;
    const satisfied = (group.option_ids || []).some((optionId) => selected.has(optionId));
    const section = (runtime.data.sections || []).find((row) => {
      const choice = rows.find((item) => item.option_id === (group.option_ids || [])[0]);
      return choice && row.section_id === choice.section_id;
    });
    const label = section?.section_name || group.group_id;
    assert.ok(satisfied || missing.has(label), `required exclusive group ${group.group_id} is unsatisfied and unreported`);
  }

  if (!runtime.state.selectedInterior) {
    assert.ok(missing.has("Interior Color"), "missing interior is not reported");
  }
}

export function assertOrderTotals(runtime) {
  const order = runtime.currentOrder();
  const selectedTotal = order.selected_options.reduce((sum, item) => sum + Number(item.price || 0), 0);
  const autoTotal = order.auto_added_options.reduce((sum, item) => sum + Number(item.price || 0), 0);
  const interiorTotal = Number(order.selected_interior?.price || 0);
  const componentTotal = (order.interior_components || []).reduce((sum, item) => sum + Number(item.price || 0), 0);
  assert.equal(
    order.pricing.selected_options_total,
    selectedTotal + autoTotal + interiorTotal + componentTotal,
    "selected_options_total does not equal the exposed option/component/interior lines",
  );
  assert.equal(
    order.pricing.total_msrp,
    Number(order.pricing.base_price || 0) + Number(order.pricing.selected_options_total || 0),
    "total_msrp does not equal base plus option lines",
  );
  const variant = currentVariant(runtime);
  assert.equal(Number(order.pricing.base_price || 0), Number(variant?.base_price || 0), "order base_price drifted from the variant");
}

export function assertPayloadIdentity(runtime, matrixCase) {
  const order = runtime.currentOrder();
  const compact = runtime.compactOrder();
  const payload = runtime.dealerSubmissionPayload(compact);
  assert.equal(payload.model, matrixCase.registryKey, "dealer payload model key");
  assert.equal(order.vehicle.variant_id, matrixCase.variantId, "order variant_id");
  assert.equal(order.vehicle.body_style, matrixCase.bodyStyle, "order body_style");
  assert.equal(order.vehicle.trim_level, matrixCase.trimLevel, "order trim_level");
  assert.equal(compact.vehicle.body_style, matrixCase.bodyStyle, "compact body_style");
  assert.equal(compact.vehicle.trim_level, matrixCase.trimLevel, "compact trim_level");
  assert.equal(compact.title, `${order.vehicle.model_year} ${order.vehicle.model}`, "compact title");
  assert.match(compact.vehicle.display_name, new RegExp(matrixCase.trimLevel), "compact display_name trim");
  assert.equal(payload.vehicle.display_name, compact.vehicle.display_name, "payload display_name");
  assert.equal(typeof payload.msrp, "string", "dealer payload msrp is formatted");
  assert.match(payload.msrp, /^\$/);
  assert.equal(payload.vehicle.base_price, compact.vehicle.base_price);
  if (runtime.missingRequired().length === 0) {
    runtime.downloadBuild();
    const download = runtime.downloads.at(-1);
    assert.ok(download, `${matrixCase.registryKey} ${matrixCase.variantId} produced no download`);
    assert.equal(download.filename, `${matrixCase.exportSlug}-build.md`);
    assert.match(download.content, new RegExp(`^# ${order.vehicle.model_year} ${order.vehicle.model}`));
    assert.match(download.content, new RegExp(matrixCase.trimLevel));
  }
}

export function assertRestState(runtime, matrixCase, registry) {
  assertModelActivation(runtime, matrixCase, registry);
  assertVariantResolution(runtime, matrixCase);
  assertResetFixedPoint(runtime);
  assertReconcileIdempotent(runtime);
  assertSelectedOptionsExist(runtime);
  assertSelectedNotDisabled(runtime);
  assertExclusiveSingleSelection(runtime);
  assertRequiredSatisfiedOrReported(runtime);
  assertDefaultRuleContract(runtime);
  assertOrderTotals(runtime);
  assertPayloadIdentity(runtime, matrixCase);
}

export function assertDefaultRuleContract(runtime) {
  const autoAdded = runtime.computeAutoAdded();
  for (const choice of runtime.activeChoiceRows()) {
    if (choice.display_behavior !== "default_selected") continue;
    if (choice.active !== "True" || choice.status === "unavailable" || choice.selectable !== "True") continue;
    if (runtime.disableReasonForChoice(choice, { includeSelectedRequirements: false })) continue;
    const group = (runtime.data.exclusiveGroups || []).find((row) => (row.option_ids || []).includes(choice.option_id));
    if (group && ["single_within_group", "required_single_within_group"].includes(group.selection_mode)) {
      const picked = (group.option_ids || []).some(
        (optionId) => runtime.state.selected.has(optionId) || autoAdded.has(optionId),
      );
      assert.ok(picked, `default-selected ${choice.option_id} left its exclusive group empty`);
      continue;
    }
    const section = (runtime.data.sections || []).find((row) => row.section_id === choice.section_id);
    if (section?.choice_mode === "single") {
      const sectionHasSelection = runtime.activeChoiceRows().some(
        (row) =>
          row.section_id === choice.section_id &&
          (runtime.state.selected.has(row.option_id) || autoAdded.has(row.option_id)),
      );
      if (sectionHasSelection) continue;
    }
    assert.ok(
      runtime.state.selected.has(choice.option_id) || autoAdded.has(choice.option_id),
      `default-selected ${choice.option_id} is neither selected nor auto-added`,
    );
  }
}

function visibleSelectable(runtime, optionId) {
  const choice = runtime.activeChoiceRows().find((row) => row.option_id === optionId);
  if (!choice) return null;
  if (choice.active !== "True" || choice.status === "unavailable" || choice.display_behavior === "hidden") return null;
  if (choice.selectable !== "True") return null;
  if (runtime.disableReasonForChoice(choice)) return null;
  return choice;
}

export function representativeTransitions(runtime) {
  const transitions = [];
  const rules = runtime.data.rules || [];
  const selected = () => new Set([...runtime.state.selected, ...runtime.computeAutoAdded().keys()]);

  const includeRule = rules.find((rule) => {
    if (rule.rule_type !== "includes" || (rule.active && rule.active !== "True")) return false;
    const source = visibleSelectable(runtime, rule.source_id);
    return Boolean(source) && !selected().has(rule.source_id);
  });
  if (includeRule) {
    const source = visibleSelectable(runtime, includeRule.source_id);
    runtime.handleChoice(source);
    assert.ok(
      runtime.computeAutoAdded().has(includeRule.target_id) || runtime.state.selected.has(includeRule.target_id),
      `includes ${includeRule.rule_id} did not add ${includeRule.target_id}`,
    );
    transitions.push(`includes:${includeRule.rule_id}`);
  }

  const excludeRule = rules.find((rule) => {
    if (rule.rule_type !== "excludes" || (rule.active && rule.active !== "True")) return false;
    if (rule.runtime_action === "replace") return false;
    const source = visibleSelectable(runtime, rule.source_id);
    return Boolean(source) && !selected().has(rule.source_id);
  });
  if (excludeRule) {
    const source = visibleSelectable(runtime, excludeRule.source_id);
    runtime.handleChoice(source);
    assert.equal(
      runtime.state.selected.has(excludeRule.target_id),
      false,
      `excludes ${excludeRule.rule_id} left ${excludeRule.target_id} selected`,
    );
    const target = runtime.activeChoiceRows().find((row) => row.option_id === excludeRule.target_id);
    if (target && target.selectable === "True" && target.status !== "unavailable") {
      assert.ok(runtime.disableReasonForChoice(target), `excludes ${excludeRule.rule_id} did not disable ${excludeRule.target_id}`);
    }
    transitions.push(`excludes:${excludeRule.rule_id}`);
  }

  const replaceRule = rules.find((rule) => {
    if (rule.runtime_action !== "replace" || (rule.active && rule.active !== "True")) return false;
    const source = visibleSelectable(runtime, rule.source_id);
    return Boolean(source) && !selected().has(rule.source_id);
  });
  if (replaceRule) {
    const target = visibleSelectable(runtime, replaceRule.target_id);
    if (target) runtime.handleChoice(target);
    const source = visibleSelectable(runtime, replaceRule.source_id);
    if (source) {
      runtime.handleChoice(source);
      assert.equal(
        runtime.state.selected.has(replaceRule.target_id),
        false,
        `replace ${replaceRule.rule_id} left ${replaceRule.target_id} selected`,
      );
      transitions.push(`replace:${replaceRule.rule_id}`);
    }
  }

  const requireRule = rules.find((rule) => {
    if (rule.rule_type !== "requires" || (rule.active && rule.active !== "True")) return false;
    const source = runtime.activeChoiceRows().find((row) => row.option_id === rule.source_id);
    const requirement = visibleSelectable(runtime, rule.target_id);
    return source && source.selectable === "True" && requirement && !selected().has(rule.target_id);
  });
  if (requireRule) {
    const blocked = runtime.activeChoiceRows().find((row) => row.option_id === requireRule.source_id);
    assert.ok(runtime.disableReasonForChoice(blocked), `requires ${requireRule.rule_id} did not disable ${requireRule.source_id}`);
    runtime.handleChoice(blocked);
    assert.equal(
      runtime.state.selected.has(requireRule.source_id),
      false,
      `requires ${requireRule.rule_id} allowed ${requireRule.source_id} without ${requireRule.target_id}`,
    );
    transitions.push(`requires:${requireRule.rule_id}`);
  }

  runtime.resetDefaults();
  runtime.reconcileSelections();
  const group = singleSelectGroups(runtime).find((row) => {
    const peers = (row.option_ids || []).map((optionId) => visibleSelectable(runtime, optionId)).filter(Boolean);
    return peers.length >= 2;
  });
  if (group) {
    const peers = (group.option_ids || []).map((optionId) => visibleSelectable(runtime, optionId)).filter(Boolean);
    const current = peers.find((choice) => runtime.state.selected.has(choice.option_id)) || peers[0];
    const other = peers.find((choice) => choice.option_id !== current.option_id);
    runtime.handleChoice(other);
    const selectedNow = new Set([...runtime.state.selected, ...runtime.computeAutoAdded().keys()]);
    const picked = (group.option_ids || []).filter((optionId) => selectedNow.has(optionId));
    assert.deepEqual(
      JSON.parse(JSON.stringify(picked)),
      [other.option_id],
      `${group.group_id} did not swap to a single peer`,
    );
    transitions.push(`exclusive:${group.group_id}`);
  }

  const priced = runtime.activeChoiceRows().find((choice) => {
    if (!visibleSelectable(runtime, choice.option_id)) return false;
    if (runtime.state.selected.has(choice.option_id)) return false;
    return Number(choice.base_price || 0) > 0;
  });
  if (priced) {
    runtime.handleChoice(priced);
    const line = runtime.currentOrder().selected_options.find((item) => item.id === priced.option_id);
    assert.ok(line, `priced ${priced.option_id} did not appear on the order`);
    assert.equal(Number(line.price), Number(runtime.optionPrice(priced.option_id)), `priced ${priced.option_id} line disagrees with optionPrice`);
    transitions.push(`price:${priced.option_id}`);
  }

  return transitions;
}

export function assertModelSwitchClearsPrior(runtime, fromCase, toCase, registry) {
  activateVariant(runtime, fromCase);
  const prior = runtime.activeChoiceRows().find((choice) => {
    if (choice.active !== "True" || choice.selectable !== "True" || choice.status === "unavailable") return false;
    if (runtime.state.selected.has(choice.option_id) || runtime.computeAutoAdded().has(choice.option_id)) return false;
    return !runtime.disableReasonForChoice(choice);
  });
  assert.ok(prior, `${fromCase.registryKey} has no non-default option to carry across a switch`);
  runtime.handleChoice(prior);
  runtime.state.selectedInterior = runtime.data.interiors?.[0]?.interior_id || runtime.state.selectedInterior;
  assert.equal(runtime.state.userSelected.has(prior.option_id), true, `${prior.option_id} should be a user pick before the switch`);

  runtime.activateModel(toCase.registryKey);
  assert.equal(runtime.activeModelKey, toCase.registryKey);
  assert.equal(
    modelDataFingerprint(runtime.data),
    modelDataFingerprint(registry.models[toCase.registryKey].data),
    `${toCase.registryKey} should bind only that model's registry data after the switch`,
  );
  assert.equal(runtime.state.userSelected.size, 0, "userSelected survived a model switch");
  assert.equal(runtime.state.selectedInterior, "", "selectedInterior survived a model switch");
  assert.equal(
    runtime.state.userSelected.has(prior.option_id),
    false,
    `${prior.option_id} from ${fromCase.registryKey} remained a user pick on ${toCase.registryKey}`,
  );
}

export function loadMatrixRuntime() {
  return {
    registry: loadDataWindow().CORVETTE_FORM_DATA,
    runtime: loadRuntime(),
  };
}

export function matrixReport(cases, seen) {
  return {
    promoted_models: [...new Set(cases.map((matrixCase) => matrixCase.modelKey))],
    registry_keys: [...new Set(cases.map((matrixCase) => matrixCase.registryKey))],
    variants: [...new Set(cases.map((matrixCase) => `${matrixCase.registryKey}:${matrixCase.variantId}`))].sort(),
    seen: [...seen].sort(),
    invariants: INVARIANTS,
  };
}
