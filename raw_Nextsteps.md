Next steps:

Temporarily unpromote GSX, ZR1, and ZR1X.
Keep all workbook sheets, model data, assets, and contracts.
Set publication off and regenerate form-app/data.js.
This gives us a stable customer form while repairs continue.

Retire only proven one-use recovery machinery.
Strong candidates are options_recovery_projection.py, options_recovery_changeset.py, their dedicated tests, the 7/20 recovery spec, and the obsolete README commands.
Keep the generic compiler, workbook service, promotion tooling, and tests that protect real runtime contracts.
Don’t delete Fable receipts or tests merely because they are annoying; confirm they have no active caller or contract first.

Clean actual disk clutter separately.
form-output/ currently occupies about 1 GB.
The specs are under 1 MB and tests about 5 MB, so deleting them won’t meaningfully reclaim disk space. Their cleanup is about cognitive clarity, not storage.

Run one main-safety check, limited to:
Workbook package/schema validity.
Stingray, Grand Sport, and Z06 generation.
Registry/model switching confirming the three unfinished models are absent.
No “prove the repaired models are correct” gates, because we already know they aren’t.

Squash-merge the stabilized branch into main.
The branch is clean but currently 86 commits ahead of origin/main.
Keep origin/ingest-wizard as the historical archive, while main gets one comprehensible checkpoint.

Revisit PR #8 from the new baseline.
The SQLite architecture is genuinely promising: workbook-shaped tables, foreign keys, row provenance, typed findings, and guarded workbook synchronization. PR #8
It can help catch dangling option IDs, broken exclusive-group references, incomplete variant coverage, invalid sections, duplicate identities, and inconsistent table families.
It cannot independently determine whether product copy, pricing, UQT behavior, or defaults are correct; those remain workbook/business decisions.

Before merging PR #8, three bounded corrections are needed:
Fix the current P1: restore the workbook backup if post-save verification fails.
Reconcile its duplicate schema registry with workbook_domain.registry.
Replace its hard-coded “three live models/65 sheets” assumptions so it can import and validate inactive GSX/ZR1/ZR1X without promoting them. The previous merge simulation already showed the compiler handles the expanded workbook; seven failures were stale inventory expectations, not structural failures. PR review details
Then we start a fresh model-rehabilitation branch from the updated main, using both the local form and database findings as review surfaces. That is a much cleaner place to fully unfuck the three models than continuing on this branch.