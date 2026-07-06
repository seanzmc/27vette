# Outcome rubric · 2026-07-06 · Pass B.1 — review-stage usability correction

## Task summary

- Goal: user-directed correction to the Pass B review stage (Sean, 2026-07-06): remove raw-JSON payload inputs, add bulk actions, smooth the completion path, and add cross-model decision copying so three similar models don't need triple review.
- Changed surface: tooling/UI/tests/docs (wizard only). Read-only toward workbook, tracked `form-output/`, `form-app/`, dealer submission — unchanged from Pass B.
- Source-of-truth decision: copy/bulk mechanics are script-owned structure; every copied or bulk-created decision is still reviewer-triggered and auditable (provenance recorded). Nothing auto-applies without an explicit reviewer action.
- Expected files: `decisions.py` (copy engine), `session.py` + `ingest_wizard_server.py` (copy endpoint), `visualizer/ingest-wizard/*`, tests, spec Pass B status note.

## Required outcome criteria

1. **No raw JSON inputs in any lane.** Every lane captures its payload through purpose-built controls (selects, text fields, per-column editable tables for presentation rows). Payload shapes stay identical on disk.
2. **Bulk actions:** section lane — assign a section to all filtered rows and per-source-section-label groups; price lane — accept all exact matches in one action; status-nuance — bulk confirm parsed statuses for filtered rows; standard-equipment — bulk include/exclude filtered rows. All bulk actions create ordinary decision records via the existing batch endpoint; nothing bypasses validation.
3. **Hint acceptance:** relationship hints get a one-click accept that prefills/creates a relationship decision (kind, source RPO, target RPOs) — editable before save, never auto-applied without the click.
4. **Cross-model copy:** reviewer-triggered copy of decisions from model A to model B: same-candidate copies where the candidate is in scope of both (shared mixed sheets), RPO-identity matching otherwise (exactly-one match required; ambiguous/no-match reported, never guessed); existing target decisions never overwritten (skip + report) without explicit overwrite; copied records carry `copiedFrom` provenance; presentation payload rows get `model_key` swapped. Copy report shows copied/skipped counts by lane.
5. **Pass B semantics preserved:** completeness math, fingerprint invalidation, comparator exclusion, reconciliation blocker, and artifact schemas unchanged (`pass-b-1`); all existing Pass B tests stay green.
6. **Boundaries preserved:** workbook read-only; protected surfaces clean.
7. **Validation real:** new copy-engine tests + updated lane/bulk coverage green; existing wizard suites green; browser proof on the real export: bulk section assign, accept-all-exact prices, hint accept, ZR1→ZR1X copy with report, no console errors.
8. **Verifier PASS** + loop closeout (receipt, STATE, skill decision, validator).

## Stop conditions

Implementation on disk; criteria gradable from artifacts; verifier pass or human-accepted failure; STATE updated. Max 3 maker/verifier cycles.
