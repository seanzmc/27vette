# Outcome rubric · Grand Sport stripe ↔ heritage hash reverse exclusions

Task: selecting any full-length/stinger racing stripe on the Grand Sport form must deactivate the Grand Sport Heritage Hash Marks (and Z15), matching the already-working reverse direction. Workbook-owned fix only; no code changes; push to main (Sean, 2026-07-11, reported as crucial runtime bug).

Measurable done state:

1. Workbook: 16 `gs_group_<rpo>_excludes_heritage_hash_and_z15` excludes_any groups (sources = exact stripe subset of `gs_group_z15_excludes_non_center_stripes` targets), each with 7 active member targets (`opt_z15_001` + 6 hash marks).
2. Regenerated `form-app/data.js` + `form-output/runtime/grand-sport-runtime-contract.json` carry exactly those groups; diff contains nothing else besides `generated_at` and the edit-log line.
3. No changes to `form-app/app.js`, `styles.css`, dealer surfaces, or other models.
4. Gates green: grand-sport contract-preview + draft-data, multi-model-runtime-switching, pytest metadata gates, workbook schema gate.
5. Browser proof: DPB selected → all 6 hash marks disabled with the new reason copy; DPB deselected → re-enabled; 17A selected → stripes disabled (regression preserved).
6. Independent verifier PASS.

Result: all criteria met. Verifier verdict PASS (see verifier-report.md). Browser proof captured in-session (DPB selected: 17A/20A/55A/75A/97A/DX4 all `disabled`, reason "DPB blocks Grand Sport Heritage Graphics and Heritage Hash Marks."; deselect re-enables; 17A selected: DPB/DUB/DZU disabled).

Spec: `.hermes/plans/grand-sport-stripe-heritage-reverse-exclusions-spec.md`

Follow-up (out of scope, flagged as task chip): same latent gap for Jake graphics — SHT/PDA/SNE/VPO exclude Z15 but not the hash marks, so hash+Jake can combine into an invalid no-Z15 order via the same suppressed-auto-add path.
