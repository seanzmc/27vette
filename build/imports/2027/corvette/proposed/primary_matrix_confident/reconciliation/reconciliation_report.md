# Canonical Reconciliation Report

Canonical reconciliation report only. canonical_apply_ready=false.

This is a reconciliation report only. It compares confident subset proposal artifacts to canonical CSV context and does not apply rows.

## Selected Human Decisions

```json
{
  "availability_schema_policy": "availability_selectable_variant",
  "first_apply_boundary": "boundary_reconciliation_first",
  "proposal_metadata_policy": "metadata_import_audit",
  "section_mapping_policy": "section_import_map",
  "selectable_id_policy": "selectable_id_model_rpo",
  "source_refs_policy": "source_refs_member_table"
}
```

## Summary

- canonical_apply_ready=false
- covered canonical models: `stingray`
- matched selectables: `48`
- new selectable candidates: `100`
- conflicting selectables: `85`
- apply blockers: `6`

## Recommended Next Step

Resolve section mapping, canonical availability/source-ref schemas, ambiguous matches, and non-covered model context before any apply.

No canonical rows were generated or applied.
