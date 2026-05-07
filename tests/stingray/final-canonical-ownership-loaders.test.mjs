import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const FIRST_SLICE_SCRIPT = "scripts/stingray_csv_first_slice.py";
const OVERLAY_SCRIPT = "scripts/stingray_csv_shadow_overlay.py";
const PACKAGE = "data/stingray";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";

const FINAL_CANONICAL_OPTION_FIELDS = [
  "canonical_option_id",
  "rpo",
  "label",
  "description",
  "canonical_kind",
  "duplicate_rpo_classification",
  "active",
  "notes",
];
const FINAL_OPTION_PRESENTATION_FIELDS = [
  "presentation_id",
  "canonical_option_id",
  "rpo_override",
  "presentation_role",
  "choice_group_id",
  "section_id",
  "section_name",
  "category_id",
  "category_name",
  "step_key",
  "selection_mode",
  "display_order",
  "selectable",
  "active",
  "label",
  "description",
  "source_detail_raw",
  "notes",
  "legacy_option_id",
  "choice_mode",
  "selection_mode_label",
];
const FINAL_OPTION_STATUS_RULE_FIELDS = [
  "status_rule_id",
  "canonical_option_id",
  "presentation_id",
  "context_scope_id",
  "status",
  "status_label",
  "priority",
  "active",
  "notes",
];
const FINAL_VARIANT_FIELDS = [
  "variant_id",
  "model_year",
  "gm_model_code",
  "model_key",
  "body_style",
  "trim_level",
  "active",
  "notes",
];
const FINAL_CONTEXT_SCOPE_FIELDS = [
  "context_scope_id",
  "model_year",
  "model_key",
  "variant_id",
  "body_style",
  "trim_level",
  "priority",
  "active",
  "notes",
];
const FINAL_PROJECTION_OWNERSHIP_FIELDS = [
  "ownership_id",
  "entity_type",
  "entity_id",
  "ownership_status",
  "legacy_rpo",
  "legacy_option_id",
  "notes",
  "active",
];
const FINAL_PRESERVED_BOUNDARY_FIELDS = [
  "boundary_id",
  "relationship_type",
  "source_type",
  "source_id",
  "target_type",
  "target_id",
  "legacy_source_option_id",
  "legacy_target_option_id",
  "reason",
  "active",
];

function tempPackage() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-final-canonical-ownership-"));
  const packageDir = path.join(root, "stingray");
  fs.cpSync(PACKAGE, packageDir, { recursive: true });
  fs.rmSync(path.join(packageDir, "canonical"), { recursive: true, force: true });
  return packageDir;
}

function csvEscape(value) {
  const stringValue = String(value ?? "");
  return /[",\n]/.test(stringValue) ? `"${stringValue.replaceAll('"', '""')}"` : stringValue;
}

function writeCsv(filePath, fields, rows) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const lines = [fields.join(",")];
  for (const row of rows) {
    lines.push(fields.map((field) => csvEscape(row[field] ?? "")).join(","));
  }
  fs.writeFileSync(filePath, `${lines.join("\n")}\n`);
}

