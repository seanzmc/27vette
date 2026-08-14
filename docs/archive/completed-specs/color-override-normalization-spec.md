# Spec: Color-combination override (D30) normalization across models + EL9 closure (Pass 3)

> **Archive closure (2026-07-29): COMPLETED.** Implementation is present at `6e4d052` with retained D30/R6X coverage. Any trailing approval request is historical; current operator commands are owned by `README.md`. Stage C approved this completed plan for archival.

Date: 2026-06-10
Branch: work/27vette-copy-2026-06-09. Follows pass 2 (R6X components).
Recommended reasoning level if handed to Sean: medium.

## Diagnosis (evidence)

The D30 "Color Combination Override" ($1,495) pipeline is:
  lt/LZ_Interiors "Color Overrides" raw text (e.g. "G26, G4Z, GBK, GPH")
    -> color_overrides sheet rows (interior_id, option_id, requires, opt_d30_001)
    -> build_color_overrides (filters to the model's interior_ids + valid options)
    -> data.colorOverrides -> app.js computeAutoAdded auto-adds D30 when the
       paired interior + exterior color are both selected.

1. Z06 NORMALIZATION GAP (the real bug):
   color_overrides has 245 rows, ALL keyed by Stingray/GS interior ids
   (1LT/2LT/3LT). Z06's LZ interior ids (1LZ/2LZ/3LZ) never match, so z06
   colorOverrides = 0 in data.js — yet LZ_Interiors has 34 rows carrying
   "G26, G4Z, GBK, GPH" raw override text that was never normalized into the
   sheet. Z06 customers currently never get the D30 charge/disclosure.
   G26/G4Z/GBK/GPH are all active z06 options (opt_g26_001 etc).
   Stingray=245, GS=245 (shared 3LT ids pass GS's filter), Z06=0.

2. D30 option-row convention drift across models:
   - stingray_options: active=True, selectable=False, display_only
     -> generated: status available, visible display-only card.
   - grandSport_options: active=True, selectable=False, auto_only
     -> generated: unavailable/False/False (hidden until auto-added).
   - z06_options: active=True, selectable=TRUE, auto_only
     (selectable=True is meaningless under auto_only — generation forces
     unavailable/False/False — but it's wrong source data).

3. EL9 (Santorini Blue Dipped with Torch Red accents, $1,995):
   ALREADY GS-only — confirmed in generated data: GS has 3LT_AE4_EL9 +
   3LT_AH2_EL9 active (model_interior_scope rows with
   requires_option_id=opt_z25_001), stingray active_for_stingray=False,
   z06 zero EL9 rows. No availability change needed; user requirement is
   already satisfied — verified, not assumed.
   Residual defect from pass 2 audit: interior_components has ONE stray row
   (grand_sport, 3LT_AE4_EL9, AE4 seat, $595) making component sum 595 vs
   interior price 1995. Its sibling 3LT_AH2_EL9 has NO component rows and
   renders correctly as a single $1,995 line. The EL9 price is a package
   price ("Included and only available with (Z25) Grand Sport Launch
   Edition") — decomposing a $595 seat out of it is wrong and invents a
   $1,400 remainder. Fix: DELETE the stray component row; both EL9 interiors
   then render as single-line interiors, sum check passes vacuously.

## Decision point (user input wanted)

D30 display convention — pick ONE for all three models:
  (a) Stingray's display_only: D30 appears as a visible, non-selectable card
      in Interior Color (sec_colo_001), so the $1,495 override is disclosed
      before it's triggered.
  (b) GS's auto_only: D30 hidden until a color/interior pairing auto-adds it.
  Default proposal: (a) display_only everywhere — better disclosure of a
  forced $1,495 charge, and Stingray is the longest-proven production model.
  Either way, z06's selectable=True is corrected to False.

## Exact changes

A. color_overrides sheet: +136 rows for z06 — the 34 LZ_Interiors rows with
   Color Overrides raw x their listed color options:
   (interior_id, opt_g26_001|opt_g4z_001|opt_gbk_001|opt_gph_001,
   'requires', 'opt_d30_001'), mirroring the existing stingray row pattern.
   Generated from LZ_Interiors raw text by the apply script (no hand
   enumeration), validating each option id exists in z06_options.
   No new sheet, no new column: build_color_overrides already model-filters
   by interior_id, so LZ-id rows are inert for stingray/GS.
b. Cross-check: lt_interiors has 36 raw-override rows vs 245 sheet rows for
   stingray/GS — apply script also AUDITS (report-only) that every
   lt_interiors raw row has matching sheet rows, so we close any silent
   stingray/GS gaps the same way. Fix gaps if found (same encoding).
C. D30 convention per decision: set display_behavior on the two non-chosen
   models' opt_d30_001 rows; set z06 selectable=False regardless.
D. interior_components: delete the (grand_sport, 3LT_AE4_EL9, AE4) row.
E. Regenerate stingray, grand_sport, z06.

## Non-goals

- No app.js changes (colorOverrides evaluation is already generic).
- No ZR1/ZR1X rows (LZ raw text may cover them later; their models are not
  promoted).
- No price changes: D30 stays $1,495; EL9 stays $1,995; no interior totals
  move.
- No EL9 availability change (already GS-only).
- No new sheets/columns/taxonomies.

## Acceptance criteria

1. data.js z06 colorOverrides = 136 (34 interiors x 4 options); stingray/GS
   counts unchanged (or increased only by audited gap-fixes from B, reported).
2. Z06 browser: select an override-listed interior (e.g. 1LZ_AQ9_HUQ
   Adrenaline Red) + an override color (e.g. GBK black) -> D30 auto-added at
   $1,495 with reason text; removing the color removes D30.
3. Stingray browser: existing D30 behavior unchanged (regression: pick a
   known pairing, verify identical auto-add + total as pre-pass).
4. GS: both EL9 interiors render as single $1,995 line items; component-sum
   integrity check passes 100% on all three models (closes the pass-2
   residual).
5. Interior totals: zero moved on all models (structural compare).
6. D30 generated choice rows consistent across models per chosen convention.

## Validation plan

1. Snapshot data.js + artifacts to /tmp/27v-pass3-pre.
2. Throwaway apply script (save_workbook_safely + read-back), Excel closed.
3. validate_workbook_schema; regenerate all three models.
4. Structural compare: only colorOverrides arrays, D30 choice rows, EL9
   component json, timestamps may differ.
5. Gates: stingray-form-regression, stingray-generator-stability,
   grand-sport-contract-preview, grand-sport-draft-data, z06-contract-preview,
   z06-form-data-draft, z06-interior-accessory-cleanup,
   z06-performance-package-interactions, z06-runtime-rule-corrections,
   multi-model-runtime-switching. The stingray-form-regression D30/R6X test
   must pass UNCHANGED (no expectation edits anticipated this pass).
6. Browser smoke per acceptance criteria 2-4.
7. Delete throwaway script.

## Risks

- 136 new rows mis-derived from raw text: mitigated by deriving
  programmatically from LZ_Interiors + validating option ids + read-back +
  count assertion (34x4).
- D30 display_only on GS/Z06 surfaces a new card in Interior Color section:
  visual change, intended disclosure; browser check confirms placement.
- The 245-row stingray/GS set may itself have gaps vs raw text (audit B
  reports before fixing).

## Approval question

Approve with D30 convention (a) display_only everywhere? Or keep (b)
auto_only on GS/Z06 (then stingray converts to auto_only instead — still one
convention)?
