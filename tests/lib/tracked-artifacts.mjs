// Shared protected-surface guard for node gates that invoke scripts/generate_form.py.
//
// Those gates are review/diagnostic surfaces: they generate into a temporary
// --output-root and must leave every tracked generated artifact byte-identical.
// Hash the tracked surfaces before generation and assert them unchanged after.
//
// This check reads the whole tracked generated surface, so it cannot run
// concurrently with another process that writes those files. Run these gates
// serially (see the README gate matrix).
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import fs from "node:fs";

const TRACKED_ARTIFACT_ROOTS = ["form-output", "form-app"];
const MISSING = "missing";

// Tracked files, plus whatever is on disk under the same roots. The disk walk is
// what catches a generator writing a brand-new untracked file into a protected
// root; git alone would never list it.
function artifactPaths() {
  const tracked = execFileSync("git", ["ls-files", "-z", ...TRACKED_ARTIFACT_ROOTS], { encoding: "utf8" })
    .split("\0")
    .filter((path) => path.length > 0);
  const paths = new Set(tracked);
  for (const root of TRACKED_ARTIFACT_ROOTS) {
    for (const entry of fs.readdirSync(root, { recursive: true, withFileTypes: true })) {
      if (entry.isFile()) paths.add(`${entry.parentPath}/${entry.name}`);
    }
  }
  return [...paths].sort();
}

/** Digest of every file under form-output/ and form-app/, keyed by repo-relative path. */
export function readTrackedArtifacts() {
  const paths = artifactPaths();
  assert.ok(paths.length > 0, "expected generated artifacts under form-output/ and form-app/");
  const digests = new Map();
  for (const path of paths) {
    // A tracked file that generation deleted must reach the comparison as a
    // removal, not as an ENOENT thrown out of the digest loop.
    digests.set(
      path,
      fs.existsSync(path) ? createHash("sha256").update(fs.readFileSync(path)).digest("hex") : MISSING
    );
  }
  return digests;
}

/** Assert no generated artifact changed, appeared, or disappeared since `before`. */
export function assertTrackedArtifactsUnchanged(before) {
  const after = readTrackedArtifacts();
  const changed = [];
  for (const [path, digest] of after) {
    const previous = before.has(path) ? before.get(path) : MISSING;
    if (previous === digest) continue;
    if (digest === MISSING) changed.push(`${path} (removed)`);
    else if (previous === MISSING) changed.push(`${path} (added)`);
    else changed.push(`${path} (modified)`);
  }
  for (const [path, previous] of before) {
    if (!after.has(path) && previous !== MISSING) changed.push(`${path} (removed)`);
  }
  changed.sort();
  assert.deepEqual(changed, [], `generation must not write repository generated artifacts: ${changed.join(", ")}`);
}
