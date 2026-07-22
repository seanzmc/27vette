# Options sheet quality audit — 2026-07-20, working-copy workbook

Read-only openpyxl probes (`read_only=True, data_only=True`, all-None rows excluded). Substrate: working-copy `stingray_master.xlsx` (Sean mid-edit); the three audited sheets + z06 verified content-identical to committed `a26c797` by the independent verifier — the working-copy delta is stale sheet dimensions on `stingray_options`/`grandSport_options` (phantom empty rows), which corrupted the first draft's grandSport row/display_order numbers until filtered. Full corrected metric table in `docs/ingest/options-sheet-quality-remediation-spec.md` §1.

Key measured facts:

- gsx: 51/247 `option_name==description`, 237/247 `description==detail_raw`, 32 multi-line names, 39 names >60ch (max 559), 237 null `display_order`, 49 rows named literally `LPO`, 26/26 no-RPO rows with `opt_std_<sha16>` ids, 1 `active=False`.
- zr1/zr1x: 98 names >60ch each (max 384) — curated scaffold names clobbered by compiler `update` actions; 11–12 priced non-selectable rows each; 1 hex no-RPO id each.
- Reference z06: 0 duplication, 0 oversize, 0 null display_order, 5 inactive, sequential `opt_NNN` no-RPO ids.
- Root cause code: `scripts/corvette_form_generator/ingest/wizard/compiler.py:1552-1554` (naive split; desc==detail), `identity.py:181` (hex ids), `compiler.py:1547` (display_order blank for greenfield). `copy_split.propose_copy_split` (correct LPO/NEW!/comma rules) consumed only by legacy decisions/plan_builder/session path, never by the canonical compiler.
- Sean's 45 `choose_section` resolutions exist with exact sectionIds in `form-output/ingest-wizard/20260717-091317-470292/exception-resolutions.json`; no decided-vs-landed reconciliation artifact exists.
- Section refs in all three sheets all resolve against `section_master` (no dangling ids).
