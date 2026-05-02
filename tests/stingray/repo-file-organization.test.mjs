import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

const MODEL_CONFIG_PATH = "scripts/corvette_form_generator/model_configs.py";
const ORG_DOC_PATH = "docs/repo-file-organization.md";

function fileExists(path) {
  return fs.existsSync(path) && fs.statSync(path).isFile();
}

function modelConfigReferences(filename) {
  const source = fs.readFileSync(MODEL_CONFIG_PATH, "utf8");
  return source.includes(`"architectureAudit" / "${filename}"`);
}

test("active interior reference inputs exist outside archived paths", () => {
  const activeReferencePaths = ["architectureAudit/stingray_interiors_refactor.csv"];
  if (modelConfigReferences("grand_sport_interiors_refactor.csv")) {
    activeReferencePaths.push("architectureAudit/grand_sport_interiors_refactor.csv");
  }

  for (const activePath of activeReferencePaths) {
    assert.ok(fileExists(activePath), `${activePath} should exist as an active generator input.`);
    assert.ok(!activePath.startsWith("archived/"), `${activePath} should not be classified as archived.`);

    const archivedPath = `archived/docs/${activePath}`;
    if (fileExists(archivedPath)) {
      assert.ok(
        fileExists(activePath),
        `${archivedPath} may exist as reference material, but it must not be the only copy of an active input.`
      );
    }
  }
});

test("experimental build output remains ignored", () => {
  const gitignore = fs.readFileSync(".gitignore", "utf8");
  assert.match(gitignore, /^build\/experimental\/$/m);
});

test("repo organization doc classifies source, generated, experimental, and archived files", () => {
  const doc = fs.readFileSync(ORG_DOC_PATH, "utf8");
  for (const requiredSnippet of [
    "stingray_master.xlsx",
    "architectureAudit/stingray_interiors_refactor.csv",
    "architectureAudit/grand_sport_interiors_refactor.csv",
    "data/stingray/**/*.csv",
    "data/stingray/validation/projected_slice_ownership.csv",
    "form-app/data.js",
    "form-output/*",
    "build/experimental/form-app/*",
    "archived/docs/*",
    "Do not move active inputs into archived paths.",
    "archived/ means not required for current generator/test gates.",
  ]) {
    assert.ok(doc.includes(requiredSnippet), `${ORG_DOC_PATH} should document ${requiredSnippet}.`);
  }
});
