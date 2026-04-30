import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

function withoutGeneratedAt(data) {
  return JSON.parse(JSON.stringify({
    ...data,
    dataset: {
      ...data.dataset,
      generated_at: "<timestamp>",
    },
  }));
}

function loadAppData() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync("form-app/data.js", "utf8"), context);
  return context.window.STINGRAY_FORM_DATA;
}

const jsonData = JSON.parse(fs.readFileSync("form-output/stingray-form-data.json", "utf8"));
const appData = loadAppData();

test("generated JSON and static app data stay synchronized apart from timestamp", () => {
  assert.deepEqual(withoutGeneratedAt(appData), withoutGeneratedAt(jsonData));
});

test("Stingray generated contract keeps the closed-out shape", () => {
  assert.equal(jsonData.dataset.name, "2027 Corvette Stingray operational form");
  assert.deepEqual(
    jsonData.variants.map((variant) => variant.variant_id),
    ["1lt_c07", "2lt_c07", "3lt_c07", "1lt_c67", "2lt_c67", "3lt_c67"]
  );
  assert.equal(jsonData.variants.length, 6);
  assert.equal(jsonData.contextChoices.length, 8);
  assert.equal(jsonData.choices.length, 1548);
  assert.equal(jsonData.standardEquipment.length, 464);
  assert.equal(jsonData.rules.length, 238);
  assert.equal(jsonData.priceRules.length, 43);
  assert.equal(jsonData.interiors.length, 130);
  assert.equal(jsonData.validation.filter((row) => row.severity === "error").length, 0);
});
