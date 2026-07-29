# Outcome rubric — Pass 4 Stage C preflight

Run: `2026-07-29-pass4c-preflight`

Source commit: `3515f72` (`Complete Pass 4 Stage B retirement`)

Authority: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`, Stage C and §§9.3–9.4.

## Scope

Read-only repository audit plus this preflight receipt/spec closeout. No plan move, archive, deletion, workbook write, artifact generation/publication, runtime change, dealer change, or Stage C implementation is authorized.

## Definition of done

C1. Mechanically enumerate every currently tracked `.hermes/plans/*.md` file and reconcile the live set with the bound §9.4 baseline: no missing, extra, or duplicate disposition.

C2. Classify each live plan individually as one of:
- `PROPOSE_ARCHIVE_ALREADY_CLOSED`
- `PROPOSE_CLOSE_THEN_ARCHIVE`
- `KEEP_OPEN`
- `KEEP_HISTORICAL_INPUT`
- `NEEDS_DECISION`

Every proposed move needs current-source/reference evidence. A plan without
top-level closure must be classified `PROPOSE_CLOSE_THEN_ARCHIVE`, with an exact
pre-move closure action in the separately approved manifest; age, filename, or
a historical completion mention is insufficient.

C3. Publish an exact source→destination map for proposed plan archives and prove destination paths do not collide. Publish explicit keep/decision lists for every non-archive plan.

C4. Rebase every §9.3 historical-doc and generated-review/log candidate against the current tree. Each proposed deletion needs zero active consumers and proof that unique evidence is already retained elsewhere. Historical archives and required Fable receipts remain protected.

C5. Decide, with evidence, whether `fable5loop/STATE.md` needs a compact current-state header. The preflight may recommend a separately approved edit but must not rewrite chronological history.

C6. Inventory all current non-archive references that would need updates after approved moves/deletions. Historical archive prose may retain original paths.

C7. Produce one exact Stage C implementation boundary for separate approval, including moves, deletions, reference updates, explicit protected surfaces, rollback, and proportional validation. No implementation action occurs in this run.

C8. Independent verification checks inventory completeness, classifications, evidence migration, destination collisions, active-reference updates, protected boundaries, and the no-implementation claim.

## Protected boundaries

- `stingray_master.xlsx`
- `form-output/` and `form-app/`
- scripts, tests, runtime behavior, and dealer submission
- existing archive payloads and historical receipts
- Stage C implementation approval

## Stop conditions

Stop and classify rather than propose archive/deletion when status or evidence is ambiguous, a current consumer exists, evidence migration is unproven, or the destination collides.
