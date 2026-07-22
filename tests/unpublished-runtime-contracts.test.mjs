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
  assert.deepEqual(
    sectionRpoOrder(contracts.grand_sport_x, "sec_roof_001"),
    ["CM9", "C2Z", "D84", "D86", "CF7", "CC3", "CF8"]
  );
  assert.deepEqual(sectionRpoOrder(contracts.zr1, "sec_roof_001"), ["C2Z"]);
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