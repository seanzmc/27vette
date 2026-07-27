import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import crypto from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";

// Spec Pass 3 requirements 6 and 9. Split out of `z06-runtime-promotion.test.mjs`
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
  assert.deepEqual(result.models, ["stingray", "grandSport", "z06"]);

  const registry = loadRegistry(target);
  assert.equal(registry.defaultModelKey, "stingray");
  assert.equal(registry.models.z06.data.dataset.status, "runtime_active");
  assert.equal(registry.models.grandSport.data.dataset.status, "runtime_active");

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
