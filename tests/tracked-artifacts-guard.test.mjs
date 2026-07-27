// Coverage for the shared guard the generation review gates depend on.
//
// Without these, a vacuous implementation of tracked-artifacts.mjs (an empty
// digest map, or an assert that never compares) would be invisible: every gate
// that uses it would still pass while proving nothing about tracked artifacts.
import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import { assertTrackedArtifactsUnchanged, readTrackedArtifacts } from "./lib/tracked-artifacts.mjs";

test("readTrackedArtifacts digests the real tracked generated surface", () => {
  const digests = readTrackedArtifacts();
  assert.ok(digests.size > 1, "expected more than one tracked generated artifact");
  assert.ok(digests.has("form-app/data.js"), "published registry must be covered");
  assert.ok(
    digests.has("form-output/runtime/z06-runtime-contract.json"),
    "runtime contracts the review gates regenerate must be covered"
  );
  for (const digest of digests.values()) {
    assert.match(digest, /^[0-9a-f]{64}$/, "each entry must be a sha256 digest");
  }
});

test("assertTrackedArtifactsUnchanged passes when nothing moved", () => {
  assertTrackedArtifactsUnchanged(readTrackedArtifacts());
});

test("assertTrackedArtifactsUnchanged reports a modified artifact", () => {
  const before = readTrackedArtifacts();
  before.set("form-app/data.js", "0".repeat(64));
  assert.throws(() => assertTrackedArtifactsUnchanged(before), /form-app\/data\.js \(modified\)/);
});

test("assertTrackedArtifactsUnchanged reports an added artifact", () => {
  const before = readTrackedArtifacts();
  before.delete("form-app/data.js");
  assert.throws(() => assertTrackedArtifactsUnchanged(before), /form-app\/data\.js \(added\)/);
});

test("assertTrackedArtifactsUnchanged reports a removed artifact", () => {
  const before = readTrackedArtifacts();
  before.set("form-output/runtime/does-not-exist.json", "0".repeat(64));
  assert.throws(() => assertTrackedArtifactsUnchanged(before), /does-not-exist\.json \(removed\)/);
});

// The three cases above are synthetic — they move the `before` map rather than
// the filesystem. These two move real files under the protected roots, which is
// the only way to prove the guard sees what a generator would actually do.
test("assertTrackedArtifactsUnchanged reports a real untracked file written into a protected root", () => {
  const strayPath = "form-output/inspection/.tracked-artifacts-guard-stray.json";
  const before = readTrackedArtifacts();
  fs.writeFileSync(strayPath, "{}\n");
  try {
    assert.throws(() => assertTrackedArtifactsUnchanged(before), /tracked-artifacts-guard-stray\.json \(added\)/);
  } finally {
    fs.rmSync(strayPath, { force: true });
  }
  assertTrackedArtifactsUnchanged(before);
});

test("assertTrackedArtifactsUnchanged reports a real deleted artifact without crashing", () => {
  const victimPath = "form-output/runtime/z06-runtime-contract.json";
  const before = readTrackedArtifacts();
  const payload = fs.readFileSync(victimPath);
  fs.rmSync(victimPath);
  try {
    assert.throws(() => assertTrackedArtifactsUnchanged(before), /z06-runtime-contract\.json \(removed\)/);
  } finally {
    fs.writeFileSync(victimPath, payload);
  }
  assertTrackedArtifactsUnchanged(before);
});
