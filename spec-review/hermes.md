Here’s a codebase-aligned rewrite:

---

**Audit the 27vette workbook source graph for structural drift between the Stingray and Grand Sport model pipelines. Focus on workbook-authored source sheets, model-specific metadata sheets, generated `form_*` sheets only as outputs, and the downstream JSON/data artifacts they produce.**

Compare the Stingray and Grand Sport structures for:

1. **Header and schema consistency**
   - Identify column/header naming differences across equivalent sheets or sheet roles.
   - Classify discrepancies by semantic similarity, not just exact string matching.
   - Flag headers that appear to represent the same concept but use different names, formats, casing, abbreviations, or value conventions.
   - Note where differences are intentional model-specific metadata versus accidental schema drift.

2. **Data type and value-shape consistency**
   - Compare equivalent columns for data type differences, including strings, booleans, numeric values, lists, delimited values, blank/null conventions, RPO references, section IDs, variant keys, and status flags.
   - Identify places where the same logical field is represented differently between Stingray and Grand Sport.
   - Call out values that may be difficult to ingest cleanly into a NoSQL/JSON structure without normalization.

3. **Key-value alignment and source graph consistency**
   - Trace how workbook rows map from source sheets through generated `form_*` sheets and into the generated runtime data artifacts.
   - Identify differences in key naming, identifier composition, variant scoping, section/category mapping, rule-group membership, option status rows, and workbook metadata ownership.
   - Look for equivalent business concepts that use different source sheets, different linking keys, or different intermediate representations.

4. **Rule, compatibility, and dependency path comparison**
   - Compare how Stingray and Grand Sport encode equivalent business outcomes such as includes, requires, excludes, exclusive groups, default selections, standard options, soft defaults, variant overrides, and required choice groups.
   - Identify cases where both models reach the same runtime behavior through different workbook or generator paths.
   - For each divergent rule path, determine the most common or most repeatable representation in the codebase.
   - Prefer workbook-authored, data-driven structures over hardcoded model/RPO-specific Python or JavaScript logic unless the existing code clearly requires otherwise.

5. **Repeatability and ingestion readiness**
   - Evaluate which structures are consistent enough to become a repeatable parser/normalizer for online order guide data.
   - Identify unconventional order-guide-derived information that currently requires special handling.
   - Recommend candidate normalization rules for eventual NoSQL/JSON ingestion, including proposed canonical field names, expected data types, nested object shapes, and relationship keys.

**Objective**

Produce a detailed audit report that helps back-engineer a repeatable method for reading, normalizing, and processing unconventional information from the online order guide layout into workbook-owned source data and, eventually, NoSQL/JSON-ready records.

The report should separate:

- confirmed structural inconsistencies,
- semantically equivalent but differently named headers,
- data type/value-shape mismatches,
- alternate rule paths that produce the same behavior,
- likely intentional model-specific differences,
- risky hardcoded or generated-output-only logic,
- recommended canonical schema conventions,
- open questions requiring human review.

Do not modify the workbook, generated `form_*` sheets, generator scripts, runtime files, or generated app data during this audit. This is a report-only pass unless explicitly approved otherwise.
