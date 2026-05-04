import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = process.env.PYTHON || ".venv/bin/python";
const TRIAGE_SCRIPT = "scripts/triage_order_guide_reconciliation.py";

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

function makeReconciliation(dir) {
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(
    path.join(dir, "reconciliation_report.json"),
    JSON.stringify(
      {
        canonical_apply_ready: false,
        match_counts: {
          matched_selectables: 3,
          new_selectable_candidates: 3,
          conflicting_selectables: 5,
          unavailable_canonical_context_rows: 1,
        },
        apply_blockers: { total: 6 },
      },
      null,
      2,
    ),
  );
  fs.writeFileSync(path.join(dir, "reconciliation_report.md"), "# Reconciliation\n");
  writeCsv(
    path.join(dir, "matched_selectables.csv"),
    [
      "proposal_selectable_id",
      "model_key",
      "orderable_rpo",
      "canonical_selectable_id",
      "match_confidence",
      "match_reasons",
      "label_match_status",
      "description_match_status",
      "notes",
    ],
    [
      {
        proposal_selectable_id: "prop_strong",
        model_key: "stingray",
        orderable_rpo: "AAA",
        canonical_selectable_id: "opt_aaa",
        match_confidence: "high",
        match_reasons: "model_context_and_rpo_match",
        label_match_status: "exact_match",
        description_match_status: "exact_match",
      },
      {
        proposal_selectable_id: "prop_label_review",
        model_key: "stingray",
        orderable_rpo: "BBB",
        canonical_selectable_id: "opt_bbb",
        match_confidence: "medium",
        match_reasons: "model_context_and_rpo_match",
        label_match_status: "mismatch",
        description_match_status: "exact_match",
      },
      {
        proposal_selectable_id: "prop_desc_review",
        model_key: "stingray",
        orderable_rpo: "CCC",
        canonical_selectable_id: "opt_ccc",
        match_confidence: "medium",
        match_reasons: "model_context_and_rpo_match",
        label_match_status: "exact_match",
        description_match_status: "mismatch",
      },
    ],
  );
  writeCsv(
    path.join(dir, "new_selectable_candidates.csv"),
    [
      "proposal_selectable_id",
      "model_key",
      "orderable_rpo",
      "candidate_canonical_selectable_id_preview",
      "candidate_id_status",
      "proposal_label",
      "description",
      "source_ref_count",
      "notes",
    ],
    [
      {
        proposal_selectable_id: "prop_new_clean",
        model_key: "stingray",
        orderable_rpo: "DDD",
        candidate_canonical_selectable_id_preview: "sel_stingray_ddd",
        candidate_id_status: "preview_only",
        proposal_label: "New Clean",
        description: "Clean description",
        source_ref_count: "2",
      },
      {
        proposal_selectable_id: "prop_new_no_source",
        model_key: "stingray",
        orderable_rpo: "EEE",
        candidate_canonical_selectable_id_preview: "sel_stingray_eee",
        candidate_id_status: "preview_only",
        proposal_label: "No Source",
        description: "No source description",
        source_ref_count: "0",
      },
      {
        proposal_selectable_id: "prop_new_no_label",
        model_key: "stingray",
        orderable_rpo: "FFF",
        candidate_canonical_selectable_id_preview: "sel_stingray_fff",
        candidate_id_status: "preview_only",
        proposal_label: "",
        description: "Needs label",
        source_ref_count: "1",
      },
    ],
  );
  writeCsv(
    path.join(dir, "conflicting_selectables.csv"),
    [
      "proposal_selectable_id",
      "model_key",
      "orderable_rpo",
      "canonical_selectable_id",
      "conflict_type",
      "proposal_value",
      "canonical_value",
      "recommended_action",
    ],
    [
      {
        proposal_selectable_id: "prop_combo",
        model_key: "stingray",
        orderable_rpo: "GGG",
        canonical_selectable_id: "opt_ggg",
        conflict_type: "label_mismatch",
        proposal_value: "Proposal Label",
        canonical_value: "Canonical Label",
        recommended_action: "Review label",
      },
      {
        proposal_selectable_id: "prop_combo",
        model_key: "stingray",
        orderable_rpo: "GGG",
        canonical_selectable_id: "opt_ggg",
        conflict_type: "description_mismatch",
        proposal_value: "Proposal Description",
        canonical_value: "Canonical Description",
        recommended_action: "Review description",
      },
      {
        proposal_selectable_id: "prop_label_only",
        model_key: "stingray",
        orderable_rpo: "HHH",
        canonical_selectable_id: "opt_hhh",
        conflict_type: "label_mismatch",
        proposal_value: "Proposal",
        canonical_value: "Canonical",
        recommended_action: "Review label",
      },
      {
        proposal_selectable_id: "prop_desc_only",
        model_key: "stingray",
        orderable_rpo: "III",
        canonical_selectable_id: "opt_iii",
        conflict_type: "description_mismatch",
        proposal_value: "Proposal",
        canonical_value: "Canonical",
        recommended_action: "Review description",
      },
      {
        proposal_selectable_id: "prop_ambiguous",
        model_key: "stingray",
        orderable_rpo: "DUP",
        canonical_selectable_id: "opt_dup_one|opt_dup_two",
        conflict_type: "ambiguous_canonical_match",
        proposal_value: "Ambiguous",
        canonical_value: "Ambiguous",
        recommended_action: "Resolve ambiguous match",
      },
    ],
  );
  writeCsv(
    path.join(dir, "unavailable_canonical_context.csv"),
    ["model_key", "reason", "affected_row_count", "notes"],
    [{ model_key: "grand_sport", reason: "model_not_covered_by_canonical_root", affected_row_count: "2", notes: "Outside Stingray" }],
  );
  writeCsv(
    path.join(dir, "section_mapping_needs.csv"),
    ["section_family", "model_key", "affected_selectable_count", "required_mapping", "recommended_action"],
    [
      {
        section_family: "standard_equipment",
        model_key: "stingray",
        affected_selectable_count: "6",
        required_mapping: "section_family -> section_id/step_id/category_id",
        recommended_action: "Create explicit section import map",
      },
    ],
  );
  writeCsv(
    path.join(dir, "availability_reconciliation.csv"),
    [
      "proposal_selectable_id",
      "model_key",
      "variant_id",
      "orderable_rpo",
      "availability_value",
      "canonical_availability_status",
      "reconciliation_status",
      "notes",
    ],
    [
      {
        proposal_selectable_id: "prop_strong",
        model_key: "stingray",
        variant_id: "1lt_c07",
        orderable_rpo: "AAA",
        availability_value: "available",
        reconciliation_status: "target_schema_missing",
      },
      {
        proposal_selectable_id: "prop_gs",
        model_key: "grand_sport",
        variant_id: "gs_1lt",
        orderable_rpo: "AAA",
        availability_value: "standard",
        reconciliation_status: "model_context_unavailable",
      },
    ],
  );
  writeCsv(
    path.join(dir, "source_ref_member_plan.csv"),
    [
      "proposal_selectable_id",
      "proposed_target_table",
      "proposed_target_row_key",
      "source_ref_id",
      "source_sheet",
      "source_row",
      "notes",
    ],
    [
      {
        proposal_selectable_id: "prop_strong",
        proposed_target_table: "catalog/selectables.csv",
        proposed_target_row_key: "opt_aaa",
        source_ref_id: "src_aaa",
        source_sheet: "Standard Equipment 1",
        source_row: "4",
        notes: "plan only",
      },
      {
        proposal_selectable_id: "prop_new_clean",
        proposed_target_table: "catalog/selectables.csv",
        proposed_target_row_key: "sel_stingray_ddd",
        source_ref_id: "src_ddd",
        source_sheet: "Standard Equipment 1",
        source_row: "5",
        notes: "plan only",
      },
      {
        proposal_selectable_id: "prop_grand_sport_standard_equipment_aaa",
        proposed_target_table: "catalog/selectables.csv",
        proposed_target_row_key: "sel_grand_sport_aaa",
        source_ref_id: "src_gs",
        source_sheet: "Standard Equipment 2",
        source_row: "4",
        notes: "plan only",
      },
    ],
  );
  writeCsv(
    path.join(dir, "apply_blockers.csv"),
    [
      "blocker_id",
      "blocker_type",
      "severity",
      "affected_domain",
      "affected_count",
      "required_decision_or_action",
      "notes",
    ],
    [
      {
        blocker_id: "canonical_selectable_id_policy_not_applied",
        blocker_type: "apply_blocker",
        severity: "apply_blocker",
        affected_domain: "selectables",
        affected_count: "",
        required_decision_or_action: "Apply policy later",
      },
      {
        blocker_id: "missing_section_family_import_map",
        blocker_type: "mapping_needed",
        severity: "apply_blocker",
        affected_domain: "ui",
        affected_count: "6",
        required_decision_or_action: "Create map later",
      },
      {
        blocker_id: "missing_canonical_availability_schema",
        blocker_type: "schema_context_missing",
        severity: "apply_blocker",
        affected_domain: "availability",
        affected_count: "2",
        required_decision_or_action: "Create schema later",
      },
      {
        blocker_id: "missing_canonical_source_ref_member_schema",
        blocker_type: "schema_context_missing",
        severity: "apply_blocker",
        affected_domain: "source_refs",
        affected_count: "3",
        required_decision_or_action: "Create schema later",
      },
      {
        blocker_id: "non_stingray_model_context_unavailable",
        blocker_type: "schema_context_missing",
        severity: "apply_blocker",
        affected_domain: "model_context",
        affected_count: "2",
        required_decision_or_action: "Add context later",
      },
      {
        blocker_id: "canonical_apply_ready_false_by_design",
        blocker_type: "apply_blocker",
        severity: "apply_blocker",
        affected_domain: "all",
        affected_count: "",
        required_decision_or_action: "Separate apply pass required",
      },
    ],
  );
}

