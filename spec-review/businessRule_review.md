# Review of Coded Rules Findings

## Important current context:

- The findings are broadly valid.
- Some are architectural/config hardcodes, not immediate data-integrity defects.
- The highest risk issues are where code can silently change availability, pricing, included options, defaults, or submitted/exported order content outside workbook governance.
- Current repo has uncommitted paint-image pass changes from prior work.

### Inspection basis:

- Reviewed current:
  - scripts/corvette_form_generator/model_configs.py
  - scripts/corvette_form_generator/mapping.py
  - scripts/generate_stingray_form.py
  - scripts/corvette_form_generator/inspection.py
  - scripts/build_grand_sport_rule_sources.py
  - form-app/app.js
  - workbook headers for key sheets

  No validation gates run for this review because this is a planning/spec task.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 1. Validity and Risk Ranking

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Ranking criterion: risk to data integrity first. “Data integrity” here means the generated order form, selected RPOs, prices, availability, included/auto-added items, exported build, or dealer payload can disagree with workbook source truth.

Rank: 1

    Finding: Runtime hardcoded RPO conflicts/replacements/defaults
    Validity: Valid
    Data integrity risk: Critical
    Reason: Can delete/add selected RPOs independently of workbook rules. Directly affects selected build state and exports.
      Current examples: FE1/FE2/Z51, NGA/NWI, GBA/ZYC, default FE1, NGA, 719.
    ────────────────────────────────────────

Rank: 2
Finding: Runtime R6X/D30 price waiver
Validity: Valid
Data integrity risk: Critical
Reason: Can alter customer price outside workbook price rules. Current interiorComponentPrice() zeroes R6X when opt_d30_001
is auto-added.
────────────────────────────────────────
Rank: 3
Finding: Hardcoded UQT availability for Stingray 1LT only
Validity: Valid
Data integrity risk: High
Reason: Generator overrides workbook availability/status for one option/trim rule. Current code mutates
status/selectable/active for opt_uqt_002.
────────────────────────────────────────
Rank: 4
Finding: R6X included-option fallback and generated manual rule
Validity: Valid
Data integrity risk: High
Reason: Generator creates includes rules from hardcoded fallback instead of canonical workbook rule rows. Affects
auto-added RPOs and exported selected/auto-added state.
────────────────────────────────────────
Rank: 5
Finding: Interior component RPO decomposition and labels
Validity: Valid
Data integrity risk: High
Reason: Generated interior price/component lines can be wrong if token parsing or hardcoded component mapping drifts.
Affects order line items and prices.
────────────────────────────────────────
Rank: 6
Finding: Standard-equipment dedupe preference around \_001 / sec_stan_002
Validity: Valid
Data integrity risk: Medium-High
Reason: Can select the wrong canonical standard-equipment row when duplicate RPO rows exist. Impacts summary/export
content.
────────────────────────────────────────
Rank: 7
Finding: Grand Sport interior trim scope and Z25 derivation
Validity: Valid
Data integrity risk: Medium-High
Reason: Grand Sport active interior scope is partially inferred from hardcoded trim set and rule-derived Z25. Affects draft
data and future live output.
────────────────────────────────────────
Rank: 8
Finding: Hardcoded hidden section behavior for sec_cust_002
Validity: Valid
Data integrity risk: Medium
Reason: Suppresses source rows outside workbook schema. If a section becomes active, generated data may silently omit it.
────────────────────────────────────────
Rank: 9
Finding: Runtime order-summary grouping
Validity: Valid
Data integrity risk: Medium
Reason: Does not usually change selected data, but can misclassify exported/submitted line items by section.
────────────────────────────────────────
Rank: 10
Finding: Hardcoded synthetic body/trim context sections
Validity: Valid
Data integrity risk: Medium
Reason: Context choices are required build dimensions. Hardcoding section metadata risks generated contract drift.
────────────────────────────────────────
Rank: 11
Finding: Step order, labels, section-to-step mapping
Validity: Valid
Data integrity risk: Medium
Reason: section_master.step_key already absorbs much, but hardcoded fallback/step order can route sections incorrectly.
────────────────────────────────────────
Rank: 12
Finding: Standard-equipment section bucket
Validity: Valid
Data integrity risk: Medium
Reason: Affects whether rows are selectable choices or standard-equipment output.
────────────────────────────────────────
Rank: 13
Finding: Stingray section display-order overrides
Validity: Valid
Data integrity risk: Low-Medium
Reason: Primarily presentation, but bad ordering can hide/mislead option workflow.
────────────────────────────────────────
Rank: 14
Finding: Body-style ordering
Validity: Valid
Data integrity risk: Low-Medium
Reason: Presentation/context ordering. Low direct data risk.
────────────────────────────────────────
Rank: 15
Finding: Grand Sport section label overrides
Validity: Valid
Data integrity risk: Low-Medium
Reason: Customer-facing label integrity. Low direct order-data risk.
────────────────────────────────────────
Rank: 16
Finding: Model-to-sheet and variant-id mapping
Validity: Valid, but architectural
Data integrity risk: Low-Medium
Reason: Static model config is acceptable short-term, but workbook-owned model activation would reduce drift.
────────────────────────────────────────
Rank: 17
Finding: Rule-text phrase mapping in Grand Sport audit parser
Validity: Valid
Data integrity risk: Low-Medium
Reason: Risk depends on whether parser output mutates workbook. Currently mostly audit/source-building support.
────────────────────────────────────────
Rank: 18
Finding: Engine-cover RPO audit group
Validity: Valid
Data integrity risk: Low
Reason: Audit grouping only unless used to generate source rows.
────────────────────────────────────────
Rank: 19
Finding: Special review RPOs
Validity: Valid
Data integrity risk: Low
Reason: Review/audit targeting, not runtime data.
────────────────────────────────────────
Rank: 20
Finding: Trim-equipment grouping by section-name regex
Validity: Valid
Data integrity risk: Low
Reason: Presentation grouping; low direct data risk but should move to workbook metadata.

