Audit findings — your complaints all confirmed, with numbers
Probed all *_options sheets (read-only). Against z06 as the clean reference:

gsx: 237/247 rows have description == detail_raw (identical all the way down, exactly as you said); 51 rows where name==description too; 49 rows named literally LPO; 113 stub names ≤12 chars (Wheels, Seats, Calipers, Frame, Glass…); 32 names containing newlines with full disclosure text inside (max name length 559 chars); 237/247 null display_order; only 1 active=False (vs 3 grandSport / 5 z06); all 26 no-RPO rows carry opt_std_<16-hex> ids (z06 uses opt_NNN).
zr1/zr1x: 98 names >60 chars each — the compiler's update actions clobbered the previously curated scaffold names with raw export text (ZR1 TDM is now a 200-char Teen Driver paragraph). 11–12 priced non-selectable standard rows each (engine appearance packages etc.), matching your price complaint. One hex id each.
Root causes — all mechanical, all located
compiler.py:1552 — the canonical compiler derives option_name with a naive split(",", 1)[0] and sets description and detail_raw to the same full raw string. The correct rules (LPO second-segment, NEW!+ strip, disclosure split) exist in copy_split.py and are tested — but only the legacy decisions/plan path calls them. The Milestone-1+ compiler never does. That one line is most of the mess.
identity.py:181 — no-RPO rows get opt_std_<sha16> instead of the z06 sequential convention.
compiler.py:1547 — display_order = existing-else-blank; greenfield GSX had no existing, so blank.
active is derived from status math, not decisions — your per-option instructions had no lane.
Your 45 choose_section resolutions are intact in run 20260717-091317-470292 with exact sectionIds — but nothing ever reconciled decided-vs-landed, which is why placements are wrong with no trace.
Spec written
options-sheet-quality-remediation-spec.md — four deliverables in strict order:

A. Lint gate first — permanent pytest gate encoding the column contract (§3) with executable predicates, so drift becomes a test failure forever. Lands before any repair so the repair is graded by it.
B. Read-only reconciliation report — decided-vs-landed sections, copy repair previews, id-rename cascade (renames ripple into *_ovs/rules/prices — spec handles it), display_order proposals, active/price review lanes, and ZR1/ZR1X curated-name restore diffed from the pre-281eb14 workbook in git history. You review once → Checkpoint 1.
C. One bounded repair changeset through the existing editor_ops/safe-save path, dry-run first → Checkpoint 2 before live write.
D. Compiler fixes + forced-branch regression tests so the next run can't reproduce this.
Independent verifier ran, failed my first draft on three real errors (a phantom-row artifact from your in-progress workbook edit corrupted one reference column — good catch), fixes applied, re-verification in flight. One thing to compare against Codex's spec: whether it catches the copy_split-bypass root cause and the id-rename referential cascade — those two are where a shallow spec would send this further down the hole.

Also flagged in STATE: commit 281eb14 wrote the workbook with no run receipt, against Milestone 3's own no-live-write line. Needs your say-so on whether that was intended.

Background agent completed
Independent verifier for audit spec run
· took 56s
Verifier died on API error. Checking partial output, then resuming.

Read partial verifier output
Discrepancy persists in their probe (13 vs my 8). Settling it by enumeration.


Ran 2 commands, edited a file, used a tool
Re-verification resumed with reconciled evidence. Key new fact from the discrepancy hunt, worth knowing now: your in-progress workbook edits are visible — 5 of gsx's 13 unpriced selectable rows now carry your zero-fills. Spec updated so the repair treats your manual edits as reviewer decisions to preserve, never drift to revert. Will finalize receipt verdict when verifier returns.

PASS. Finalizing receipt + correcting one wording detail (DTC fill is 1295, not zero).


Edited 3 files, created a file, ran a command
Done. Verifier PASS on cycle 2, loop validator green, receipt complete.

Final state:

Spec: options-sheet-quality-remediation-spec.md — verifier-passed, every §1 number reproduced independently, every predicate executable (they become the lint rules verbatim). Order: A lint gate → B read-only reconciliation report (your 45 section decisions vs landed, copy previews, id-rename cascade, ZR1/ZR1X curated-name restore from git history) → your Checkpoint 1 → C one bounded repair changeset, dry-run, your Checkpoint 2 → D compiler fixes with regression tests.
Root causes (verifier-confirmed): compiler.py:1552 bypasses copy_split entirely — that one emission block is most of the mess; identity.py:181 hex ids; display_order blank for greenfield; active derived not decided.
Verifier earned its keep twice: caught a phantom-row artifact (openpyxl trusts stale sheet dimensions from external editor saves — corrupted my first grandSport numbers), and surfaced that your in-progress edits are already visible in the workbook — 5 gsx price fills (AQ9/CF7/CM9/R9W → 0, DTC → 1295). Spec now mandates the repair diff against the live workbook at execution time and treat your manual edits as decisions to preserve, never drift to revert.
Receipt: fable5loop/runs/2026-07-20-options-sheet-quality-audit-spec/ complete; STATE.md updated.
When comparing against Codex's spec, the two make-or-break items: does it find the copy_split bypass at compiler.py:1552 (versus prescribing new copy rules from scratch), and does it handle the option_id rename cascade into *_ovs/rules/prices (renaming hex ids without the cascade breaks every reference). Next move is yours: pick a spec, then deliverable A starts.