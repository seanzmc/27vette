import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";

import { cell, workbookRows, workbookTruthy } from "./lib/workbook-truth.mjs";

// Spec Pass 3 requirements 6 and 9. Split out of the published-runtime gate
// so the read-only promotion assertions never invoke the publisher, then given an
// isolated `--output` by requirement 9 so this file no longer rewrites the tracked
// `form-app/data.js` either. Running the whole node gate set is now read-only with
// respect to the published registry.

const TRACKED_REGISTRY = "form-app/data.js";

function sha256(file) {
  return crypto.createHash("sha256").update(fs.readFileSync(file)).digest("hex");
}

function loadRegistry(file) {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync(file, "utf8"), context);
  return context.window.CORVETTE_FORM_DATA;
}

// Expected side of the publication parity check: a direct read of the
// `model_registry_promotion` rows, ordered the way the sheet orders them.
function promotedRegistryKeys() {
  return workbookRows("model_registry_promotion")
    .filter((row) => workbookTruthy(row.active) && workbookTruthy(row.promoted_to_runtime))
    .sort((a, b) => Number(a.display_order) - Number(b.display_order))
    .map((row) => cell(row.registry_key));
}

test("dedicated registry generator publishes promoted runtime artifacts", () => {
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "registry-publication-"));
  const target = path.join(scratch, "data.js");
  const before = sha256(TRACKED_REGISTRY);

  const output = execFileSync(
    ".venv/bin/python",
    ["scripts/generate_registry.py", "--output", target],
    { encoding: "utf8" }
  );
  const result = JSON.parse(output);
  assert.equal(result.status, "registry_generated");
  assert.equal(result.output, target);

  // Checkpoint 1 of the fast layered validation suite (spec §9) replaced the
  // literal ["stingray", "grandSport", "z06"] here. Three models were promoted
  // when it was written and six are promoted now, so the literal failed for a
  // valid workbook state. Which models are promoted is workbook data, compared
  // against the promotion rows themselves; the catalog records
  // `promoted_model_membership` as a proposed acceptance lock, which stays
  // proposed because declaring it freezes a business decision (spec §12).
  const expectedModels = promotedRegistryKeys();
  assert.ok(expectedModels.length > 0, "model_registry_promotion promotes no model");
  assert.deepEqual(result.models, expectedModels);

  const registry = loadRegistry(target);
  // `defaultModelKey === "stingray"` is the default_model_is_stingray
  // acceptance lock, owned by tests/multi-model-runtime-switching.test.mjs.
  // This gate asserts only that publication carries the workbook's flagged row
  // through, without restating which model that is (spec §4.4).
  const defaultRows = workbookRows("model_registry_promotion").filter(
    (row) => workbookTruthy(row.active) && workbookTruthy(row.default_model)
  );
  assert.equal(defaultRows.length, 1, "exactly one active promotion row may be the default model");
  assert.equal(registry.defaultModelKey, cell(defaultRows[0].registry_key));

  for (const registryKey of expectedModels) {
    assert.ok(registry.models[registryKey], `${registryKey} is promoted but absent from the registry`);
    assert.equal(
      registry.models[registryKey].data.dataset.status,
      "runtime_active",
      `${registryKey} published a contract that is not runtime_active`
    );
  }

  // Requirement 9's practical payoff: publishing to an explicit target must not
  // touch the tracked registry. Breaks if --output is ever ignored or partially
  // honoured.
  assert.equal(sha256(TRACKED_REGISTRY), before, "publishing to --output rewrote the tracked registry");
  assert.equal(fs.readdirSync(scratch).length, 1, "atomic write left a temporary file behind");

  fs.rmSync(scratch, { recursive: true, force: true });
});

test("the published registry and an isolated rebuild agree apart from timestamps", () => {
  const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "registry-parity-"));
  const target = path.join(scratch, "data.js");

  execFileSync(".venv/bin/python", ["scripts/generate_registry.py", "--output", target], { encoding: "utf8" });

  const stripTimestamps = (value) => {
    if (Array.isArray(value)) return value.map(stripTimestamps);
    if (value && typeof value === "object") {
      return Object.fromEntries(
        Object.entries(value)
          .filter(([key]) => !["generated_at", "generatedAt", "sourceGeneratedAt"].includes(key))
          .map(([key, item]) => [key, stripTimestamps(item)])
      );
    }
    return value;
  };

  // Breaks if --output ever produces a different registry than the default path,
  // which would make the isolated gate above prove nothing about publication.
  // Compared as serialized JSON, not deepEqual: each registry is evaluated in its
  // own vm context, so the objects are cross-realm and fail a prototype-sensitive
  // structural compare even when their contents are identical.
  assert.equal(
    JSON.stringify(stripTimestamps(loadRegistry(target))),
    JSON.stringify(stripTimestamps(loadRegistry(TRACKED_REGISTRY)))
  );

  fs.rmSync(scratch, { recursive: true, force: true });
});
