# Outcome rubric — refresh the three stale unpromoted runtime contracts

Timing, stated honestly: this rubric was written after the isolated diff review
and after Sean's four product decisions, but **before** any tracked file was
written. It formalizes those decisions into pass/fail criteria; it is not a
post-hoc description of what happened.

Run: `2026-07-27-stale-unpromoted-contract-refresh`
Trigger: the Pass 3 candidate lane, on its first real run, refused every
promotion because `grand_sport_x`, `zr1`, and `zr1x` retained contracts no longer
matched what the workbook generates.

## Boundaries

- The canonical workbook is **not** written. `stingray_master.xlsx` SHA-256 must
  be identical at start and end.
- `form-app/data.js` is **not** republished. All three models are unpromoted, so
  no customer-visible surface may change.
- No product or business rule is decided here. Where the fresh output differs
  from the old artifact, the workbook is the authority and the difference is
  reported, not adjudicated.

## Sean's decisions this run implements

D1 J57 Carbon Ceramic Brakes at $0 on Grand Sport X is correct — it is standard
   equipment on that model. Leave as generated.
D2 FED Sport Performance Package at $500 is intentional. The price schedule shows
   ZER and the order guide shows FED; that is the manufacturer's to reconcile.
   Judgement call made, leave as generated.
D3 The `selectable` False→True flips are correct: those standard options have
   selectable alternatives, so they must be selectable.
D4 **Except EFR on ZR1 and ZR1X** — that option has no alternative on those
   models and must not be selectable.

## Criteria

C1 **Every written value traces to the workbook.** For each field that changed,
   the fresh value equals what the workbook authors. No generator-side
   adjustment, no hand-edited artifact.

C2 **D4 is satisfied by the written artifacts.** EFR must be non-selectable on
   ZR1 and ZR1X in the artifacts on disk. If regeneration alone does not achieve
   this, a guarded workbook ChangeSet is required and this run stops for approval
   rather than hand-editing.

C3 **D1–D3 are preserved, not silently reverted.** J57 $0, FED $500, and the
   remaining selectable flips must be present in the written artifacts.

C4 **The blocker is actually cleared.** `verify_workbook_candidate.py` with
   nothing declared changed exits 0 with `unexpected_drift == []` for all six
   models.

C5 **Protected boundaries hold.** Workbook SHA unchanged; `form-app/data.js`
   unchanged; only the three target contracts (plus any generator-owned
   companion artifact) modified.

C6 **Every test that breaks is investigated at the workbook, not patched to
   green.** A test asserting on these contracts that now fails must be shown to
   be pinning a stale artifact — by reading the workbook column that owns the
   value — before its expectation is changed. Changing an expectation without
   that check fails this criterion.

C7 **Full gate parity.** Python suite and all node gates at or above baseline,
   with any pre-existing failure named.

## Failure conditions

- Any workbook byte change, or any `form-app/data.js` change.
- EFR selectable on ZR1 or ZR1X in the written artifacts.
- A test expectation edited to match the new artifact without confirming the
  workbook authors that value.
- The candidate lane still reporting drift afterwards.
