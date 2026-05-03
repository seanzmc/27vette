import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = process.env.PYTHON || ".venv/bin/python";
const RECONCILE_SCRIPT = "scripts/reconcile_confident_subset_to_canonical.py";

function parseCsv(source) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let index = 0; index < source.length; index++) {
    const char = source[index];
    const next = source[index + 1];
    if (char === '"' && inQuotes && next === '"') {
      field += '"';
      index++;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") index++;
      row.push(field);
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  const [headers, ...records] = rows;
  return records.map((record) => Object.fromEntries(headers.map((header, index) => [header, record[index] || ""])));
}

function readCsv(filePath) {
  return parseCsv(fs.readFileSync(filePath, "utf8"));
}

function writeCsv(filePath, headers, rows) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const quote = (value) => {
    const text = String(value ?? "");
    if (/[",\n\r]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
    return text;
  };
  fs.writeFileSync(filePath, `${headers.join(",")}\n${rows.map((row) => headers.map((header) => quote(row[header])).join(",")).join("\n")}\n`);
}

function makeSubset(subsetDir) {
  fs.mkdirSync(subsetDir, { recursive: true });
  fs.writeFileSync(
    path.join(subsetDir, "proposal_subset_report.json"),
    JSON.stringify(
      {
        readiness: { canonical_apply_ready: false },
        confident_subset_counts: { retained_selectables: 5, retained_availability: 5 },
      },
      null,
      2,
    ),
  );
  writeCsv(
    path.join(subsetDir, "catalog", "selectables.csv"),
    [
      "proposal_selectable_id",
      "proposal_scope",
      "proposal_status",
      "source_sheet",
      "model_key",
      "section_family",
      "orderable_rpo",
      "ref_rpo",
      "proposal_label",
      "description",
      "selectable_source",
      "has_orderable_rpo",
      "has_ref_rpo",
      "review_status",
      "source_ref_ids",
      "notes",
      "proposal_filter_status",
    ],
    [
      {
        proposal_selectable_id: "prop_stingray_standard_equipment_aaa",
        proposal_scope: "primary_matrix_selectable_candidate",
        proposal_status: "proposal_only",
        source_sheet: "Standard Equipment 1",
        model_key: "stingray",
        section_family: "standard_equipment",
        orderable_rpo: "AAA",
        proposal_label: "Existing Canonical Label",
        description: "Existing canonical description",
        selectable_source: "primary_variant_matrix",
        has_orderable_rpo: "true",
        has_ref_rpo: "false",
        review_status: "proposal_only",
        source_ref_ids: "src_aaa",
        notes: "proposal only",
        proposal_filter_status: "confident_subset",
      },
      {
        proposal_selectable_id: "prop_stingray_standard_equipment_bbb",
        proposal_scope: "primary_matrix_selectable_candidate",
        proposal_status: "proposal_only",
        source_sheet: "Standard Equipment 1",
        model_key: "stingray",
        section_family: "standard_equipment",
        orderable_rpo: "BBB",
        proposal_label: "New Proposal Label",
        description: "New proposal description",
        selectable_source: "primary_variant_matrix",
        has_orderable_rpo: "true",
        has_ref_rpo: "false",
        review_status: "proposal_only",
        source_ref_ids: "src_bbb",
        notes: "proposal only",
        proposal_filter_status: "confident_subset",
      },
      {
        proposal_selectable_id: "prop_stingray_standard_equipment_ccc",
        proposal_scope: "primary_matrix_selectable_candidate",
        proposal_status: "proposal_only",
        source_sheet: "Standard Equipment 1",
        model_key: "stingray",
        section_family: "standard_equipment",
        orderable_rpo: "CCC",
        proposal_label: "Conflicting Proposal Label",
        description: "Proposal description differs",
        selectable_source: "primary_variant_matrix",
        has_orderable_rpo: "true",
        has_ref_rpo: "false",
        review_status: "proposal_only",
        source_ref_ids: "src_ccc",
        notes: "proposal only",
        proposal_filter_status: "confident_subset",
      },
      {
        proposal_selectable_id: "prop_stingray_standard_equipment_dup",
        proposal_scope: "primary_matrix_selectable_candidate",
        proposal_status: "proposal_only",
        source_sheet: "Standard Equipment 1",
        model_key: "stingray",
        section_family: "standard_equipment",
        orderable_rpo: "DUP",
        proposal_label: "Ambiguous Canonical Match",
        description: "Ambiguous",
        selectable_source: "primary_variant_matrix",
        has_orderable_rpo: "true",
        has_ref_rpo: "false",
        review_status: "proposal_only",
        source_ref_ids: "src_dup",
        notes: "proposal only",
        proposal_filter_status: "confident_subset",
      },
      {
        proposal_selectable_id: "prop_grand_sport_standard_equipment_aaa",
        proposal_scope: "primary_matrix_selectable_candidate",
        proposal_status: "proposal_only",
        source_sheet: "Standard Equipment 2",
        model_key: "grand_sport",
        section_family: "standard_equipment",
        orderable_rpo: "AAA",
        proposal_label: "Grand Sport Label",
        description: "Outside canonical model coverage",
        selectable_source: "primary_variant_matrix",
        has_orderable_rpo: "true",
        has_ref_rpo: "false",
        review_status: "proposal_only",
        source_ref_ids: "src_gs",
        notes: "proposal only",
        proposal_filter_status: "confident_subset",
      },
    ],
  );
  writeCsv(
    path.join(subsetDir, "ui", "selectable_display.csv"),
    [
      "proposal_selectable_id",
      "proposal_status",
      "model_key",
      "section_family",
      "section_name",
      "category_name",
      "display_label",
      "display_description",
      "source_description_raw",
      "source_detail_raw",
      "review_status",
      "source_ref_ids",
      "proposal_filter_status",
    ],
    [
      {
        proposal_selectable_id: "prop_stingray_standard_equipment_aaa",
        proposal_status: "proposal_only",
        model_key: "stingray",
        section_family: "standard_equipment",
        section_name: "Standard Equipment",
        category_name: "Standard",
        display_label: "Existing Canonical Label",
        display_description: "Existing canonical description",
        source_ref_ids: "src_aaa",
        review_status: "proposal_only",
        proposal_filter_status: "confident_subset",
      },
    ],
  );
  writeCsv(
    path.join(subsetDir, "ui", "availability.csv"),
    [
      "proposal_selectable_id",
      "proposal_status",
      "model_key",
      "variant_id",
      "body_code",
      "body_style",
      "trim_level",
      "orderable_rpo",
      "ref_rpo",
      "raw_status",
      "status_symbol",
      "footnote_refs",
      "canonical_status",
      "availability_value",
      "source_ref_id",
      "review_status",
      "notes",
      "proposal_filter_status",
    ],
    [
      {
        proposal_selectable_id: "prop_stingray_standard_equipment_aaa",
        proposal_status: "proposal_only",
        model_key: "stingray",
        variant_id: "1lt_c07",
        body_code: "C07",
        body_style: "coupe",
        trim_level: "1LT",
        orderable_rpo: "AAA",
        raw_status: "A/D2",
        status_symbol: "A/D",
        footnote_refs: "2",
        canonical_status: "available",
        availability_value: "available",
        source_ref_id: "src_aaa",
        review_status: "proposal_only",
        notes: "proposal only",
        proposal_filter_status: "confident_subset",
      },
      {
        proposal_selectable_id: "prop_stingray_standard_equipment_bbb",
        proposal_status: "proposal_only",
        model_key: "stingray",
        variant_id: "1lt_c07",
        body_code: "C07",
        body_style: "coupe",
        trim_level: "1LT",
        orderable_rpo: "BBB",
        raw_status: "S",
        status_symbol: "S",
        canonical_status: "standard",
        availability_value: "standard",
        source_ref_id: "src_bbb",
        review_status: "proposal_only",
        notes: "proposal only",
        proposal_filter_status: "confident_subset",
      },
    ],
  );
  writeCsv(
    path.join(subsetDir, "meta", "source_refs.csv"),
    [
      "source_ref_id",
      "source_file",
      "source_sheet",
      "source_row",
      "source_column_or_cell_range",
      "source_field",
      "raw_value",
      "raw_status",
      "orderable_rpo",
      "ref_rpo",
      "source_detail_raw",
    ],
    ["aaa", "bbb", "ccc", "dup", "gs"].map((suffix, index) => ({
      source_ref_id: `src_${suffix}`,
      source_file: "staging_variant_matrix_rows.csv",
      source_sheet: index === 4 ? "Standard Equipment 2" : "Standard Equipment 1",
      source_row: String(index + 4),
      source_column_or_cell_range: "1lt_c07",
      source_field: "variant_matrix_row",
      raw_value: suffix.toUpperCase(),
      raw_status: "A",
      orderable_rpo: suffix.toUpperCase(),
      source_detail_raw: suffix.toUpperCase(),
    })),
  );
}

function makeCanonicalRoot(canonicalRoot) {
  writeCsv(
    path.join(canonicalRoot, "catalog", "variants.csv"),
    ["variant_id", "model_key", "model_year", "body_style", "body_code", "trim_level", "label", "base_price_usd", "active"],
    [
      {
        variant_id: "1lt_c07",
        model_key: "stingray",
        model_year: "2027",
        body_style: "coupe",
        body_code: "C07",
        trim_level: "1LT",
        label: "1LT Coupe",
        base_price_usd: "73495",
        active: "true",
      },
    ],
  );
  writeCsv(
    path.join(canonicalRoot, "catalog", "selectables.csv"),
    ["selectable_id", "selectable_type", "rpo", "label", "description", "active", "availability_condition_set_id", "notes"],
    [
      {
        selectable_id: "opt_aaa_existing",
        selectable_type: "option",
        rpo: "AAA",
        label: "Existing Canonical Label",
        description: "Existing canonical description",
        active: "true",
      },
      {
        selectable_id: "opt_ccc_existing",
        selectable_type: "option",
        rpo: "CCC",
        label: "Different Canonical Label",
        description: "Different canonical description",
        active: "true",
      },
      {
        selectable_id: "opt_dup_one",
        selectable_type: "option",
        rpo: "DUP",
        label: "Ambiguous Canonical Match",
        description: "Ambiguous",
        active: "true",
      },
      {
        selectable_id: "opt_dup_two",
        selectable_type: "option",
        rpo: "DUP",
        label: "Ambiguous Canonical Match",
        description: "Ambiguous",
        active: "true",
      },
    ],
  );
  writeCsv(
    path.join(canonicalRoot, "ui", "selectable_display.csv"),
    ["selectable_id", "section_id", "section_name", "category_id", "category_name", "label", "description", "source_detail_raw"],
    [
      {
        selectable_id: "opt_aaa_existing",
        section_id: "sec_existing",
        section_name: "Existing Section",
        category_id: "cat_existing",
        category_name: "Existing Category",
        label: "Existing Canonical Label",
        description: "Existing canonical description",
      },
    ],
  );
}

function runReconcile(subsetDir, canonicalRoot, outDir) {
  execFileSync(
    PYTHON,
    [RECONCILE_SCRIPT, "--subset", subsetDir, "--canonical-root", canonicalRoot, "--out", outDir],
    { cwd: process.cwd(), encoding: "utf8" },
  );
}

test("canonical reconciliation reports matches, candidates, conflicts, and blockers without applying", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-reconcile-"));
  const subsetDir = path.join(tmpDir, "subset");
  const canonicalRoot = path.join(tmpDir, "canonical", "stingray");
  const outDir = path.join(tmpDir, "reconciliation");
  const secondOutDir = path.join(tmpDir, "reconciliation-second");
  makeSubset(subsetDir);
  makeCanonicalRoot(canonicalRoot);
  const canonicalBefore = fs.readFileSync(path.join(canonicalRoot, "catalog", "selectables.csv"), "utf8");

  runReconcile(subsetDir, canonicalRoot, outDir);
  runReconcile(subsetDir, canonicalRoot, secondOutDir);

  for (const fileName of [
    "reconciliation_report.json",
    "reconciliation_report.md",
    "matched_selectables.csv",
    "new_selectable_candidates.csv",
    "conflicting_selectables.csv",
    "unavailable_canonical_context.csv",
    "section_mapping_needs.csv",
    "availability_reconciliation.csv",
    "source_ref_member_plan.csv",
    "apply_blockers.csv",
  ]) {
    assert.ok(fs.existsSync(path.join(outDir, fileName)), `${fileName} should exist`);
    assert.equal(fs.readFileSync(path.join(outDir, fileName), "utf8"), fs.readFileSync(path.join(secondOutDir, fileName), "utf8"));
  }
  assert.equal(fs.readFileSync(path.join(canonicalRoot, "catalog", "selectables.csv"), "utf8"), canonicalBefore);

  const report = JSON.parse(fs.readFileSync(path.join(outDir, "reconciliation_report.json"), "utf8"));
  assert.equal(report.canonical_apply_ready, false);
  assert.equal(report.decision_summary.selectable_id_policy, "selectable_id_model_rpo");
  assert.equal(report.decision_summary.availability_schema_policy, "availability_selectable_variant");
  assert.equal(report.decision_summary.source_refs_policy, "source_refs_member_table");

  const matched = readCsv(path.join(outDir, "matched_selectables.csv"));
  assert.ok(matched.some((row) => row.orderable_rpo === "AAA" && row.canonical_selectable_id === "opt_aaa_existing"));
  assert.equal(matched.some((row) => row.canonical_selectable_id === "prop_stingray_standard_equipment_aaa"), false);

  const candidates = readCsv(path.join(outDir, "new_selectable_candidates.csv"));
  assert.ok(
    candidates.some(
      (row) =>
        row.orderable_rpo === "BBB" &&
        row.candidate_canonical_selectable_id_preview === "sel_stingray_bbb" &&
        row.candidate_id_status === "preview_only",
    ),
  );

  const conflicts = readCsv(path.join(outDir, "conflicting_selectables.csv"));
  assert.ok(conflicts.some((row) => row.orderable_rpo === "CCC" && row.conflict_type === "label_mismatch"));
  assert.ok(conflicts.some((row) => row.orderable_rpo === "DUP" && row.conflict_type === "ambiguous_canonical_match"));

  const unavailable = readCsv(path.join(outDir, "unavailable_canonical_context.csv"));
  assert.ok(unavailable.some((row) => row.model_key === "grand_sport" && row.reason === "model_not_covered_by_canonical_root"));

  const sectionNeeds = readCsv(path.join(outDir, "section_mapping_needs.csv"));
  assert.ok(sectionNeeds.some((row) => row.section_family === "standard_equipment" && row.required_mapping.includes("section_id")));

  const availability = readCsv(path.join(outDir, "availability_reconciliation.csv"));
  assert.ok(
    availability.some(
      (row) =>
        row.proposal_selectable_id === "prop_stingray_standard_equipment_aaa" &&
        row.reconciliation_status === "target_schema_missing" &&
        row.availability_value === "available",
    ),
  );

  const sourcePlan = readCsv(path.join(outDir, "source_ref_member_plan.csv"));
  assert.ok(sourcePlan.some((row) => row.proposal_selectable_id === "prop_stingray_standard_equipment_aaa" && row.notes.includes("plan only")));

  const blockers = readCsv(path.join(outDir, "apply_blockers.csv"));
  for (const blockerId of [
    "canonical_selectable_id_policy_not_applied",
    "missing_section_family_import_map",
    "missing_canonical_availability_schema",
    "missing_canonical_source_ref_member_schema",
    "non_stingray_model_context_unavailable",
    "ambiguous_canonical_match",
    "canonical_apply_ready_false_by_design",
  ]) {
    assert.ok(blockers.some((row) => row.blocker_id === blockerId), `${blockerId} should be reported`);
  }

  const markdown = fs.readFileSync(path.join(outDir, "reconciliation_report.md"), "utf8");
  assert.match(markdown, /reconciliation report only/);
  assert.match(markdown, /canonical_apply_ready=false/);
  assert.match(markdown, /No canonical rows were generated or applied/);

  for (const forbiddenPath of [
    "data/stingray/catalog/selectables.csv",
    "form-app/data.js",
    "form-output/stingray-form-data.json",
    "logic/dependency_rules.csv",
    "logic/auto_adds.csv",
    "pricing/price_rules.csv",
  ]) {
    assert.equal(fs.existsSync(path.join(outDir, forbiddenPath)), false, `${forbiddenPath} must not be generated`);
  }
});

test("canonical reconciliation fails clearly for missing subset input and unsafe output", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-reconcile-failures-"));
  const subsetDir = path.join(tmpDir, "subset");
  const canonicalRoot = path.join(tmpDir, "canonical", "stingray");
  makeSubset(subsetDir);
  makeCanonicalRoot(canonicalRoot);
  fs.rmSync(path.join(subsetDir, "ui", "availability.csv"));

  assert.throws(
    () => runReconcile(subsetDir, canonicalRoot, path.join(tmpDir, "reconciliation")),
    /Missing required confident subset input/,
  );
  assert.throws(
    () => runReconcile(subsetDir, canonicalRoot, path.join(process.cwd(), "data", "stingray", "reconciliation")),
    /Refusing to write canonical reconciliation output/,
  );
});
