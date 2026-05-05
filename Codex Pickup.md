# Codex Pickup

We are continuing the `27vette` schema_refactor to CSV for Stingray CSV-shadow ownership.

Use disciplined pass workflow:

- spec first
- provide Codex prompts with recommended reasoning level
- report-only vs migration scope must be explicit

Current status:

- Pass 156 showed no remaining ready migration rows: 83 preserved rows remain.
- Pass 157/158/159 split the legacy/non-selectable lane and added `data/stingray/validation/non_selectable_references.csv`.
- Pass 160 designed Option A for reference support: `subject_selector_type=non_selectable_reference` and `condition_terms.term_type=reference_selected`.
- Pass 161 implemented support only in `scripts/stingray_csv_first_slice.py`, with synthetic tests. No real migration rows were added.
- Full ladder after Pass 161 passed: `445/445`.
- No production/runtime/generated/workbook/form-app files were touched.
- Real data counts remain unchanged: `dependency_rules.csv` 101 rows, `requires` 3, `excludes` 98, `auto_adds.csv` 19 active, preserved rows 83, `selectables.csv` 97, non-selectable refs 6.

Key decisions:

- Do not project `5VM`, `5W8`, `5ZW`, `CF8`, `RYQ`, or `CFX` as customer selectables.
- `5VM/5W8/5ZW` can now participate in future CSV-owned dependency rules via registered non-selectable references.
- `CF8/RYQ` remain runtime-owned structured references.
- `CFX` remains design-gated for possible non-selectable auto-add/include target support.

Direction:

- Next useful pass is likely Pass 162: migrate a tiny/safe subset of `5VM/5W8/5ZW` rules using the new reference selector support, or do a final preflight selecting the safest subset.
- Keep migration small and oracle-confirmed.
- Do not touch catalog/display/pricing/runtime/generated/workbook.

Open questions / next steps:

- Decide whether Pass 162 should be report-only candidate selection or a micro-migration.
- If migrating, likely start with simple plain excludes involving projected normal endpoints, not Z51/package-adjacent rows.
- Ensure any migration adds only dependency/condition rows plus matching ownership cleanup, with production-oracle message parity.
