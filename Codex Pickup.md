# Codex Pickup

We were working in `/Users/seandm/Projects/27vette` on the Stingray CSV/shadow migration control plane. The latest completed work was **Pass 126: human-readable migration status report**. It generated a workspace audit bundle at `pass126-migration-status-report/` with:

- `migration-status-report.md`
- `csv-owned-projected.csv`
- `production-owned-not-projected.csv`
- `cross-boundary-relationships.csv`

Key decisions:

- CSV/shadow remains experimental only; no source switch or runtime cutover.
- Production behavior remains the oracle.
- Reporting is audit-only and non-decisional.
- “CSV-owned/projected” means currently emitted/owned by the shadow CSV migration package.
- “Production-owned/not-projected” means still coming from old generated production data, not necessarily bad or missing.
- Cross-boundary relationships are split between current guarded dependencies and manifest-only preservation rows.
- Decision ledger review should happen only after reading the migration status map.

Current reconciled Pass 126 counts:

- CSV-owned/projected: 68
- Production-owned/not-projected: 147
- Cross-boundary relationship rows: 122
- Current guarded dependencies: 43
- Manifest-only preservation rows/groups: 83 / 78
- Invalid preserved rows: 0

Direction:

- Continue spec-first, evidence-backed, narrow control-plane/report passes before any implementation migration.
- Use the Pass 126 report to understand migration status by category/section, then use the Pass 125 decision ledger for human review notes.
- Do not apply ledger decisions or migrate anything until explicitly approved.

Open next steps:

- Review `migration-status-report.md` and the three CSV sidecars.
- Decide which category/section areas need manual review first.
- Potential next pass: make the migration status report reproducible via a small checked-in helper/test if we want to freeze it, or start reviewing ledger rows using the status report as context.

Important user/business context:

- You are Sean, Corvette specialist at Stingray Chevrolet in Plant City, FL.
- You’re building structured Corvette order/configuration systems and prefer careful, stepwise, evidence-backed migrations with strict scope control and tests.
