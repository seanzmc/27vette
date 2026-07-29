# Spec: Retire R6X special-casing; R6X as a workbook interior component at $995 (Pass 2)

> **Execution status (2026-07-29): SUPERSEDED FOR COMMANDS.** `production.py` references and generator commands below describe an older topology and are not operator guidance. Use `README.md` and Pass 4 Stage A of `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md` for current commands. The product-contract evidence remains historical context.

Date: 2026-06-10
Branch: work/27vette-copy-2026-06-09 (local copy). Follows pass 1 (J57 + app.js).
Recommended reasoning level if handed to Sean: high (pricing flow has an
unread seam — see Step 0).

## Decisions locked by user

- Retire review_flag / price_semantic / lifecycle taxonomy. STATUS: already
  retired in local workbook + generator + schema_validation. Merge simply
  takes local. No further action this pass; live's schema checks die with the
  merge. (Confirmed: local sheets have no review_flag/price_semantic columns;
  local schema_validation has no checks referencing them.)
- Retire live's Python R6X manual-rule synthesis. STATUS: already absent from
  local production.py. The replacement contract is workbook-owned:
  interior_components rows + lt/LZ included_option_id — completed by this pass.
- R6X = interior component at $995, applied to interiors with R6X in the id,
  auto-added on selection of any of those interiors.
- Color-combination override normalization across models: NAMED, DEFERRED to
  its own pass (pass 3 candidate). Not touched here.

## Diagnosis (evidence)

1. Z06 R6X component price resolves $0.
   z06 interior_components R6X rows (15) use price_ref_type='r6x',
   price_ref_code='R6X', price_trim_scope='3LZ_R6X' — but PriceRef has NO r6x
   row. PriceRef only has ('Seat','3LZ R6X','AH2')=995 and
   ('Seat','3LZ R6X','AE4')=1590. The z06 rows are authored for a target
   state whose PriceRef row was never added.
   Generated data confirms: all 15 z06 R6X interiors have component sums
   short of interior price by EXACTLY 995 (e.g. 3LZ_R6X_AH2_HZB price 995
   compSum 0; 3LZ_R6X_AH2_HXO_N2Z_38S_TU7 price 2980 compSum 1985).
   These 15 are the ONLY z06 interiors where component sum != price — this is
   the entirety of the user-reported "z06 components not populating with
   right prices" issue.

2. Stingray/GS R6X component rows overstate the R6X price.
   stingray interior_components R6X rows use price_ref_type='seat',
   price_ref_code=AE4|AH2, scope '3LT_R6X' -> AE4 resolves 1590, AH2 995.
   But generated stingray totals contradict 1590: 3LT_R6X_AE4_HU0_38S price
   1490 = 995 + 495 stitching, while its component list claims R6X:1590 +
   38S:495 = 2085. Totals across all models are consistent with R6X = 995
   flat regardless of seat. The PriceRef ('Seat','3LT R6X','AE4')=1590 and
   ('Seat','3LZ R6X','AE4')=1590 rows look like legacy double-count
   (995 R6X + 595 3LT/3LZ AE4 seat) and conflict with shipped totals.

3. Z06 R6X auto-add is broken in source data.
   - LZ_Interiors: requires_r6x=True on 15 rows but included_option_id is
     BLANK on all (lt_interiors has opt_r6x_001 on its 15).
   - z06_options opt_r6x_001: active=False (stingray: active=True,
     selectable=True, display_behavior=auto_only; GS: active=True,
     selectable=False).
   - production.py validates included_option_id for R6X rows (stingray path);
     the draft path's enforcement for LZ needs verification in Step 0.

Risk level: medium. Data-only intent, but the interior pricing flow has an
unverified seam (see Step 0) and totals must not move.
Change type: workbook/data-only (goal); generator change only if Step 0
proves the pipeline cannot express the contract (must be flagged first per
AGENTS.md).

## Non-goals

- No color-override normalization (deferred pass).
- No ZR1/ZR1X work (their interior_components rows exist but models are not
  promoted; do not touch).
- No runtime JS changes.
- No new sheets, no new taxonomy — fills existing canonical blanks only.

## Step 0 (read-only, required before any edit)

Trace where the z06 R6X interior TOTAL price (995) comes from today given the
component resolves 0 — read pricing.py r6x/price_ref paths and
inspection.py/production.py interior price assembly. The fix must keep totals
byte-identical while making components sum to them. If totals are derived
from PriceRef seat rows ('Seat','3LZ R6X',seat), removing/changing the AE4
1590 row could change totals — Step 0 decides whether AE4 1590 rows can be
retired now or must be corrected to 995 instead. Report findings before edits.

