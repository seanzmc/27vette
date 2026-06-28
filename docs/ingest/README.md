# 27vette ingest docs

This folder owns the current schema and raw order-guide ingest planning docs.

Raw GM order-guide ingest is an edge workflow, not routine maintenance. Use it only for:

- adding a model that is not already in the form; or
- performing a broad GM/order-guide refresh across existing models.

Routine corrections belong in canonical workbook source sheets, followed by normal regeneration and gates.

## Current docs

- `pass-0/ingest-wizard-source-profiler-spec.md` — implemented CLI-first, read-only source profiler that emits source-layout, variant-matrix, raw-row, disclosure-link, manifest, and checkpoint artifacts before any candidate normalization or workbook apply exists.
- `pass-1/candidate-normalizer-spec.md` — implemented CLI-first, read-only candidate normalizer over Pass 0 evidence artifacts; emits transient candidate and unresolved-review artifacts only.
- `pass-2/interactive-review-wizard-spec.md` — current spec for a read-only Ingest Review tab over Pass 1 candidate artifacts; captures/export review decisions without workbook apply.

## Current decisions

- Keep `Order-Guide_IngestPrompt.md`, but treat the old content as replaced by the rewritten normalized prompt.
- Continue ingest work on the single `ingest-wizard` branch after merging Pass 0/1 into local `main`; do not create a new branch per pass unless explicitly requested.
- `docs/workbook-sheet-index.md` was stale and has been archived to `docs/archive/workbook-sheet-index-2026-06-12.md`.
- Existing ZR1/ZR1X workbook source scaffolds should not be used as canonical ingest truth. They need a clean reprocess path before future ingest implementation/testing relies on them.
