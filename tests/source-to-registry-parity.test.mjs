// Source-to-registry parity: what the workbook promotes is what publishes.
//
// Spec `docs/superpowers/specs/2026-08-17-fast-layered-validation-suite.md`
// §4.2 and Checkpoint 2. The companion of `source-to-contract-parity`: that
// gate proves each runtime contract equals its source rows, this one proves the
// published registry equals the workbook's promotion and model-metadata rows,
// and that it carries exactly the contracts those rows name.
//
//   expected: model_registry_promotion + model_master + asset_map, read
//             through the §6.2 workbook-truth snapshot
//   actual:   form-app/data.js (or a candidate registry through
//             CORVETTE_FORM_DATA_JS)
//
// Checkpoint 1 replaced `assert.deepEqual(result.models, ["stingray",
// "grandSport", "z06"])` in `z06-registry-publication` with a comparison
// against the promotion rows. That fixed one literal in one gate; this is the
// general owner. Membership, order, default model, labels, slugs, setup copy,
// card media, and legacy aliases all come from workbook rows here, so a
// promotion change moves the gate instead of breaking it.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import process from "node:process";
import test from "node:test";

import { cell, workbookTruth } from "./lib/workbook-truth.mjs";

const truth = workbookTruth();

// The candidate lane sets CORVETTE_FORM_DATA_JS to its temporary registry, the
// same override the browser harness already uses. Unset, this reads the
// published registry.
const REGISTRY_PATH = process.env.CORVETTE_FORM_DATA_JS || "form-app/data.js";
const CONTRACT_ROOT = process.env.CORVETTE_CONTRACT_ROOT || ".";

const ASSET_IMAGE_FIELDS = [
  "image_url",
  "image_alt",
  "image_fit",
  "image_position",
  "hover_image_url",
  "hover_image_alt",
  "hover_image_position",
];

function loadRegistry(path) {
  const source = readFileSync(path, "utf8");
  const scope = { window: {} };
  // The published bundle is a browser assignment, not a module. Evaluating it
  // against a bare object is how the runtime harness reads it too.
  new Function("window", source)(scope.window);
  const registry = scope.window.CORVETTE_FORM_DATA;
  assert.ok(registry, `${path} did not define window.CORVETTE_FORM_DATA`);
  return { registry, window: scope.window };
}

const { registry, window: registryWindow } = loadRegistry(REGISTRY_PATH);
const promoted = truth.promotions.rows;

test("published models equal the promoted rows, in their declared order", () => {
  assert.ok(promoted.length > 0, "workbook promotes no model");
  assert.deepEqual(
    Object.keys(registry.models),
    promoted.map((row) => truth.models[row.model_key].registry_key),
    "published model membership or order drifted from model_registry_promotion",
  );
});

test("the default model is the single row the workbook marks default", () => {
  assert.deepEqual(
    truth.promotions.default_model_keys.length,
    1,
    `model_registry_promotion declares ${truth.promotions.default_model_keys.length} default models`,
  );
  const [defaultModelKey] = truth.promotions.default_model_keys;
  assert.equal(registry.defaultModelKey, truth.models[defaultModelKey].registry_key);
});

test("every promoted row names a runtime contract that exists", () => {
  for (const row of promoted) {
    assert.equal(row.artifact_type, "runtime_contract", `${row.model_key} artifact_type`);
    assert.ok(row.artifact_path, `${row.model_key} names no artifact path`);
    assert.doesNotThrow(
      () => readFileSync(resolve(CONTRACT_ROOT, row.artifact_path), "utf8"),
      `${row.model_key} promotes a missing artifact: ${row.artifact_path}`,
    );
  }
});

test("legacy aliases are exactly the aliases the workbook declares", () => {
  // An alias is an additional global the published bundle defines for a model.
  // The workbook decides which models have one; a published alias with no row
  // behind it is an unowned public surface.
  const declared = new Map(
    promoted.filter((row) => row.legacy_alias).map((row) => [row.legacy_alias, row.model_key]),
  );
  for (const [alias, modelKey] of declared) {
    assert.ok(registryWindow[alias], `${modelKey} declares legacy alias ${alias} but the bundle has none`);
    assert.deepEqual(
      registryWindow[alias],
      registry.models[truth.models[modelKey].registry_key].data,
      `${alias} does not alias ${modelKey}'s published data`,
    );
  }
  const publishedAliases = Object.keys(registryWindow).filter(
    (name) => name !== "CORVETTE_FORM_DATA" && name.endsWith("_FORM_DATA"),
  );
  assert.deepEqual(
    publishedAliases.sort(),
    [...declared.keys()].sort(),
    "published legacy aliases drifted from the workbook's legacy_alias column",
  );
});

for (const promotion of promoted) {
  const modelKey = promotion.model_key;
  const model = truth.models[modelKey];
  const published = registry.models[model.registry_key];

  test(`${modelKey}: published model metadata equals its model_master row`, () => {
    assert.ok(published, `${modelKey} is promoted but absent from the registry`);
    assert.equal(published.key, model.registry_key, "registry key");
    assert.equal(published.label, model.model_label, "label");
    assert.equal(published.exportSlug, model.export_slug, "export slug");
    // modelName is the one composed string: the marque plus the workbook's
    // label. Stated as the composition so a changed label follows it.
    assert.equal(published.modelName, `Corvette ${model.model_label}`, "model name");
  });

  test(`${modelKey}: published setup copy equals its model_master columns`, () => {
    const master = model.master_row;
    assert.deepEqual(
      published.vehicleSetup,
      {
        cardSubtitle: cell(master.setup_card_subtitle),
        eyebrow: cell(master.setup_eyebrow),
        title: cell(master.setup_title),
        description: cell(master.setup_description),
        facts: [master.setup_fact_1, master.setup_fact_2, master.setup_fact_3]
          .map(cell)
          .filter(Boolean),
      },
      "published vehicle setup copy drifted from model_master",
    );
  });

  test(`${modelKey}: published data is exactly the contract the row promotes`, () => {
    const contract = JSON.parse(readFileSync(resolve(CONTRACT_ROOT, promotion.artifact_path), "utf8"));
    assert.deepEqual(
      published.data,
      contract,
      `published ${modelKey} data is not the artifact its promotion row names`,
    );
  });

  test(`${modelKey}: published card media equals its applicable asset_map row`, () => {
    // Model-card assets are addressed by registry key, and unlike option media
    // they take no wildcard row — a card belongs to one model.
    const expected = (truth.assets[modelKey] ?? {})[`model::${model.registry_key}`];
    for (const field of ASSET_IMAGE_FIELDS) {
      if (expected) {
        assert.equal(published[field], expected[field], `${modelKey} ${field}`);
      } else {
        assert.equal(
          Object.hasOwn(published, field),
          false,
          `${modelKey} publishes ${field} with no applicable active asset_map row`,
        );
      }
    }
  });
}

test("no unpromoted model reaches the published registry", () => {
  const promotedRegistryKeys = new Set(promoted.map((row) => truth.models[row.model_key].registry_key));
  const unpromoted = Object.values(truth.models)
    .filter((model) => !promotedRegistryKeys.has(model.registry_key))
    .map((model) => model.registry_key);
  for (const registryKey of unpromoted) {
    assert.equal(
      Object.hasOwn(registry.models, registryKey),
      false,
      `${registryKey} publishes without an active promoted row`,
    );
  }
});
