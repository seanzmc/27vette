Recommended reasoning level: high

Report-only task. Do not edit `stingray_master.xlsx`, generated `form_*` sheets, `form-output/*`, or `form-app/data.js`.

Audit `stingray_master.xlsx` for structural drift between the Stingray source sheets and the Grand Sport source sheets. Focus on workbook-owned business data and generator-facing contracts, not runtime refactors.

Primary comparison targets:

- Stingray: `stingray_options`, `stingray_ovs`, `rule_mapping`, `price_rules`, `rule_groups`, `rule_group_members`, `exclusive_groups`, `exclusive_group_members`, `color_overrides`, `lt_interiors`, `LZ_Interiors`
- Grand Sport: `grandSport_options`, `grandSport_ovs`, `grandSport_rule_mapping`, `grandSport_price_rules`, `grandSport_rule_groups`, `grandSport_rule_group_members`, `grandSport_exclusive_groups`, `grandSport_exclusive_members`, `grandSport_variant_overrides`
- Shared/reference sheets where relevant: `variant_master`, `category_master`, `section_master`, `PriceRef`
- Generated `form_*` sheets may be inspected only as downstream contract evidence, not as source-of-truth sheets to change.

Audit goals:

1. Identify header-level inconsistencies between equivalent Stingray and Grand Sport sheets.
   - Compare exact header names, semantic equivalents, missing/extra columns, casing, pluralization, model prefixes, and naming patterns.
   - Classify each mismatch as blocker, likely intentional, harmless drift, or needs human review.

2. Identify data-type inconsistencies in equivalent columns.
   - Check booleans, prices, numeric sort/order fields, RPO codes, model/variant identifiers, comma-delimited values, JSON-like values, blanks/nulls, and free-text detail fields.
   - Call out columns where the same concept is stored differently across models.

3. Analyze key-value alignment differences from the source order-guide structure.
   - Look for cases where equivalent information appears as a dedicated column in one model but as a free-text/detail value, matrix-derived value, override row, or grouped rule in the other.
   - Note whether the difference appears to come from the online order guide layout, manual normalization, or generator expectations.

4. Compare rule and compatibility logic paths.
   - Review how includes, requires, excludes, grouped requirements, exclusive groups, package includes, color/interior availability, price scopes, and variant overrides are represented.
   - When two paths reach the same runtime/business outcome, identify the dominant/common workbook pattern and the alternate pattern.
   - Do not assume both paths are wrong; explain the practical impact on repeatable ingestion and JSON generation.

5. Evaluate semantic similarity.
   - For header or rule-path discrepancies, compare meaning rather than only exact strings.
   - Provide proposed canonical names only as recommendations, not edits.
   - Prefer workbook-owned normalization over Python or JavaScript special cases.

Deliverable:
Provide a detailed audit report with:

- Executive summary
- Sheet-pair comparison matrix
- Header discrepancy table
- Data-type discrepancy table
- Rule-path / compatibility-path discrepancy table
- Key-value alignment observations
- Recommended canonical workbook patterns for future ingestion
- Risks for NoSQL/JSON ingestion
- Open questions requiring Sean’s decision
- Suggested validation checks or scripts for a later implementation pass

Constraints:

- Treat the workbook as the source of truth.
- Do not change workbook data, generated sheets, generated artifacts, runtime JavaScript, tests, or docs.
- Do not add dependencies.
- Do not hide source-data issues in generator/runtime logic.
- Do not expand hardcoded model-specific behavior.
- Cite concrete workbook sheets, headers, representative rows/RPOs, and generator/runtime consumers where relevant.
