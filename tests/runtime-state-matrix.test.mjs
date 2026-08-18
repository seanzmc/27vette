// Generated runtime state matrix — Checkpoint 3.
//
// Spec `docs/superpowers/specs/2026-08-17-fast-layered-validation-suite.md`
// §4.3. Cases are discovered from the workbook-truth snapshot. The runtime
// under test is the published registry, or a candidate registry through
// CORVETTE_FORM_DATA_JS. No live dealer request is made.
import assert from "node:assert/strict";
import test from "node:test";

import { loadDataWindow } from "./lib/runtime-harness.mjs";
import {
  INVARIANTS,
  activateVariant,
  assertDefaultRuleContract,
  assertExclusiveSingleSelection,
  assertModelActivation,
  assertModelSwitchClearsPrior,
  assertOrderTotals,
  assertPayloadIdentity,
  assertReconcileIdempotent,
  assertRequiredSatisfiedOrReported,
  assertResetFixedPoint,
  assertRestState,
  assertSelectedNotDisabled,
  assertSelectedOptionsExist,
  assertVariantResolution,
  casesByRegistryKey,
  loadMatrixRuntime,
  matrixReport,
  promotedMatrixCases,
  representativeTransitions,
} from "./lib/runtime-state-matrix.mjs";

const cases = promotedMatrixCases();
const byModel = casesByRegistryKey();
const registry = loadDataWindow().CORVETTE_FORM_DATA;
const seen = new Set();

test("the matrix enumerates every promoted model and declared active variant", () => {
  assert.ok(cases.length > 0, "no matrix cases");
  const reported = matrixReport(cases, seen);
  assert.deepEqual(
    reported.promoted_models,
    [...new Set(cases.map((matrixCase) => matrixCase.modelKey))],
  );
  assert.equal(reported.invariants.length, 12);
  assert.deepEqual(reported.invariants, INVARIANTS);

  const publishedKeys = Object.keys(registry.models);
  for (const registryKey of publishedKeys) {
    assert.ok(
      byModel.has(registryKey),
      `published ${registryKey} has no workbook-discovered matrix cases`,
    );
  }
  for (const [registryKey, modelCases] of byModel) {
    const published = registry.models[registryKey];
    assert.ok(published, `workbook-promoted ${registryKey} is missing from the registry`);
    assert.deepEqual(
      JSON.parse(JSON.stringify(modelCases.map((matrixCase) => matrixCase.variantId).sort())),
      JSON.parse(JSON.stringify(published.data.variants.map((variant) => variant.variant_id).sort())),
      `${registryKey} matrix variants drifted from the registry`,
    );
  }
});

for (const [registryKey, modelCases] of byModel) {
  const { runtime } = loadMatrixRuntime();
  test(`${registryKey}: every declared variant satisfies the rest-state matrix`, () => {
    for (const matrixCase of modelCases) {
      activateVariant(runtime, matrixCase);
      assertRestState(runtime, matrixCase, registry);
      seen.add(`${matrixCase.registryKey}:${matrixCase.variantId}`);
    }
  });

  test(`${registryKey}: representative transitions preserve generic rule contracts`, () => {
    const matrixCase = modelCases[0];
    activateVariant(runtime, matrixCase);
    representativeTransitions(runtime);
    assertExclusiveSingleSelection(runtime);
    assertSelectedOptionsExist(runtime);
    assertSelectedNotDisabled(runtime);
    assertOrderTotals(runtime);
    assertDefaultRuleContract(runtime);
    assertReconcileIdempotent(runtime);
  });
}

test("model switching clears incompatible prior-model state for every promoted pair", () => {
  const { runtime } = loadMatrixRuntime();
  const keys = [...byModel.keys()];
  assert.ok(keys.length >= 2, "need at least two promoted models to switch");
  for (let index = 0; index < keys.length; index += 1) {
    const fromKey = keys[index];
    const toKey = keys[(index + 1) % keys.length];
    assertModelSwitchClearsPrior(runtime, byModel.get(fromKey)[0], byModel.get(toKey)[0], registry);
  }
});

test("the report names every promoted model and active variant the matrix exercised", () => {
  const reported = matrixReport(cases, seen);
  assert.deepEqual(reported.seen, reported.variants);
});

function firstCase() {
  return cases[0];
}

function primed(runtime, matrixCase = firstCase()) {
  activateVariant(runtime, matrixCase);
  return matrixCase;
}

test("forced failure: model activation binds the wrong registry data", () => {
  const { runtime } = loadMatrixRuntime();
  const matrixCase = primed(runtime);
  const otherKey = [...byModel.keys()].find((key) => key !== matrixCase.registryKey);
  runtime.setActiveData(registry.models[otherKey].data);
  assert.throws(
    () => assertModelActivation(runtime, matrixCase, registry),
    /should bind only that model's registry data/,
  );
});

test("forced failure: body/trim resolve to the wrong variant", () => {
  const { runtime } = loadMatrixRuntime();
  const matrixCase = primed(runtime);
  runtime.state.trimLevel = byModel.get(matrixCase.registryKey).find((row) => row.variantId !== matrixCase.variantId).trimLevel;
  assert.throws(() => assertVariantResolution(runtime, matrixCase), /resolved the wrong variant|still has choices from another variant/);
});