function emitLegacyFragment(packageDir = PACKAGE) {
  const output = execFileSync(PYTHON, [FIRST_SLICE_SCRIPT, "--package", packageDir, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function runOverlay(args = []) {
  return spawnSync(PYTHON, [OVERLAY_SCRIPT, ...args], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 32 * 1024 * 1024,
  });
}

function runStrictOverlayWithFragment(packageDir, fragmentPath) {
  const code = `
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path("scripts").resolve()))
from stingray_csv_first_slice import CsvSlice
from stingray_csv_shadow_overlay import (
    OverlayError,
    load_combined_ownership_scope,
    load_production_data,
    overlay_shadow_data,
)

package_dir = Path(${JSON.stringify(packageDir)})
fragment = json.loads(Path(${JSON.stringify(fragmentPath)}).read_text(encoding="utf-8"))
production = load_production_data(Path("form-app/data.js"))
csv_slice = CsvSlice(package_dir)
try:
    ownership = load_combined_ownership_scope(
        Path(${JSON.stringify(OWNERSHIP_MANIFEST)}),
        package_dir,
        csv_slice,
        production,
        fragment,
        require_complete_final_owned_option_coverage=True,
    )
    overlay_shadow_data(production, fragment, ownership)
except OverlayError as error:
    print(str(error))
    raise SystemExit(1)
`;
  return spawnSync(PYTHON, ["-c", code], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 32 * 1024 * 1024,
  });
}

function overlayData(packageDir = PACKAGE, extraArgs = []) {
  const output = execFileSync(PYTHON, [OVERLAY_SCRIPT, "--package", packageDir, ...extraArgs], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 32 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function writeFinalContextTables(packageDir) {
  const variants = [
    ["1lt_c07", "C07", "coupe", "1LT"],
    ["2lt_c07", "C07", "coupe", "2LT"],
    ["3lt_c07", "C07", "coupe", "3LT"],
    ["1lt_c67", "C67", "convertible", "1LT"],
    ["2lt_c67", "C67", "convertible", "2LT"],
    ["3lt_c67", "C67", "convertible", "3LT"],
  ].map(([variant_id, gm_model_code, body_style, trim_level]) => ({
    variant_id,
    model_year: "2027",
    gm_model_code,
    model_key: "stingray",
    body_style,
    trim_level,
    active: "true",
    notes: "Temp final variant fixture.",
  }));
  writeCsv(path.join(packageDir, "canonical", "status", "variants.csv"), FINAL_VARIANT_FIELDS, variants);
  writeCsv(path.join(packageDir, "canonical", "status", "context_scopes.csv"), FINAL_CONTEXT_SCOPE_FIELDS, [
    {
      context_scope_id: "ctx_2027_stingray",
      model_year: "2027",
      model_key: "stingray",
      variant_id: "",
      body_style: "",
      trim_level: "",
      priority: "1",
      active: "true",
      notes: "Temp model default scope.",
    },
  ]);
}

function writeJ6aCanonical(packageDir, { includeDisplayPresentation = false } = {}) {
  writeFinalContextTables(packageDir);
  writeCsv(path.join(packageDir, "canonical", "options", "canonical_options.csv"), FINAL_CANONICAL_OPTION_FIELDS, [
    {
      canonical_option_id: "canonical_j6a",
      rpo: "J6A",
      label: "Black painted calipers",
      description: "",
      canonical_kind: "customer_choice",
      duplicate_rpo_classification: includeDisplayPresentation ? "display_only_duplicate" : "none",
      active: "true",
      notes: "Temp final canonical J6A option.",
    },
  ]);
  const presentations = [
    {
      presentation_id: "pres_j6a_caliper_choice",
      canonical_option_id: "canonical_j6a",
      rpo_override: "",
      presentation_role: "customer_choice",
      choice_group_id: "cg_calipers",
      section_id: "sec_cali_001",
      section_name: "Caliper Color",
      category_id: "cat_exte_001",
      category_name: "Exterior",
      step_key: "wheels",
      selection_mode: "single_select_req",
      display_order: "10",
      selectable: "True",
      active: "true",
      label: "",
      description: "",
      source_detail_raw: "",
      notes: "Temp final customer choice presentation.",
      legacy_option_id: "opt_j6a_001",
      choice_mode: "single",
      selection_mode_label: "Required single choice",
    },
  ];
  if (includeDisplayPresentation) {
    presentations.push({
      presentation_id: "pres_j6a_standard_options",
      canonical_option_id: "canonical_j6a",
      rpo_override: "",
      presentation_role: "standard_options_display",
      choice_group_id: "",
      section_id: "sec_stan_002",
      section_name: "Standard Options",
      category_id: "cat_stan_001",
      category_name: "Standard Equipment",
      step_key: "standard_equipment",
      selection_mode: "display_only",
      display_order: "1",
      selectable: "False",
      active: "true",
      label: "Calipers",
      description: "Black painted",
      source_detail_raw: "",
      notes: "Temp final Standard Options presentation.",
      legacy_option_id: "opt_j6a_002",
      choice_mode: "display",
      selection_mode_label: "Display only",
    });
  }
  writeCsv(path.join(packageDir, "canonical", "presentation", "option_presentations.csv"), FINAL_OPTION_PRESENTATION_FIELDS, presentations);
  writeCsv(path.join(packageDir, "canonical", "status", "option_status_rules.csv"), FINAL_OPTION_STATUS_RULE_FIELDS, presentations.map((presentation) => ({
    status_rule_id: `status_${presentation.presentation_id}`,
    canonical_option_id: "",
    presentation_id: presentation.presentation_id,
    context_scope_id: "ctx_2027_stingray",
    status: presentation.presentation_role === "customer_choice" ? "standard_choice" : "standard_fixed",
    status_label: "Standard",
    priority: "10",
    active: "true",
    notes: "Temp final status fixture.",
  })));
}

function writeProjectionOwnership(packageDir, rows = []) {
  writeCsv(path.join(packageDir, "canonical", "ownership", "projection_ownership.csv"), FINAL_PROJECTION_OWNERSHIP_FIELDS, rows);
}

function writePreservedBoundaries(packageDir, rows = []) {
  writeCsv(path.join(packageDir, "canonical", "ownership", "preserved_boundaries.csv"), FINAL_PRESERVED_BOUNDARY_FIELDS, rows);
}

function j6aChoiceOwnership() {
  return {
    ownership_id: "own_pres_j6a_choice",
    entity_type: "presentation",
    entity_id: "pres_j6a_caliper_choice",
    ownership_status: "projected_owned",
    legacy_rpo: "J6A",
    legacy_option_id: "opt_j6a_001",
    notes: "Temp final presentation ownership.",
    active: "true",
  };
}

function j6aDisplayOwnership() {
  return {
    ownership_id: "own_pres_j6a_standard_options",
    entity_type: "presentation",
    entity_id: "pres_j6a_standard_options",
    ownership_status: "generated_display_owned",
    legacy_rpo: "J6A",
    legacy_option_id: "opt_j6a_002",
    notes: "Temp final display presentation ownership.",
    active: "true",
  };
}

test("absent and header-only final ownership tables preserve output and overlay behavior when no final rows are authored", () => {
  const absentPackage = tempPackage();
  fs.rmSync(path.join(absentPackage, "canonical", "ownership"), { recursive: true, force: true });

  const headerOnlyPackage = tempPackage();
  writeProjectionOwnership(headerOnlyPackage);
  writePreservedBoundaries(headerOnlyPackage);

  assert.deepEqual(emitLegacyFragment(headerOnlyPackage), emitLegacyFragment(absentPackage));
  assert.deepEqual(overlayData(headerOnlyPackage), overlayData(absentPackage));
});

test("temp canonical presentation with final presentation ownership passes projected coverage", () => {
  const packageDir = tempPackage();
  writeJ6aCanonical(packageDir);
  writeProjectionOwnership(packageDir, [j6aChoiceOwnership()]);

  const result = runOverlay(["--package", packageDir]);
  assert.equal(result.status, 0, result.stderr);
  const shadow = JSON.parse(result.stdout);
  assert.equal(shadow.choices.filter((row) => row.option_id === "opt_j6a_001").length, 6);
  assert.equal(shadow.choices.filter((row) => row.option_id === "opt_j6a_002").length, 6);
});

test("duplicate-RPO canonical option passes when both emitted presentations are owned", () => {
  const packageDir = tempPackage();
  writeJ6aCanonical(packageDir, { includeDisplayPresentation: true });
  writeProjectionOwnership(packageDir, [
    j6aChoiceOwnership(),
    j6aDisplayOwnership(),
  ]);

  const result = runOverlay(["--package", packageDir]);
  assert.equal(result.status, 0, result.stderr);
  const shadow = JSON.parse(result.stdout);
  assert.equal(shadow.choices.filter((row) => row.option_id === "opt_j6a_001").length, 6);
  assert.equal(shadow.choices.filter((row) => row.option_id === "opt_j6a_002").length, 6);
});

test("missing final presentation ownership fails clearly", () => {
  const packageDir = tempPackage();
  writeJ6aCanonical(packageDir, { includeDisplayPresentation: true });
  writeProjectionOwnership(packageDir, [j6aChoiceOwnership()]);

  const result = runOverlay(["--package", packageDir]);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Projected fragment includes choices without ownership: \['opt_j6a_002'\]/);
});

test("default final ownership coverage rejects custom fragments that omit owned presentations", () => {
  const packageDir = tempPackage();
  writeJ6aCanonical(packageDir, { includeDisplayPresentation: true });
  writeProjectionOwnership(packageDir, [
    j6aChoiceOwnership(),
    j6aDisplayOwnership(),
  ]);
  const fragment = emitLegacyFragment(packageDir);
  fragment.choices = fragment.choices.filter((row) => row.option_id !== "opt_j6a_002");
  const fragmentPath = path.join(path.dirname(packageDir), "missing-final-owned-presentation.json");
  fs.writeFileSync(fragmentPath, JSON.stringify(fragment));

  const result = runStrictOverlayWithFragment(packageDir, fragmentPath);
  assert.notEqual(result.status, 0);
  const output = `${result.stdout}\n${result.stderr}`;
  assert.match(output, /Projected fragment final presentation scope changed/);
  assert.match(output, /opt_j6a_002/);
});

test("custom fragment-json filtering is limited to explicit custom-fragment overlay tests", () => {
  const packageDir = tempPackage();
  writeJ6aCanonical(packageDir, { includeDisplayPresentation: true });
  writeProjectionOwnership(packageDir, [
    j6aChoiceOwnership(),
    j6aDisplayOwnership(),
  ]);
  const fragment = emitLegacyFragment(packageDir);
  fragment.choices = fragment.choices.filter((row) => row.option_id !== "opt_j6a_002");
  const fragmentPath = path.join(path.dirname(packageDir), "custom-fragment-missing-final-owned-presentation.json");
  fs.writeFileSync(fragmentPath, JSON.stringify(fragment));

  const result = runOverlay(["--package", packageDir, "--fragment-json", fragmentPath]);
  assert.equal(result.status, 0, result.stderr);
  const shadow = JSON.parse(result.stdout);
  assert.equal(shadow.choices.filter((row) => row.option_id === "opt_j6a_001").length, 6);
  assert.equal(shadow.choices.filter((row) => row.option_id === "opt_j6a_002").length, 6);
});

test("invalid final ownership entity refs fail clearly", () => {
  const packageDir = tempPackage();
  writeProjectionOwnership(packageDir, [
    {
      ownership_id: "own_missing_presentation",
      entity_type: "presentation",
      entity_id: "pres_missing",
      ownership_status: "projected_owned",
      legacy_rpo: "J6A",
      legacy_option_id: "opt_j6a_001",
      notes: "Invalid temp ownership.",
      active: "true",
    },
  ]);

  const result = runOverlay(["--package", packageDir]);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /references missing presentation: pres_missing/);
});

test("final relationship ownership validates against compiler-known relationship ids", () => {
  const packageDir = tempPackage();
  writeProjectionOwnership(packageDir, [
    {
      ownership_id: "own_relationship_sht_pdv",
      entity_type: "relationship",
      entity_id: "dep_excl_sht_pdv",
      ownership_status: "projected_owned",
      legacy_rpo: "",
      legacy_option_id: "",
      notes: "Temp relationship ownership validation fixture.",
      active: "true",
    },
  ]);

  const result = runOverlay(["--package", packageDir]);
  assert.equal(result.status, 0, result.stderr);
});

test("final and transitional ownership conflicts fail clearly", () => {
  const packageDir = tempPackage();
  writeCsv(path.join(packageDir, "canonical", "options", "canonical_options.csv"), FINAL_CANONICAL_OPTION_FIELDS, [
    {
      canonical_option_id: "canonical_b6p_conflict",
      rpo: "B6P",
      label: "Engine Lighting",
      description: "",
      canonical_kind: "customer_choice",
      duplicate_rpo_classification: "none",
      active: "true",
      notes: "Temp conflict fixture.",
    },
  ]);
  writeProjectionOwnership(packageDir, [
    {
      ownership_id: "own_b6p_conflict",
      entity_type: "canonical_option",
      entity_id: "canonical_b6p_conflict",
      ownership_status: "projected_owned",
      legacy_rpo: "B6P",
      legacy_option_id: "",
      notes: "Conflicts with transitional B6P ownership.",
      active: "true",
    },
  ]);

  const result = runOverlay(["--package", packageDir]);
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /conflicts with transitional projected_slice_ownership\.csv for RPOs: \['B6P'\]/);
});

