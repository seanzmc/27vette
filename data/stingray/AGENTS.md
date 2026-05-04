# Agent Instructions for data/stingray

## CSV-shadow scope

This directory is the CSV-shadow migration package. It is not the production source of truth yet.

- Production behavior remains the oracle.
- Do not describe `data/stingray/**/*.csv` as canonical unless cutover has been explicitly approved.
- Do not write shadow output into production `form-app/data.js`.
- Preserve the existing production-shaped output contract unless the task explicitly approves a contract change.

## Ownership rules

- Keep ownership explicit: `projected_owned`, `production_guarded`, or `preserved_cross_boundary`.
- Use `validation/projected_slice_ownership.csv` when changing projected slices, package edges, rule groups, guarded IDs, or cross-boundary records.
- Package includes and price rules may project only when the source and emitted targets are projected-owned.
- Rule groups may project only when the source and all emitted targets are projected-owned.
- Do not remove preserved cross-boundary rows until both sides are intentionally migrated.

## Interior and non-choice references

- No interior migration unless explicitly approved.
- Do not create fake selectables or manifest rows for `3LT_*` interior source IDs.
- `3LT_*` IDs are valid interior runtime source IDs backed by production `data.interiors[]`.
- Rule-only legacy option IDs remain guarded only when they are option-like legacy references.
- Unknown structured non-choice refs should fail validation unless guarded or valid interior IDs.

## Validation

For CSV data changes, run the focused affected `tests/stingray/*` test first.

Run adjacent control-plane tests when ownership, package boundaries, rule-only IDs, or interior source namespaces are involved.