function runTriage(reconciliationDir, outDir) {
  execFileSync(PYTHON, [TRIAGE_SCRIPT, "--reconciliation", reconciliationDir, "--out", outDir], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
}

test("reconciliation triage classifies review buckets without creating apply artifacts", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-reconciliation-triage-"));
  const reconciliationDir = path.join(tmpDir, "reconciliation");
  const outDir = path.join(reconciliationDir, "triage");
  const secondOutDir = path.join(tmpDir, "triage-second");
  makeReconciliation(reconciliationDir);
  const reconciliationBefore = fs.readFileSync(path.join(reconciliationDir, "reconciliation_report.json"), "utf8");

  runTriage(reconciliationDir, outDir);
  runTriage(reconciliationDir, secondOutDir);

  for (const fileName of [
    "reconciliation_triage_report.json",
    "reconciliation_triage_report.md",
    "matched_selectables_review.csv",
    "new_candidates_review.csv",
    "conflicts_review.csv",
    "apply_blockers_review.csv",
    "section_mapping_requirements.csv",
    "availability_triage_summary.csv",
    "source_ref_plan_summary.csv",
  ]) {
    assert.ok(fs.existsSync(path.join(outDir, fileName)), `${fileName} should exist`);
    assert.equal(fs.readFileSync(path.join(outDir, fileName), "utf8"), fs.readFileSync(path.join(secondOutDir, fileName), "utf8"));
  }
  assert.equal(fs.readFileSync(path.join(reconciliationDir, "reconciliation_report.json"), "utf8"), reconciliationBefore);

  const report = JSON.parse(fs.readFileSync(path.join(outDir, "reconciliation_triage_report.json"), "utf8"));
  assert.equal(report.canonical_apply_ready, false);
  assert.equal(report.triage_ready_for_apply_plan, false);
  assert.equal(report.optional_input_presence.schema_decisions_csv, true);
  assert.equal(report.conflict_bucket_counts.label_and_description_conflict, 2);
  assert.equal(report.conflict_bucket_counts.label_only_conflict, 1);
  assert.equal(report.conflict_bucket_counts.description_only_conflict, 1);
  assert.equal(report.conflict_bucket_counts.ambiguous_canonical_match, 1);

  const conflicts = readCsv(path.join(outDir, "conflicts_review.csv"));
  assert.ok(conflicts.some((row) => row.proposal_selectable_id === "prop_combo" && row.original_conflict_type === "label_mismatch" && row.conflict_bucket === "label_and_description_conflict"));
  assert.ok(conflicts.some((row) => row.conflict_bucket === "ambiguous_canonical_match" && row.triage_status === "blocked"));

  const candidates = readCsv(path.join(outDir, "new_candidates_review.csv"));
  assert.ok(candidates.some((row) => row.proposal_selectable_id === "prop_new_clean" && row.candidate_bucket === "clean_new_candidate" && row.triage_status === "candidate_for_future_apply_plan"));
  assert.ok(candidates.some((row) => row.proposal_selectable_id === "prop_new_no_source" && row.candidate_bucket === "missing_source_refs"));
  assert.ok(candidates.some((row) => row.proposal_selectable_id === "prop_new_no_label" && row.candidate_bucket === "needs_label_review"));

  const matched = readCsv(path.join(outDir, "matched_selectables_review.csv"));
  assert.ok(matched.some((row) => row.proposal_selectable_id === "prop_strong" && row.review_bucket === "strong_match"));
  assert.ok(matched.some((row) => row.proposal_selectable_id === "prop_label_review" && row.review_bucket === "label_review_needed"));

  const sections = readCsv(path.join(outDir, "section_mapping_requirements.csv"));
  assert.ok(sections.some((row) => row.section_family === "standard_equipment" && row.suggested_config_file === "data/import_maps/corvette_2027/section_family_map.csv"));
  assert.equal(fs.existsSync(path.join(outDir, "data", "import_maps", "corvette_2027", "section_family_map.csv")), false);

  const blockers = readCsv(path.join(outDir, "apply_blockers_review.csv"));
  assert.ok(blockers.some((row) => row.blocker_id === "missing_section_family_import_map" && row.blocker_bucket === "mapping_needed"));
  assert.ok(blockers.some((row) => row.blocker_id === "canonical_apply_ready_false_by_design" && row.blocker_bucket === "design_boundary"));

  const availability = readCsv(path.join(outDir, "availability_triage_summary.csv"));
  assert.ok(availability.some((row) => row.reconciliation_status === "target_schema_missing" && row.affected_row_count === "1"));

  const sourceRefs = readCsv(path.join(outDir, "source_ref_plan_summary.csv"));
  assert.ok(sourceRefs.some((row) => row.target_status === "matched_canonical_target" && row.planned_member_count === "1"));
  assert.ok(sourceRefs.some((row) => row.model_key_confidence === "inferred_from_proposal_id"));

  const markdown = fs.readFileSync(path.join(outDir, "reconciliation_triage_report.md"), "utf8");
  assert.match(markdown, /generated triage only, not apply/);
  assert.match(markdown, /canonical_apply_ready=false/);
  assert.match(markdown, /No canonical rows were generated or applied/);
  assert.match(markdown, /No section map was created/);

  for (const forbiddenPath of [
    "data/stingray/catalog/selectables.csv",
    "data/import_maps/corvette_2027/section_family_map.csv",
    "form-app/data.js",
    "form-output/stingray-form-data.json",
    "logic/dependency_rules.csv",
    "logic/auto_adds.csv",
    "pricing/price_rules.csv",
  ]) {
    assert.equal(fs.existsSync(path.join(outDir, forbiddenPath)), false, `${forbiddenPath} must not be generated`);
  }
});

test("reconciliation triage fails clearly for missing inputs and unsafe output", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-reconciliation-triage-failures-"));
  const reconciliationDir = path.join(tmpDir, "reconciliation");
  makeReconciliation(reconciliationDir);
  fs.rmSync(path.join(reconciliationDir, "apply_blockers.csv"));

  assert.throws(
    () => runTriage(reconciliationDir, path.join(tmpDir, "triage")),
    /Missing required reconciliation input/,
  );
  assert.throws(
    () => runTriage(reconciliationDir, path.join(process.cwd(), "data", "corvette", "triage")),
    /Refusing to write reconciliation triage output/,
  );
});