test("forced failure: reset plus reconciliation is not a fixed point", () => {
  const { runtime } = loadMatrixRuntime();
  primed(runtime);
  const original = runtime.reconcileSelections;
  runtime.reconcileSelections = () => {
    original.call(runtime);
    runtime.state.selectedInterior = "__not_a_fixed_point__";
  };
  assert.throws(() => assertResetFixedPoint(runtime), /not a stable fixed point/);
  runtime.reconcileSelections = original;
});

test("forced failure: a second reconciliation is not idempotent", () => {
  const { runtime } = loadMatrixRuntime();
  primed(runtime);
  const original = runtime.reconcileSelections;
  let calls = 0;
  runtime.reconcileSelections = () => {
    original.call(runtime);
    calls += 1;
    if (calls === 2) runtime.state.selectedInterior = "__not_idempotent__";
  };
  assert.throws(() => assertReconcileIdempotent(runtime), /not idempotent/);
  runtime.reconcileSelections = original;
});

test("forced failure: a selected option does not exist in context", () => {
  const { runtime } = loadMatrixRuntime();
  primed(runtime);
  runtime.state.selected.add("opt_does_not_exist");
  assert.throws(() => assertSelectedOptionsExist(runtime), /does not exist on the current variant/);
});

test("forced failure: a selected option remains disabled", () => {
  const { runtime } = loadMatrixRuntime();
  primed(runtime);
  const choice = runtime.activeChoiceRows().find((row) => runtime.state.selected.has(row.option_id) && row.selectable === "True");
  assert.ok(choice, "need a selected selectable option to mutate");
  const original = runtime.disableReasonForChoice;
  runtime.disableReasonForChoice = (row, options) => {
    if (row.option_id === choice.option_id) return "forced disabled";
    return original.call(runtime, row, options);
  };
  assert.throws(() => assertSelectedNotDisabled(runtime), /remains disabled/);
  runtime.disableReasonForChoice = original;
});

test("forced failure: two peers remain selected in a single-selection exclusive group", () => {
  const { runtime } = loadMatrixRuntime();
  primed(runtime);
  const group = (runtime.data.exclusiveGroups || []).find((row) => {
    if (!["single_within_group", "required_single_within_group"].includes(row.selection_mode)) return false;
    return (row.option_ids || []).length >= 2;
  });
  assert.ok(group, "need an exclusive group to mutate");
  runtime.state.selected.add(group.option_ids[0]);
  runtime.state.selected.add(group.option_ids[1]);
  assert.throws(() => assertExclusiveSingleSelection(runtime), /selected peers/);
});

test("forced failure: a required selection is neither satisfied nor reported", () => {
  const { runtime } = loadMatrixRuntime();
  primed(runtime);
  const original = runtime.missingRequired;
  runtime.missingRequired = () => [];
  runtime.state.selectedInterior = "";
  assert.throws(() => assertRequiredSatisfiedOrReported(runtime), /unsatisfied and unreported|missing interior is not reported/);
  runtime.missingRequired = original;
});

test("forced failure: include/default rule contract is dropped", () => {
  const { runtime } = loadMatrixRuntime();
  primed(runtime);
  const choice = runtime.activeChoiceRows().find((row) => {
    if (row.display_behavior !== "default_selected") return false;
    if (row.selectable !== "True" || row.status === "unavailable") return false;
    return runtime.state.selected.has(row.option_id);
  });
  assert.ok(choice, "need a default-selected option to drop");
  runtime.state.selected.delete(choice.option_id);
  assert.throws(() => assertDefaultRuleContract(runtime), /neither selected nor auto-added|left its exclusive group empty/);
});

test("forced failure: order totals disagree with the exposed lines", () => {
  const { runtime } = loadMatrixRuntime();
  primed(runtime);
  const original = runtime.currentOrder;
  runtime.currentOrder = () => {
    const order = original.call(runtime);
    return {
      ...order,
      pricing: { ...order.pricing, total_msrp: order.pricing.total_msrp + 1 },
    };
  };
  assert.throws(() => assertOrderTotals(runtime), /total_msrp does not equal/);
  runtime.currentOrder = original;
});

test("forced failure: model switch keeps prior-model user state", () => {
  const { runtime } = loadMatrixRuntime();
  const keys = [...byModel.keys()];
  const fromCase = byModel.get(keys[0])[0];
  const toCase = byModel.get(keys[1])[0];
  const original = runtime.activateModel;
  runtime.activateModel = (modelKey, options) => {
    const interior = runtime.state.selectedInterior;
    const userSelected = [...runtime.state.userSelected];
    original.call(runtime, modelKey, options);
    runtime.state.selectedInterior = interior;
    for (const optionId of userSelected) runtime.state.userSelected.add(optionId);
  };
  assert.throws(() => assertModelSwitchClearsPrior(runtime, fromCase, toCase, registry), /survived a model switch/);
  runtime.activateModel = original;
});

test("forced failure: dealer payload identity does not match the active model/variant", () => {
  const { runtime } = loadMatrixRuntime();
  const matrixCase = primed(runtime);
  const original = runtime.dealerSubmissionPayload;
  runtime.dealerSubmissionPayload = (order) => ({
    ...original.call(runtime, order),
    model: "not-this-model",
  });
  assert.throws(() => assertPayloadIdentity(runtime, matrixCase), /dealer payload model key/);
  runtime.dealerSubmissionPayload = original;
});