## Step 0 FINDINGS (resolved 2026-06-10)

- PriceRef ('Seat','3LT R6X'/'3LZ R6X', AE4=1590 / AH2=995) rows are DELTA
  INPUTS consumed by pricing.r6x_price_component (R6X-trim seat minus
  base-trim seat = 995 in all four cases). They are NOT double-counts and
  MUST STAY. Diagnosis point 2's "legacy double-count" hypothesis is
  WITHDRAWN; totals already encode R6X=995 via delta arithmetic.
- Component prices use a separate lookup (price_ref_component_prices) keyed
  by normalized OptionType; a single new row OptionType='R6X', Trim blank,
  Code='R6X', Price=995 resolves via the documented blank-trim fallback.
- z06/zr1/zr1x interior_components R6X rows already use r6x/R6X encoding;
  only stingray (15) + grand_sport (15) rows need normalizing from seat/AE4|AH2.
- Runtime auto-add is via interior component line items (lineItemsFromInterior
  in app.js), NOT the opt_r6x_001 choice; generated choice rows are
  active=False on all models by design. identityPrice = max(0, replacedSeat +
  interiorPrice - componentSum) keeps totals invariant; only breakdowns change.
- LZ included_option_id is read only by production.py (stingray path) today;
  filling it is inert for z06 runtime but correct parity data.

## Exact changes (final)

A. PriceRef: ADD one row ('R6X', '', 'R6X', 995). KEEP all existing Seat
   R6X-trim rows (delta inputs).
B. interior_components: stingray + grand_sport R6X rows (30 total):
   price_ref_type 'seat'->'r6x', price_ref_code AE4|AH2->'R6X'. z06/zr1/zr1x
   untouched (already correct).
C. LZ_Interiors: included_option_id='opt_r6x_001' on the 15 requires_r6x rows.
D. z06_options opt_r6x_001: active=False->True (align to GS convention
   active=True/selectable=False); stingray_options opt_r6x_001
   selectable True->False to complete the convention. Generated choice rows
   stay active=False on all models (verified existing behavior).
E. Regenerate stingray, grand_sport, z06.

## Acceptance criteria

1. All three models: every interior's component sum == interior price
   (script check across data.js), specifically the 15+15+15 R6X interiors
   now carry R6X:995 components.
2. Interior TOTAL prices unchanged vs pre-pass data.js (only component
   breakdowns and the R6X auto-add change).
3. Z06 browser: selecting any 3LZ R6X interior auto-adds R6X (opt_r6x_001)
   to the build summary; deselecting removes it; dealer payload includes R6X.
   Stingray 3LT R6X interiors keep identical behavior to pre-pass.
4. No new validation errors from generate_form on any model.

## Validation plan

1. Pre-change: snapshot data.js + z06/gs/stingray artifacts to /tmp.
2. After workbook edits: openpyxl read-back verification of every edited row.
3. .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
4. Regenerate all three models; structural compare: assert the ONLY deltas
   are interior_components_json contents, z06 opt_r6x_001 activation, and
   timestamps.
5. Gates:
   node --test tests/stingray-form-regression.test.mjs
   node --test tests/stingray-generator-stability.test.mjs
   node --test tests/grand-sport-contract-preview.test.mjs
   node --test tests/grand-sport-draft-data.test.mjs
   node --test tests/z06-contract-preview.test.mjs
   node --test tests/z06-form-data-draft.test.mjs
   node --test tests/z06-interior-accessory-cleanup.test.mjs
   node --test tests/z06-performance-package-interactions.test.mjs
   node --test tests/z06-runtime-rule-corrections.test.mjs
   node --test tests/multi-model-runtime-switching.test.mjs
   (some z06 interior tests may assert current broken component data — if a
   test locks the $0 R6X component, update the test WITH the fix and call it
   out in the handoff)
6. Browser smoke per acceptance criteria 3, all three models.
7. Throwaway apply scripts deleted after verification.

## Risks

- Pricing-flow seam (Step 0) — main risk; totals must not move.
- opt_r6x_001 activation on Z06 could surface the option somewhere visible if
  display_behavior/auto_only handling differs by model — browser check covers.
- PriceRef row removal could break an unseen consumer — Step 0 greps all
  readers of PriceRef seat scope before removal; prefer correcting values
  over deleting rows if ambiguous.

## Approval question

Approve pass 2 as scoped (Step 0 report first, then A–E + validation)?
Color-override normalization will be specced separately as pass 3.
