import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const contractPaths = {
  grand_sport_x: "form-output/runtime/grand-sport-x-runtime-contract.json",
  zr1: "form-output/runtime/zr1-runtime-contract.json",
  zr1x: "form-output/runtime/zr1x-runtime-contract.json",
};

const contracts = Object.fromEntries(
  Object.entries(contractPaths).map(([modelKey, path]) => [modelKey, JSON.parse(fs.readFileSync(path, "utf8"))])
);

function sectionRpoOrder(data, sectionId) {
  const orderByRpo = new Map();
  for (const choice of data.choices.filter((item) => item.section_id === sectionId && item.active === "True")) {
    const order = Number(choice.display_order);
    if (!orderByRpo.has(choice.rpo) || order < orderByRpo.get(choice.rpo)) {
      orderByRpo.set(choice.rpo, order);
    }
  }
  return [...orderByRpo]
    .sort((a, b) => a[1] - b[1] || a[0].localeCompare(b[0]))
    .map(([rpo]) => rpo);
}

test("retained unpublished contracts preserve reviewed roof-option baselines", () => {
  // Ordering is owned by `grand_sport_x_options.display_order` (10,20,30,40,50,60,70).
  // Updated 2026-07-27 when the stale GSX contract was regenerated: the previous
  // expectation pinned the artifact's order, which the workbook had since moved
  // past. If this fails again, read the workbook column before editing the list.
  assert.deepEqual(
    sectionRpoOrder(contracts.grand_sport_x, "sec_roof_001"),
    ["CF7", "C2Z", "CC3", "CM9", "CF8", "D84", "D86"]
  );
  // zr1 carries CFC (Visible Carbon Fiber Retractable Hardtop) in sec_roof_001;
  // zr1x files the same option under sec_stan_001 instead. That asymmetry is
  // workbook-authored — see zr1_options / zr1x_options `section_id`.
  assert.deepEqual(sectionRpoOrder(contracts.zr1, "sec_roof_001"), ["C2Z", "CFC"]);
  assert.deepEqual(sectionRpoOrder(contracts.zr1x, "sec_roof_001"), ["C2Z"]);
});

test("retained unpublished contracts preserve generated order-summary metadata", () => {
  for (const [modelKey, data] of Object.entries(contracts)) {
    const expectsRequiredCharges = modelKey === "zr1" || modelKey === "zr1x";
    const expectedOrderSummarySections = expectsRequiredCharges ? 12 : 11;
    const expectedOrderSummaryStepMap = expectsRequiredCharges ? 14 : 13;

    assert.equal(data.steps.length, 14, `${modelKey} should retain generated runtime steps`);
    assert.equal(data.orderSummary.sections.length, expectedOrderSummarySections);
    assert.equal(Object.keys(data.orderSummary.stepMap).length, expectedOrderSummaryStepMap);
    assert.equal(data.orderSummary.stepMap.base_interior, "seats_interior");
    assert.equal(Object.hasOwn(data.orderSummary.stepMap, "standard_equipment"), expectsRequiredCharges);
  }
});