Invalid findings: - None are outright invalid. - Caveat: generated form-app/data.js should not be treated as a source of truth. It may contain hardcoded-looking values because it is generated output. Fix source workbook/generator, not generated data directly.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 2. Recommended Migration Strategy

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use a compatibility-first migration:

    1. Add workbook-owned tables/columns.
    2. Add generator readers with fallback to current behavior.
    3. Populate workbook rows matching existing output.
    4. Add parity tests proving generated output is unchanged.
    5. Flip code paths from hardcoded constants to workbook data.
    6. Remove hardcoded fallbacks only after parity passes.
    7. Deploy generated static app atomically.

    Zero-downtime principle:
    - Existing static deployment remains live while workbook/generator migration occurs locally.
    - The runtime must accept both old and new generated contracts during transition.
    - Deploy only after generated app data passes parity tests.
    - Rollback is git revert + redeploy previous form-app/data.js/runtime bundle.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 3. Phase 0 — Safety Baseline

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Risk: Low
    Purpose: prevent mixing migrations with current dirty state.

    Steps:
    1. Commit or stash current paint-image pass.
    2. Confirm clean tree:
       sh
       git status --short

    3. Confirm workbook not open:
       sh
       test ! -e './~$stingray_master.xlsx'

    4. Run baseline gates:
       sh
       .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
       .venv/bin/python scripts/generate_stingray_form.py
       .venv/bin/python scripts/generate_grand_sport_form.py
       node --test tests/stingray-form-regression.test.mjs
       node --test tests/multi-model-runtime-switching.test.mjs
       node --test tests/stingray-generator-stability.test.mjs
       node --test tests/grand-sport-contract-preview.test.mjs
       node --test tests/grand-sport-draft-data.test.mjs
       node --test tests/grand-sport-rule-audit.test.mjs


    Rollback:
    - No data changes. If baseline fails, stop and fix current branch before migration.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 4. Phase 1 — Add Workbook Metadata Tables

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Risk: Low
    Purpose: add source tables without changing generated output yet.

    New workbook source sheets:

    | Sheet                      | Purpose                                                   |
    |----------------------------|-----------------------------------------------------------|
    | runtime_steps              | Step order/labels/source of runtime navigation.           |
    | context_section_master     | Body/trim synthetic section metadata.                     |
    | section_presentation       | Section buckets, labels, display behavior, grouping.      |
    | model_master               | Model registry metadata.                                  |
    | model_workbook_sources     | Model-specific sheet names/roles.                         |
    | model_variants             | Active variant set per model.                             |
    | variant_option_overrides   | Variant-scoped selectable/display/active overrides.       |
    | default_selection_rules    | Workbook-owned defaults currently in JS.                  |
    | runtime_rule_exceptions    | Transitional suppress/replace exceptions currently in JS. |
    | interior_components        | Component decomposition for interiors.                    |
    | component_price_rules      | Component-level price overrides, including R6X/D30.       |
    | standard_equipment_groups  | Trim-equipment grouping metadata.                         |
    | order_summary_sections     | Export/summary section labels/order.                      |
    | step_order_summary_map     | Step-to-summary-section mapping.                          |
    | rule_phrase_map            | Grand Sport parser phrase mapping.                        |
    | option_audit_groups        | Audit grouping metadata.                                  |
    | option_audit_group_members | Audit group members.                                      |
    | rule_review_groups         | RPOs requiring special review.                            |

    Production-ready migration script:

    python
    #!/usr/bin/env python3
    """Add workbook-owned runtime/business-rule metadata sheets.

    Idempotent: preserves existing rows and only creates missing sheets/headers.
    """

    from future import annotations

    from pathlib import Path

    from openpyxl import load_workbook

    from corvette_form_generator.workbook import (
        rows_from_sheet,
        save_workbook_safely,
        write_sheet,
    )

    WORKBOOK_PATH = Path("stingray_master.xlsx")

    SHEETS: dict[str, list[str]] = {
        "runtime_steps": [
            "model_key",
            "step_key",
            "step_label",
            "runtime_order",
            "source",
            "active",
            "notes",
        ],
        "context_section_master": [
            "model_key",
            "context_type",
            "section_id",
            "section_name",
            "selection_mode",
            "choice_mode",
            "is_required",
            "standard_behavior",
            "section_display_order",
            "step_key",
            "step_label",
            "active",
            "notes",
        ],
        "section_presentation": [
            "model_key",
            "section_id",
            "display_label",
            "step_key",
            "presentation_bucket",
            "display_behavior",
            "section_display_order",
            "standard_equipment_bucket",
            "standard_equipment_group_type",
            "active",
            "notes",
        ],
        "model_master": [
            "model_key",
            "registry_key",
            "model_label",
            "model_year",
            "dataset_name",
            "export_slug",
            "expected_variant_count",
            "default_model",
            "active",
            "notes",
        ],
        "model_workbook_sources": [
            "model_key",
            "source_role",
            "sheet_name",
            "active",
            "notes",
        ],
        "model_variants": [
            "model_key",
            "variant_id",
            "display_order",
            "active",
            "notes",
        ],
        "variant_option_overrides": [
            "model_key",
            "option_id",
            "variant_id",
            "status",
            "selectable",
            "active",
            "display_behavior",
            "notes",
        ],
        "default_selection_rules": [
            "model_key",
            "rule_id",
            "target_option_id",
            "condition_type",
            "condition_id",
            "body_style_scope",
            "trim_level_scope",
            "variant_scope",
            "priority",
            "active",
            "notes",
        ],
        "runtime_rule_exceptions": [
            "model_key",
            "exception_id",
            "source_option_id",
            "target_option_id",
            "exception_type",
            "body_style_scope",
            "trim_level_scope",
            "variant_scope",
            "disabled_reason",
            "active",
            "notes",
        ],
        "interior_components": [
            "model_key",
            "interior_id",
            "rpo",
            "component_type",
            "label",
            "price_ref_type",
            "price_ref_code",
            "price_trim_scope",
            "display_order",
            "active",
            "notes",
        ],
        "component_price_rules": [
            "model_key",
            "price_rule_id",
            "condition_option_id",
            "target_component_rpo",
            "price_rule_type",
            "price_value",
            "body_style_scope",
            "trim_level_scope",
            "variant_scope",
            "active",
            "notes",
        ],
        "standard_equipment_groups": [
            "model_key",
            "section_id",
            "group_type",
            "default_open",
            "canonical_rank",
            "duplicate_group_key",
            "active",
            "notes",
        ],
        "order_summary_sections": [
            "model_key",
            "section_key",
            "section_label",
            "display_order",
            "active",
            "notes",
        ],
        "step_order_summary_map": [
            "model_key",
            "step_key",
            "section_key",
            "active",
            "notes",
        ],
        "rule_phrase_map": [
            "phrase",
            "rule_type",
            "direction",
            "stop_phrases",
            "review_flag_default",
            "active",
            "notes",
        ],
        "option_audit_groups": [
            "group_id",
            "group_label",
            "active",
            "notes",
        ],
        "option_audit_group_members": [
            "group_id",
            "rpo",
            "option_id",
            "active",
            "notes",
        ],
        "rule_review_groups": [
            "model_key",
            "group_id",
            "rpo",
            "review_reason",
            "active",
            "notes",
        ],
    }


    def main() -> None:
        if Path("~$stingray_master.xlsx").exists():
            raise SystemExit("Excel lock file exists; close workbook first.")

        loaded_mtime_ns = WORKBOOK_PATH.stat().st_mtime_ns
        wb = load_workbook(WORKBOOK_PATH)

        for sheet_name, headers in SHEETS.items():
            if sheet_name in wb.sheetnames:
                rows = rows_from_sheet(wb, sheet_name)
            else:
                rows = []
            write_sheet(wb, sheet_name, headers, rows)

        backup = save_workbook_safely(
            wb,
            WORKBOOK_PATH,
            loaded_mtime_ns=loaded_mtime_ns,
        )
        print(f"metadata sheets verified; backup={backup}")


    if name == "main":
        main()


    Rollback:
    1. Restore workbook backup produced by save_workbook_safely().
    2. Or remove new sheets in a revert migration if no downstream code uses them yet.
    3. Git revert migration script/tests.

    Validation:
    sh
    PYTHONPATH=scripts .venv/bin/python scripts/migrations/add_business_rule_tables.py
    .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx


    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 5. Phase 2 — Shared Workbook Metadata Loader

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Risk: Low-Medium
    Purpose: centralize workbook metadata reads and preserve fallbacks.

    Create:
    - scripts/corvette_form_generator/runtime_metadata.py

    Production-ready implementation:

    python
    """Workbook-owned runtime/business metadata loaders."""

    from future import annotations

    from collections import defaultdict
    from typing import Any, Iterable

    from corvette_form_generator.workbook import clean, intish, rows_from_sheet


    def truthy(value: Any, default: bool = False) -> bool:
        text = clean(value).lower()
        if not text:
            return default
        return text in {"true", "yes", "1", "y"}


    def optional_rows(wb, sheet_name: str) -> list[dict[str, str]]:
        if sheet_name not in wb.sheetnames:
            return []
        return rows_from_sheet(wb, sheet_name)


    def active_rows(
        wb,
        sheet_name: str,
        *,
        model_key: str | None = None,
    ) -> list[dict[str, str]]:
        rows = []
        for row in optional_rows(wb, sheet_name):
            if not truthy(row.get("active", "True"), default=True):
                continue
            if model_key is not None:
                row_model = clean(row.get("model_key"))
                if row_model not in {"*", model_key}:
                    continue
            rows.append(row)
        return rows


    def load_runtime_steps(
        wb,
        model_key: str,
        fallback_order: Iterable[str],
        fallback_labels: dict[str, str],
    ) -> list[dict[str, Any]]:
        rows = active_rows(wb, "runtime_steps", model_key=model_key)
        if rows:
            return sorted(
                [
                    {
                        "step_key": clean(row["step_key"]),
                        "step_label": clean(row.get("step_label")),
                        "runtime_order": intish(row.get("runtime_order")),
                        "source": clean(row.get("source")) or "workbook",
                        "section_ids": "",
                    }
                    for row in rows
                    if clean(row.get("step_key"))
                ],
                key=lambda row: row["runtime_order"],
            )

        return [
            {
                "step_key": step_key,
                "step_label": fallback_labels[step_key],
                "runtime_order": idx + 1,
                "source": "fallback_config",
                "section_ids": "",
            }
            for idx, step_key in enumerate(fallback_order)
        ]


    def load_context_sections(
        wb,
        model_key: str,
        fallback_sections: Iterable[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rows = active_rows(wb, "context_section_master", model_key=model_key)
        if not rows:
            return [dict(row) for row in fallback_sections]

        return sorted(
            [
                {
                    "section_id": clean(row["section_id"]),
                    "section_name": clean(row["section_name"]),
                    "selection_mode": clean(row["selection_mode"]),
                    "selection_mode_label": clean(row.get("selection_mode_label")),
                    "choice_mode": clean(row.get("choice_mode")),
                    "is_required": clean(row.get("is_required")),
                    "standard_behavior": clean(row.get("standard_behavior")),
                    "section_display_order": intish(row.get("section_display_order")),
                    "step_key": clean(row["step_key"]),
                    "step_label": clean(row.get("step_label")),
                }
                for row in rows
                if clean(row.get("section_id"))
            ],
            key=lambda row: row["section_display_order"],
        )


    def load_section_presentation(wb, model_key: str) -> dict[str, dict[str, str]]:
        rows = active_rows(wb, "section_presentation", model_key=model_key)
        return {
            clean(row["section_id"]): row
            for row in rows
            if clean(row.get("section_id"))
        }


    def load_variant_option_overrides(
        wb,
        model_key: str,
        fallback_sheet: str = "",
    ) -> dict[tuple[str, str], dict[str, str]]:
        rows = active_rows(wb, "variant_option_overrides", model_key=model_key)
        if not rows and fallback_sheet:
            rows = active_rows(wb, fallback_sheet, model_key=None)

        out: dict[tuple[str, str], dict[str, str]] = {}
        for row in rows:
            option_id = clean(row.get("option_id"))
            variant_id = clean(row.get("variant_id"))
            if option_id and variant_id:
                out[(option_id, variant_id)] = row
        return out


    def load_default_selection_rules(wb, model_key: str) -> list[dict[str, Any]]:
        rows = active_rows(wb, "default_selection_rules", model_key=model_key)
        return sorted(
            [
                {
                    "rule_id": clean(row["rule_id"]),
                    "target_option_id": clean(row["target_option_id"]),
                    "condition_type": clean(row.get("condition_type")),
                    "condition_id": clean(row.get("condition_id")),
                    "body_style_scope": clean(row.get("body_style_scope")),
                    "trim_level_scope": clean(row.get("trim_level_scope")),
                    "variant_scope": clean(row.get("variant_scope")),
                    "priority": intish(row.get("priority")),
                }
                for row in rows
                if clean(row.get("rule_id")) and clean(row.get("target_option_id"))
            ],
            key=lambda row: row["priority"],
        )


    def load_runtime_rule_exceptions(wb, model_key: str) -> list[dict[str, str]]:
        return [
            {
                "exception_id": clean(row["exception_id"]),
                "source_option_id": clean(row.get("source_option_id")),
                "target_option_id": clean(row.get("target_option_id")),
                "exception_type": clean(row.get("exception_type")),
                "body_style_scope": clean(row.get("body_style_scope")),
                "trim_level_scope": clean(row.get("trim_level_scope")),
                "variant_scope": clean(row.get("variant_scope")),
                "disabled_reason": clean(row.get("disabled_reason")),
            }
            for row in active_rows(wb, "runtime_rule_exceptions", model_key=model_key)
            if clean(row.get("exception_id"))
        ]


    def load_order_summary_metadata(wb, model_key: str) -> dict[str, Any]:
        sections = [
            {
                "section_key": clean(row["section_key"]),
                "section_label": clean(row["section_label"]),
                "display_order": intish(row.get("display_order")),
            }
            for row in active_rows(wb, "order_summary_sections", model_key=model_key)
            if clean(row.get("section_key"))
        ]
        step_map = {
            clean(row["step_key"]): clean(row["section_key"])
            for row in active_rows(wb, "step_order_summary_map", model_key=model_key)
            if clean(row.get("step_key")) and clean(row.get("section_key"))
        }
        return {
            "sections": sorted(sections, key=lambda row: row["display_order"]),
            "stepMap": step_map,
        }


    def load_standard_equipment_groups(wb, model_key: str) -> dict[str, dict[str, str]]:
        return {
            clean(row["section_id"]): row
            for row in active_rows(wb, "standard_equipment_groups", model_key=model_key)
            if clean(row.get("section_id"))
        }


    def load_component_price_rules(wb, model_key: str) -> list[dict[str, Any]]:
        return [
            {
                "price_rule_id": clean(row["price_rule_id"]),
                "condition_option_id": clean(row.get("condition_option_id")),
                "target_component_rpo": clean(row.get("target_component_rpo")),
                "price_rule_type": clean(row.get("price_rule_type")).lower(),
                "price_value": intish(row.get("price_value")),
                "body_style_scope": clean(row.get("body_style_scope")),
                "trim_level_scope": clean(row.get("trim_level_scope")),
                "variant_scope": clean(row.get("variant_scope")),
            }
            for row in active_rows(wb, "component_price_rules", model_key=model_key)
            if clean(row.get("price_rule_id"))
        ]


    Rollback:
    - Safe to revert because all loaders fall back if sheets absent/empty.
    - Git revert this module and imports.

    Validation:
    sh
    python -m py_compile scripts/corvette_form_generator/runtime_metadata.py


    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 6. Phase 3 — Fix Critical Runtime Rule Hardcodes

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Risk: High
    Fixes findings:
    - Runtime RPO conflicts/replacements/defaults
    - Runtime R6X/D30 price waiver
    - Runtime order-summary grouping

    Workbook rows to add:

    default_selection_rules:
    text
    stingray | default_fe1 | opt_fe1_001 | unless_selected_rpo | Z51 | * | * | * | 10 | TRUE
    stingray | default_nga | opt_nga_001 | unless_selected_rpo | NWI | * | * | * | 20 | TRUE
    stingray | default_719 | opt_719_001 | unless_selected_section | sec_seat_001 | * | * | * | 30 | TRUE


    runtime_rule_exceptions:
    text
    stingray | ex_z51_fe1 | opt_z51_001 | opt_fe1_001 | remove_target_when_source_selected | * | * | * | Replaced by FE3 Z51 performance suspension. | TRUE
    stingray | ex_z51_fe2 | opt_z51_001 | opt_fe2_001 | remove_target_when_source_selected | * | * | * | Not available with Z51 Performance Package. | TRUE
    stingray | ex_nwi_nga | opt_nwi_001 | opt_nga_001 | remove_target_when_source_selected | * | * | * | Replaced by NWI center exhaust. | TRUE
    stingray | ex_gba_zyc | opt_gba_001 | opt_zyc_001 | remove_target_when_source_selected | * | * | * | Black exterior paint is not available with body-color accents. | TRUE


    component_price_rules:
    text
    stingray | cpr_d30_r6x | opt_d30_001 | R6X | override | 0 | * | * | * | TRUE


    Generator data additions:

    In scripts/generate_stingray_form.py, after loading workbook:

    python
    from corvette_form_generator.runtime_metadata import (
        load_component_price_rules,
        load_default_selection_rules,
        load_order_summary_metadata,
        load_runtime_rule_exceptions,
    )

    default_selection_rules = load_default_selection_rules(wb, MODEL_CONFIG.model_key)
    runtime_rule_exceptions = load_runtime_rule_exceptions(wb, MODEL_CONFIG.model_key)
    component_price_rules = load_component_price_rules(wb, MODEL_CONFIG.model_key)
    order_summary_metadata = load_order_summary_metadata(wb, MODEL_CONFIG.model_key)


    In final data object:

    python
    data = {
        # existing fields...
        "defaultSelectionRules": default_selection_rules,
        "runtimeRuleExceptions": runtime_rule_exceptions,
        "componentPriceRules": component_price_rules,
        "orderSummary": order_summary_metadata,
    }


    Runtime implementation in form-app/app.js:

    js
    function generatedDefaultRules() {
      return Array.isArray(data.defaultSelectionRules) ? data.defaultSelectionRules : [];
    }

    function generatedRuleExceptions() {
      return Array.isArray(data.runtimeRuleExceptions) ? data.runtimeRuleExceptions : [];
    }

    function generatedComponentPriceRules() {
      return Array.isArray(data.componentPriceRules) ? data.componentPriceRules : [];
    }

    function optionIdByRpo(rpo) {
      return (data.choices || []).find((choice) => choice.rpo === rpo)?.option_id || "";
    }

    function exceptionApplies(exception) {
      if (!scopeMatches(exception.body_style_scope, state.bodyStyle)) return false;
      if (!scopeMatches(exception.trim_level_scope, state.trimLevel)) return false;
      if (!scopeMatches(exception.variant_scope, currentVariantId())) return false;
      return true;
    }

    function selectedOptionForException(optionId) {
      return state.selected.has(optionId);
    }

    function runtimeExceptionForTarget(targetOptionId) {
      return generatedRuleExceptions().find(
        (exception) =>
          exception.target_option_id === targetOptionId &&
          exceptionApplies(exception) &&
          selectedOptionForException(exception.source_option_id)
      );
    }

    function removeRuntimeExceptionTargets(sourceOptionId = "") {
      for (const exception of generatedRuleExceptions()) {
        if (!exceptionApplies(exception)) continue;
        if (sourceOptionId && exception.source_option_id !== sourceOptionId) continue;
        if (state.selected.has(exception.source_option_id)) {
          deleteSelectedOption(exception.target_option_id);
        }
      }
    }

    function addGeneratedDefaultChoices(autoAdded) {
      for (const rule of generatedDefaultRules()) {
        if (!scopeMatches(rule.body_style_scope, state.bodyStyle)) continue;
        if (!scopeMatches(rule.trim_level_scope, state.trimLevel)) continue;
        if (!scopeMatches(rule.variant_scope, currentVariantId())) continue;

        if (rule.condition_type === "unless_selected_rpo") {
          if (selectedOptionByRpo(rule.condition_id)) continue;
        }

        if (rule.condition_type === "unless_selected_section") {
          if (selectedOrAutoInSection(rule.condition_id, autoAdded)) continue;
        }

        addDefaultOption(rule.target_option_id);
      }
    }

    function componentPriceOverride(component, autoAdded) {
      for (const rule of generatedComponentPriceRules()) {
        if (rule.target_component_rpo !== component.rpo) continue;
        if (!scopeMatches(rule.body_style_scope, state.bodyStyle)) continue;
        if (!scopeMatches(rule.trim_level_scope, state.trimLevel)) continue;
        if (!scopeMatches(rule.variant_scope, currentVariantId())) continue;
        if (!autoAdded.has(rule.condition_option_id)) continue;
        if (rule.price_rule_type === "override") return Number(rule.price_value || 0);
      }
      return null;
    }


    Replace current hardcoded runtime branches:

    js
    function disableReasonForChoice(choice) {
      if (choice.active !== "True") return "Inactive in the source workbook.";
      if (choice.status === "unavailable") return "Not available for this body and trim.";

      const exception = runtimeExceptionForTarget(choice.option_id);
      if (exception) return exception.disabled_reason || Blocked by ${getEntityLabel(exception.source_option_id)}.;

      // existing generic rule logic continues...
    }


    js
    function reconcileSelections() {
      for (const id of [...state.selected]) {
        removeRuntimeExceptionTargets(id);
      }

      for (const id of [...state.selected]) {
        removeReplaceRuleTargets(id);
      }

      for (const id of [...state.selected]) {
        const choice = choiceForCurrentVariant(id);
        if (!choice || shouldHideChoice(choice) || disableReasonForChoice(choice)) deleteSelectedOption(id);
      }

      reconcileInteriorSelection();

      const autoAdded = computeAutoAdded();

      for (const id of [...state.selected]) {
        const choice = choiceForCurrentVariant(id);
        if (!choice || shouldHideChoice(choice) || disableReasonForChoice(choice)) deleteSelectedOption(id);
      }

      removeAutoDefaultDuplicates(autoAdded);

      const refreshedAutoAdded = computeAutoAdded();
      addWorkbookDefaultChoices();
      addGeneratedDefaultChoices(refreshedAutoAdded);
      dedupeSelectedRpos();
    }


    js
    function interiorComponentPrice(component, autoAdded) {
      const override = componentPriceOverride(component, autoAdded);
      if (override !== null) return override;
      return Number(component.price || 0);
    }


    Order summary runtime compatibility:

    js
    function orderSummarySections() {
      const generated = data.orderSummary?.sections;
      if (Array.isArray(generated) && generated.length) return generated;
      return orderSectionDefinitions.map(([section_key, section_label], display_order) => ({
        section_key,
        section_label,
        display_order,
      }));
    }

    function orderSummaryStepMap() {
      return data.orderSummary?.stepMap || Object.fromEntries(stepOrderSectionKeys);
    }

    function sectionKeyForStep(stepKey, type = "") {
      if (type === "auto_added") return "auto_added_required";
      return orderSummaryStepMap()[stepKey] || stepKey || "vehicle";
    }

    function sectionLabelForKey(sectionKey) {
      const section = orderSummarySections().find((row) => row.section_key === sectionKey);
      return section?.section_label || sectionKey;
    }


    Tests:
    - Add regression tests that:
      - Selecting Z51 removes/suppresses FE1/FE2 from workbook-driven exceptions.
      - Selecting GBA removes ZYC from workbook-driven exceptions.
      - Defaults FE1/NGA/719 are seeded by defaultSelectionRules.
      - R6X price becomes 0 only because componentPriceRules contains the override.
      - Removing the generated rows in test fixture disables behavior.

    Rollback:
    1. Revert runtime JS commit only. Generated data still contains extra arrays but runtime ignores them.
    2. Or set affected workbook rows active = FALSE, regenerate, redeploy.
    3. If deployed static app misbehaves, redeploy prior form-app/app.js + form-app/data.js.

    Risk controls:
    - Keep old hardcoded branches behind a temporary fallback flag for one release:
      js
      const USE_GENERATED_RUNTIME_RULES = Array.isArray(data.runtimeRuleExceptions);

    - Remove fallback only after parity tests pass.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 7. Phase 4 — Fix Generator Availability and R6X Manual Rules

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Risk: High
    Fixes:
    - UQT 1LT-only hardcode
    - R6X included-option fallback/manual rules
    - hidden section behavior

    Workbook changes:
    1. Add variant_option_overrides rows for opt_uqt_002 non-1LT Stingray variants:
       text
       stingray | opt_uqt_002 | 2lt_c07 | unavailable | False | False |  | UQT restricted to 1LT
       stingray | opt_uqt_002 | 3lt_c07 | unavailable | False | False |  | UQT restricted to 1LT
       stingray | opt_uqt_002 | 2lt_c67 | unavailable | False | False |  | UQT restricted to 1LT
       stingray | opt_uqt_002 | 3lt_c67 | unavailable | False | False |  | UQT restricted to 1LT


    2. Backfill lt_interiors.included_option_id = opt_r6x_001 for every active Stingray R6X interior row.

    3. Add section_presentation row:
       text
       stingray | sec_cust_002 |  | interior_trim |  | hidden |  |  |  | TRUE


    Generator implementation:

    python
    from corvette_form_generator.runtime_metadata import (
        load_section_presentation,
        load_variant_option_overrides,
    )

    section_presentation = load_section_presentation(wb, MODEL_CONFIG.model_key)
    variant_option_overrides = load_variant_option_overrides(
        wb,
        MODEL_CONFIG.model_key,
    )


    Replace hidden section logic:

    python
    def section_display_behavior(section_id: str) -> str:
        return clean(section_presentation.get(section_id, {}).get("display_behavior")).lower()


    python
    for option in options_raw:
        display_behavior = display_behavior_by_option_id.get(option["option_id"], "")
        section_behavior = section_display_behavior(option.get("section_id", ""))
        option["_display_behavior"] = display_behavior or section_behavior
        if option["_display_behavior"] == "hidden":
            option["active"] = "False"


    Replace UQT branch:

    python
    override = variant_option_overrides.get((option_id, variant["variant_id"]))
    if override:
        if clean(override.get("status")):
            status = clean(override["status"]).lower()
        if clean(override.get("selectable")):
            selectable = clean(override["selectable"])
        if clean(override.get("active")):
            active = clean(override["active"])
        if clean(override.get("display_behavior")):
            display_behavior = clean(override["display_behavior"]).lower()


    Then delete this hardcode:
    python
    if option_id == "opt_uqt_002" and variant["trim_level"] != "1LT":
        status = "unavailable"
        selectable = "False"
        active = "False"


    Replace R6X fallback:

    python
    included_option_id = clean(row.get("included_option_id"))
    if active_for_stingray and requires_r6x and not included_option_id:
        validation_rows.append(
            {
                "check_id": f"missing_r6x_included_option_{interior_id}",
                "severity": "error",
                "entity_type": "interior",
                "entity_id": interior_id,
                "message": "R6X interior requires included_option_id in lt_interiors.",
            }
        )


    Manual rules remain generated from workbook field, but no implicit fallback.

    Tests:
    - opt_uqt_002 output matches prior contract.
    - Removing the override row in a fixture changes output, proving workbook ownership.
    - Missing R6X included_option_id produces validation error.
    - sec_cust_002 hidden behavior comes from section_presentation.

    Rollback:
    1. Re-enable old hardcoded fallback in generator.
    2. Set new workbook rows inactive.
    3. Regenerate form-app/data.js.
    4. Restore workbook backup if necessary.

    Zero-downtime:
    - Deploy generated output only after parity with old behavior.
    - Extra workbook rows are inert until generator reads them.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 8. Phase 5 — Fix Interior Component Source of Truth

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Risk: Medium-High
    Fixes:
    - Interior component RPO decomposition and labels
    - Grand Sport interior scope/Z25 derivation

    Workbook changes:
    - Populate interior_components for each component-bearing interior.
    - Add scope fields or use model_interior_scope if you prefer separate ownership.

    Recommended separate sheet:
    text
    model_interior_scope(
      model_key,
      interior_id,
      trim_level,
      active,
      requires_option_id,
      notes
    )


    Generator implementation:

    python
    def load_interior_components(wb, model_key: str) -> dict[str, list[dict[str, Any]]]:
        rows = active_rows(wb, "interior_components", model_key=model_key)
        by_interior: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            interior_id = clean(row.get("interior_id"))
            rpo = clean(row.get("rpo"))
            if not interior_id or not rpo:
                continue
            by_interior[interior_id].append(
                {
                    "rpo": rpo,
                    "label": clean(row.get("label")),
                    "price": 0,
                    "component_type": clean(row.get("component_type")),
                    "price_ref_type": clean(row.get("price_ref_type")),
                    "price_ref_code": clean(row.get("price_ref_code")) or rpo,
                    "price_trim_scope": clean(row.get("price_trim_scope")),
                    "display_order": intish(row.get("display_order")),
                }
            )
        for interior_id in by_interior:
            by_interior[interior_id].sort(key=lambda row: row["display_order"])
        return by_interior


    def price_components(
        components: list[dict[str, Any]],
        price_ref: dict[tuple[str, str, str], int],
        trim: str,
    ) -> list[dict[str, Any]]:
        priced = []
        for component in components:
            price_trim = component["price_trim_scope"] or trim
            component = dict(component)
            component["price"] = price_ref_component_price(
                price_ref,
                component["price_ref_type"],
                component["price_ref_code"],
                price_trim,
            )
            priced.append(
                {
                    "rpo": component["rpo"],
                    "label": component["label"],
                    "price": component["price"],
                    "component_type": component["component_type"],
                }
            )
        return priced


    Use workbook components first, legacy parser fallback during migration:

    python
    component_rows = load_interior_components(wb, MODEL_CONFIG.model_key)

    def resolved_interior_components(row, price_ref):
        interior_id = clean(row.get("interior_id") or row.get("ID"))
        trim = clean(row.get("Trim"))
        if interior_id in component_rows:
            return price_components(component_rows[interior_id], price_ref, trim)
        return interior_component_metadata(row, price_ref)


    Grand Sport scope:

    python
    def load_model_interior_scope(wb, model_key: str) -> dict[str, dict[str, str]]:
        return {
            clean(row["interior_id"]): row
            for row in active_rows(wb, "model_interior_scope", model_key=model_key)
            if clean(row.get("interior_id"))
        }


    Replace hardcoded:
    python
    if trim not in {"1LT", "2LT", "3LT", "3LT_R6X"}:
        continue


    With:
    python
    scope = model_interior_scope.get(interior_id)
    if not scope:
        continue


    Tests:
    - Compare generated interior component arrays before/after migration.
    - Assert no hardcoded component labels remain required for active rows.
    - Assert Grand Sport interior count and Z25 requires behavior unchanged.

    Rollback:
    - Leave new sheets but disable rows.
    - Generator falls back to legacy parser.
    - Revert generator commit if needed.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 9. Phase 6 — Fix Step/Section/Presentation Metadata

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Risk: Medium
    Fixes:
    - Step order/labels
    - Section-to-step mapping
    - Standard-equipment section bucket
    - Body-style ordering
    - Synthetic context sections
    - Grand Sport section label overrides
    - Stingray section display-order overrides
    - Trim-equipment regex grouping

    Workbook backfills:
    - runtime_steps: copy current STEP_ORDER/STEP_LABELS.
    - context_section_master: copy current CONTEXT_SECTIONS.
    - section_presentation: copy current overrides and buckets:
      - standard_equipment_bucket = TRUE for existing standard section IDs.
      - display_label for Grand Sport overrides.
      - section_display_order for current Stingray overrides.
      - standard_equipment_group_type = trim_equipment for LT equipment sections.

    Generator implementation:

    python
    runtime_steps = load_runtime_steps(
        wb,
        MODEL_CONFIG.model_key,
        MODEL_CONFIG.step_order,
        MODEL_CONFIG.step_labels,
    )
    context_sections = load_context_sections(
        wb,
        MODEL_CONFIG.model_key,
        MODEL_CONFIG.context_sections,
    )
    section_presentation = load_section_presentation(wb, MODEL_CONFIG.model_key)


    Section display order:

    python
    presentation = section_presentation.get(section_id, {})
    section_display_order = (
        intish(presentation.get("section_display_order"))
        if clean(presentation.get("section_display_order"))
        else intish(section.get("display_order"))
    )


    Section label:

    python
    section_name = clean(presentation.get("display_label")) or section.get("section_name", "")


    Standard-equipment bucket:

    python
    def is_standard_section(section_id: str) -> bool:
        presentation = section_presentation.get(section_id, {})
        value = clean(presentation.get("standard_equipment_bucket"))
        if value:
            return value.lower() in {"true", "yes", "1"}
        return section_id in MODEL_CONFIG.standard_sections


    Update shared step_for_section() signature to accept a predicate or bucket map rather than static set.

    Runtime trim-equipment grouping:
    - Emit standard_equipment_group_type on standard equipment rows.
    - Replace regex:

    js
    function trimEquipmentRows() {
      return standardEquipmentRows().filter(
        (item) => item.standard_equipment_group_type === "trim_equipment"
      );
    }


    Backward-compatible fallback:

    js
    function trimEquipmentRows() {
      return standardEquipmentRows().filter(
        (item) =>
          item.standard_equipment_group_type === "trim_equipment" ||
          (!item.standard_equipment_group_type && /LT Equipment$/.test(item.section_name || ""))
      );
    }


    Tests:
    - Generated form_steps exactly matches prior step order.
    - Every section_master.step_key/presentation mapping resolves.
    - Grand Sport display labels unchanged.
    - Trim standard equipment visible without regex when metadata exists.

    Rollback:
    - Keep generator fallbacks for one release.
    - Set new presentation rows inactive or revert generator commit.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 10. Phase 7 — Fix Model Configuration Ownership

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Risk: Low-Medium
    Fixes:
    - Model-to-sheet and variant-id mapping

    Workbook rows:
    model_master:
    text
    stingray | stingray | Stingray | 2027 | 2027 Corvette Stingray operational form | stingray | 6 | TRUE | TRUE
    grand_sport | grandSport | Grand Sport | 2027 | 2027 Corvette Grand Sport operational form | grand-sport | 6 | FALSE | TRUE


    model_workbook_sources:
    text
    stingray | source_option_sheet | stingray_options | TRUE
    stingray | status_sheet | stingray_ovs | TRUE
    grand_sport | source_option_sheet | grandSport_options | TRUE
    grand_sport | status_sheet | grandSport_ovs | TRUE
    ...


    model_variants:
    - One row per active variant/model.

    Implementation:

    python
    def load_model_config_overrides(wb, config: ModelConfig) -> ModelConfig:
        master = {
            clean(row["model_key"]): row
            for row in active_rows(wb, "model_master")
            if clean(row.get("model_key"))
        }
        sources = {
            clean(row["source_role"]): clean(row["sheet_name"])
            for row in active_rows(wb, "model_workbook_sources", model_key=config.model_key)
            if clean(row.get("source_role")) and clean(row.get("sheet_name"))
        }
        variants = tuple(
            clean(row["variant_id"])
            for row in sorted(
                active_rows(wb, "model_variants", model_key=config.model_key),
                key=lambda row: intish(row.get("display_order")),
            )
            if clean(row.get("variant_id"))
        )
        row = master.get(config.model_key, {})
        return config.with_overrides(
            model_label=clean(row.get("model_label")) or config.model_label,
            model_year=clean(row.get("model_year")) or config.model_year,
            dataset_name=clean(row.get("dataset_name")) or config.dataset_name,
            source_option_sheet=sources.get("source_option_sheet", config.source_option_sheet),
            status_sheet=sources.get("status_sheet", config.status_sheet),
            variant_ids=variants or config.variant_ids,
            expected_variant_count=intish(row.get("expected_variant_count")) or config.expected_variant_count,
        )


    Requires ModelConfig.with_overrides():

    python
    from dataclasses import replace

    @dataclass(frozen=True)
    class ModelConfig:
        ...
        def with_overrides(self, **changes):
            return replace(self, **{k: v for k, v in changes.items() if v is not None})


    Rollback:
    - Existing model_configs.py constants remain fallback.
    - If workbook metadata bad, generator emits validation error and falls back or stops based on rollout flag.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 11. Phase 8 — Fix Audit Parser Hardcodes

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Risk: Low-Medium
    Fixes:
    - Rule phrase mapping
    - Engine-cover audit groups
    - Special review RPOs

    Parser implementation:

    python
    def load_rule_phrase_map(wb) -> list[dict[str, str]]:
        rows = active_rows(wb, "rule_phrase_map")
        if rows:
            return rows
        return [
            {"phrase": phrase, "rule_type": "", "direction": "", "stop_phrases": "", "review_flag_default": ""}
            for phrase in RULE_PHRASES
        ]


    def load_audit_group_members(wb) -> dict[str, set[str]]:
        groups: dict[str, set[str]] = defaultdict(set)
        for row in active_rows(wb, "option_audit_group_members"):
            group_id = clean(row.get("group_id"))
            rpo = clean(row.get("rpo"))
            if group_id and rpo:
                groups[group_id].add(rpo)
        if not groups:
            groups["engine_cover"] = set(ENGINE_COVER_RPOS)
        return groups


    def load_special_review_rpos(wb, model_key: str) -> set[str]:
        rows = active_rows(wb, "rule_review_groups", model_key=model_key)
        rpos = {clean(row.get("rpo")) for row in rows if clean(row.get("rpo"))}
        return rpos or set(GRAND_SPORT_MODEL.special_rule_review_rpos or ())


    Rollback:
    - Parser keeps constant fallback.
    - Audit output remains unchanged if workbook rows disabled.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 12. Phase 9 — Validation and Deployment

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Risk: Medium
    Purpose: prove no data drift.

    Required parity checks:
    1. Generate before migration on clean baseline.
    2. Save baseline generated JSON snapshots:
       sh
       cp form-output/stingray-form-data.json /tmp/stingray-before.json
       cp form-output/inspection/grand-sport-form-data-draft.json /tmp/grand-sport-before.json

    3. Run migration and regenerate.
    4. Compare data ignoring timestamps:
       sh
       node scripts/compare-generated-contracts.mjs /tmp/stingray-before.json form-output/stingray-form-data.json
       node scripts/compare-generated-contracts.mjs /tmp/grand-sport-before.json form-output/inspection/grand-sport-form-data-draft.json


    Production-ready comparison script:

    js
    #!/usr/bin/env node
    const fs = require("fs");
    const assert = require("assert");

    function normalize(value) {
      if (Array.isArray(value)) return value.map(normalize);
      if (value && typeof value === "object") {
        const out = {};
        for (const key of Object.keys(value).sort()) {
          if (["generated_at", "sourceGeneratedAt"].includes(key)) continue;
          out[key] = normalize(value[key]);
        }
        return out;
      }
      return value;
    }

    const [beforePath, afterPath] = process.argv.slice(2);
    if (!beforePath || !afterPath) {
      console.error("usage: compare-generated-contracts.mjs before.json after.json");
      process.exit(2);
    }

    const before = normalize(JSON.parse(fs.readFileSync(beforePath, "utf8")));
    const after = normalize(JSON.parse(fs.readFileSync(afterPath, "utf8")));

    try {
      assert.deepStrictEqual(after, before);
      console.log("contracts match");
    } catch (error) {
      console.error("contracts differ");
      throw error;
    }


    Full gates:
    sh
    .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
    .venv/bin/python scripts/generate_stingray_form.py
    .venv/bin/python scripts/generate_grand_sport_form.py
    node --test tests/stingray-form-regression.test.mjs
    node --test tests/multi-model-runtime-switching.test.mjs
    node --test tests/stingray-generator-stability.test.mjs
    node --test tests/grand-sport-contract-preview.test.mjs
    node --test tests/grand-sport-draft-data.test.mjs
    node --test tests/grand-sport-rule-audit.test.mjs


    Manual verification:
    - Stingray:
      - model/body/trim
      - paint
      - suspension/Z51
      - exhaust
      - interior R6X/D30
      - download build
      - submit modal payload
    - Grand Sport:
      - model switch
      - heritage hash marks
      - center stripes
      - UQT behavior
      - interiors/Z25
      - export/download

    Zero-downtime deployment:
    1. Build/regenerate locally.
    2. Verify static app locally.
    3. Upload/deploy static files atomically:
       - form-app/index.html
       - form-app/app.js
       - form-app/styles.css
       - form-app/data.js
    4. Keep previous deploy artifact available.
    5. Monitor dealer submission logs and browser console.

    Rollback:
    - Redeploy prior static artifact.
    - Git revert migration commit.
    - Restore workbook backup if needed.
    - Re-run generator from restored workbook.
    - Confirm form_validation has zero errors.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 13. Recommended Implementation Order

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    Do not do all findings in one pass. Recommended commits:

    1. chore(workbook): add runtime metadata sheets
       - New empty/backfilled source sheets only.
       - No behavior change.

    2. refactor(generator): load workbook metadata
       - Add shared loader with fallbacks.
       - No output drift.

    3. feat(runtime): drive defaults from generated data
       - Fix Critical Rank 1.

    4. feat(pricing): drive component price overrides
       - Fix Critical Rank 2.

    5. feat(generator): apply variant option overrides
       - Fix UQT and similar future variant-specific rules.

    6. feat(generator): require workbook R6X includes
       - Fix manual R6X fallback.

    7. feat(generator): source interior components
       - Move interior component decomposition to workbook.

    8. feat(generator): source step presentation
       - Move step/section/presentation metadata.

    9. feat(audit): source Grand Sport audit groups
       - Move parser/audit constants last.

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## 14. Spec Approval Boundary

    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    This spec is production-oriented but intentionally not implemented yet.

    Because this would:
    - touch multiple files,
    - alter workbook schema,
    - alter generated data contracts,
    - alter runtime selection/pricing behavior,
    - and affect live customer/dealer output,

    AGENTS.md requires approval before edits.

    Recommended first approved implementation pass:
    - Phase 1 + Phase 2 only.
    - Goal: add workbook sheets and loader fallbacks with zero behavior/output drift.
    - This creates the safe substrate before touching critical runtime behavior.
