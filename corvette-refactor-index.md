# Corvette Skill Refactor Index

This refactor leaves the current skill files untouched and introduces a replacement document set that closes the gaps called out in [criticalReview.md](/Users/seandm/Projects/27vette/criticalReview.md:1).

## File Set

1. [corvette-contract/sharedContractV2.md](/Users/seandm/Projects/27vette/corvette-contract/sharedContractV2.md:1)
   Shared operating contract. This is the dependency root for the refactor.

2. [corvette-ingest/ingestSkillV2.md](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkillV2.md:1)
   Replacement ingest skill spec built on the shared contract.

3. [corvette-build/buildSkillV2.md](/Users/seandm/Projects/27vette/corvette-build/buildSkillV2.md:1)
   Replacement build skill spec that consumes the revised ingest outputs.

## Dependency Order

The files are intentionally ordered by what unlocks the remaining work:

1. Shared contract
   This resolves cross-skill blockers first: workbook substrate, model-year boundaries, canonical variant scope, ID conventions, rerun policy, and exception gating.

2. Ingest V2
   This closes the source-shape and schema gaps. Build cannot be made deterministic until ingest emits a stable, explicit contract.

3. Build V2
   This consumes the revised ingest outputs and defines deterministic row generation, UI metadata authoring, pricing behavior, and validation coverage.

## What Changed

- Added a shared contract instead of duplicating cross-skill rules in two separate files.
- Expanded the ingest contract to define Standard Equipment, Equipment Groups, price schedule staging, legend parsing, note provenance, and enriched Color and Trim outputs.
- Expanded the build contract to define row-generation rules, collapse/split rules, UI metadata derivation, equipment-group handling, and explicit D30/R6X pricing behavior.

## Migration Intent

These files are written as replacement specs, not supplements. If you later want to promote them into the active skill set, the expected sequence is:

1. Review [corvette-contract/sharedContractV2.md](/Users/seandm/Projects/27vette/corvette-contract/sharedContractV2.md:1)
2. Validate [corvette-ingest/ingestSkillV2.md](/Users/seandm/Projects/27vette/corvette-ingest/ingestSkillV2.md:1)
3. Validate [corvette-build/buildSkillV2.md](/Users/seandm/Projects/27vette/corvette-build/buildSkillV2.md:1)
4. Decide whether to replace the current active skill files or keep both generations side by side
