# Outcome: Grand Sport Jake-graphics/heritage-hash reverse exclusion gap

Date: 2026-07-11

## Task

Same bug class as the closed stripe/heritage fix (`287383e`): SHT/PDA/SNE/VPO (and VPW, per explicit check) exclude `opt_z15_001` but target none of the six Heritage Hash Marks (`opt_17a_001`, `opt_20a_001`, `opt_55a_001`, `opt_75a_001`, `opt_97a_001`, `opt_dx4_001`). Hash marks reach Z15 only via `includes` auto-add, suppressed when the Stripes section already has a user pick — so e.g. SNE + 17A combine into an invalid order with no Z15.

## Outcome rubric

- Workbook gains 5 new `excludes_any` groups (`gs_group_<rpo>_excludes_heritage_hash_and_z15` for sht/pda/sne/vpo/vpw), each targeting Z15 + the 6 heritage hash marks.
- Schema gate valid; grand-sport node gates + multi-model-runtime-switching green; pytest metadata gate green.
- Browser-proven: each of the 5 sources (SHT, PDA, SNE, VPO, VPW) disables all 6 hash marks + Z15 with the correct disabled-reason copy when selected; deselecting re-enables; pre-existing reverse direction (hash-mark-first blocking SNE/SHT/VPO via Z15's existing group) unaffected.

## Result: PASS

Spec: `.hermes/plans/grand-sport-jake-heritage-hash-reverse-exclusions-spec.md`. 40 ops (5 groups + 35 members) applied via `apply_workbook_ops.py --write` (dry-run clean, then write; workbook mtime guard bypassed with `--allow-stale` since the batch was authored fresh against current disk state, not a stale export). Verified rows on disk via openpyxl re-read. Regenerated grand_sport + registry. All gates green (see `validation-output.txt`). Browser-proven all 5 sources individually via `javascript_tool` DOM inspection (screenshot rendering was flaky in this session's Browser pane; accessibility-tree/DOM state was used as the verification source of truth instead, which is a stronger signal than pixels for a disabled-state/reason-text check).

## Non-goals confirmed out of scope

- PDA and VPW are not currently disabled by Z15 selection (Z15's own reverse group only targets stripes) — pre-existing, unrelated gap, not touched.
- VPO/VPW's existing Jake-to-Jake exclusions untouched.
