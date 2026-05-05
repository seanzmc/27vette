# Chat Pickup

We were working on the 27vette Stingray CSV/shadow migration, specifically trying to understand the current migration state and whether the new CSV-owned data has actually captured the old/generated relationships.

Key decisions/clarifications:

- Production/generated behavior remains the oracle.
- No source switch, runtime cutover, manifest edits, workbook/generator/app/generated artifact changes, or migration was performed.
- The recent Pass 103–125 work built a control-plane/reporting/review system, not the actual migration.
- The “manifest” is a migration safety checklist, not runtime app logic.
- “Projected/CSV-owned” means the shadow CSV migration currently owns/emits that option row.
- “Production-owned/not-projected” means the option row still comes from old generated data.
- The decision ledger is not for deciding whether valid legacy relationships should be deleted. The safer default is essentially protect_until_migrated until both sides and the relationship itself are represented in CSV and tested.
- Current ledger terms like preserve / migrate_later are not ideal and may need replacement.

Where we landed:

- The uploaded migration-status-report.md is useful for option-row status:
  - 68 CSV-owned/projected RPO rows
  - 147 production-owned/not-projected RPO rows
  - 122 preserved cross-boundary manifest rows
  - 43 current guarded dependencies
  - 83 manifest-only preservation rows / 78 groups
  - 0 invalid preserved rows
- But it does not answer the critical question: whether each old relationship itself is already represented in the new CSV/rules/package data.

Direction heading next:

- Pause manual ledger review.
- Build Pass 127: relationship coverage map.
- Goal: compare preserved relationships against actual data/stingray/ CSV/rules/package files and report whether each relationship is covered, partially covered, missing, or needs mapping.
- Needed output should include:
  - relationship-coverage-report.md
  - relationship-coverage-by-group.csv
  - data-stingray-file-inventory.csv
  - relationship-file-inventory.csv

Open questions/next steps:

- Which data/stingray/ files are real rule/package/relationship files vs placeholders/control-plane files?
- Which files are actually consumed by scripts/tests/runtime?
- For each preserved relationship, what type is it: include, requires, conflict, auto-add, price rule, choice group, availability, etc.?
- Where, if anywhere, is that relationship already represented in the new CSV schema?

Important context:

- I’m Sean, Corvette specialist at Stingray Chevrolet in Plant City, building structured Corvette order/configuration systems.
- I am frustrated by the slow migration and need plain-English status maps, not abstract control-plane language.
- I need the tooling to prove what is migrated instead of asking me to infer it manually.
