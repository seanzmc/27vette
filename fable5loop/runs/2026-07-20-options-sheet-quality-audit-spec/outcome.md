# Outcome rubric — options sheet quality audit + remediation spec

Docs-only pass. Graded criteria:

1. Every complaint in Sean's notes is either confirmed with a tool-verified number or explicitly rebutted with evidence. (Confirmed — see `audit-metrics.md`; the one nuance: some priced non-selectable rows are legitimate mandatory charges, recorded as a review lane not a blanket rule.)
2. Each defect is traced to a specific code location, not a narrative. (Confirmed: `compiler.py:1552-1554`, `compiler.py:1547`, `identity.py:181`, copy_split consumer gap.)
3. The spec's fix order puts the regression gate before the repair, so the repair is graded by the gate and drift cannot silently recur.
4. The spec requires reconciliation of Sean's 45 `choose_section` resolutions against landed rows before any repair write.
5. No workbook, generated-artifact, runtime, or dealer surface changed in this pass.