test("final preserved boundary classifies a typed boundary without RPO-only matching", () => {
  const packageDir = tempPackage();
  const manifestPath = path.join(path.dirname(packageDir), "projected_slice_ownership.csv");
  const manifest = fs.readFileSync(OWNERSHIP_MANIFEST, "utf8")
    .replace("rule,,RZ9,,EFY,,,preserved_cross_boundary,RZ9 to EFY LPO Exterior boundary remains production-owned before EFY dependency migration,true",
      "rule,,RZ9,,EFY,,,preserved_cross_boundary,RZ9 to EFY LPO Exterior boundary remains production-owned before EFY dependency migration,false");
  fs.writeFileSync(manifestPath, manifest);
  writePreservedBoundaries(packageDir, [
    {
      boundary_id: "boundary_rz9_efy",
      relationship_type: "excludes",
      source_type: "legacy_option",
      source_id: "opt_rz9_001",
      target_type: "legacy_option",
      target_id: "opt_efy_001",
      legacy_source_option_id: "",
      legacy_target_option_id: "",
      reason: "Temp final typed boundary preserving RZ9 to EFY.",
      active: "true",
    },
  ]);

  const result = runOverlay(["--package", packageDir, "--ownership-manifest", manifestPath]);
  assert.equal(result.status, 0, result.stderr);
});
