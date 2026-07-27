import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

// Spec Pass 3 requirement 6. This assertion runs `scripts/generate_registry.py`,
// which rewrites the tracked `form-app/data.js`. It lives in its own file so the
// read-only promotion assertions in `z06-runtime-promotion.test.mjs` can be run
// as a gate without modifying a published artifact.
//
// Running THIS file dirties `form-app/data.js` (by `generated_at` at minimum).
// That is inherent until requirement 9 gives the generator an isolated output
// path; the split is what stops it from happening on every read-only gate run.

function loadDataWindow() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync("form-app/data.js", "utf8"), context);
  return context.window;
}

test("dedicated registry generator publishes promoted runtime artifacts", () => {
  const output = execFileSync(".venv/bin/python", ["scripts/generate_registry.py"], { encoding: "utf8" });
  const result = JSON.parse(output);
  assert.equal(result.status, "registry_generated");
  assert.ok(result.output.endsWith("form-app/data.js"));
  assert.deepEqual(result.models, ["stingray", "grandSport", "z06"]);

  const registry = loadDataWindow().CORVETTE_FORM_DATA;
  assert.equal(registry.defaultModelKey, "stingray");
  assert.equal(registry.models.z06.data.dataset.status, "runtime_active");
  assert.equal(registry.models.grandSport.data.dataset.status, "runtime_active");
});
