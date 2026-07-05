# Outcome rubric · 2026-07-05 tidy pass 4 + pass 7

Task-specific derivative of `fable5loop/outcomes/27vette-loop-outcomes.md`.

## Task summary

- Goal: implement simplification-audit Pass 4 (archive completed docs/plans per the 2026-06-27 precedent) and Pass 7 (rename ellipsis-named loop source doc), spec-first, after committing Pass 1.
- Changed surface: docs/file-organization + comment-only path references in code/tests + loop artifacts (contract sourceDocument, README, STATE, skill).
- Source-of-truth decision: docs/tooling; no workbook, generator-logic, runtime, or styling changes.
- Protected boundaries: workbook, generated artifacts, runtime app, styling, dealer submission, ingest — preserved (one gate-induced timestamp churn caught and restored).
- Expected files: 13 archival renames + 4 plan deletions + 5 comment-path updates (Pass 4); 1 rename + 5 reference updates (Pass 7); 2 specs; receipt + STATE + skill update.

## Required outcome criteria

1. Spec-first: both passes have narrow specs written before edits, with exact files and gates.
2. Exact scope: staged diff matches specs exactly; no other audit passes touched; generated surfaces diff-empty.
3. Reference integrity: no active references to moved/deleted paths; old ellipsis filename referenced only by immutable historical receipts and the doc's own content.
4. Gates real: node/pytest gates run with honest reporting of pre-existing failures; loop validator green.
5. Independent verifier grades from artifacts; maker fixes only evidence-backed failures (max 3 cycles).
6. Memory compounds: verified facts + last-session in STATE; durable procedural lesson distilled to skill.

## Result

All criteria met. Verifier: FAIL on first cycle (gate-induced z06 timestamp churn), maker restored the artifact, re-verified read-only → **PASS** (11/11). One maker/verifier cycle used of 3.
