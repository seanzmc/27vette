Use the 27vette skill and configure this workbook according to that architecture.

This workbook currently contains raw source tabs, staging tabs, and some half-built processed tabs. Do not treat all sheets as equally authoritative.

For this pass, treat these sheets as canonical unless you find a confirmed conflict:
- Order Schema Map
- Variant Catalog
- Option Catalog
- Option Rules
- Option Price Scopes
- Choice Groups
- Choice Group Members

Treat these as staging/reference only unless needed to backfill or validate:
- Option Pricing
- Pricing
- Options Master
- Options Long
- Color Trim Notes
- Color Trim Seats
- Color Trim Matrix
- Color Trim Combos
- All / All 1-4
- Standard Equipment 1-4
- Equipment Groups 1-4
- Interior 1-4
- Exterior 1-4
- Mechanical 1-4
- Wheels 1-4
- Dimensions
- Specs

My current most promising workflow begins with:
- Order Schema Map
- Option Pricing
- Option Catalog
- Option Rules

Your task for this pass:
1. Audit the workbook structure against the skill architecture.
2. Identify which existing sheets already align with the canonical model and which are redundant, staging, legacy, or partially processed.
3. Do not delete anything yet.
4. Create a clear workbook configuration plan inside the workbook.
5. Add or update these sheets if needed:
   - Workbook Index
   - Variant Option Matrix
   - Price Resolver
   - Package Composition
   - Variant Choice Availability
   - Audit Exceptions
6. Populate Workbook Index with:
   - sheet name
   - layer (raw, staging, canonical, derived, presentation, legacy)
   - role/purpose
   - trusted as source of truth? yes/no
   - recommended action (keep, refine, derive from, retire, review)
7. Populate Audit Exceptions with conflicts, duplicates, missing IDs, missing mappings, ambiguous rules, and pricing issues.
8. Preserve raw data.
9. Preserve provenance when comparing conflicts.
10. Do not hardcode business logic into presentation sheets.

After making changes, summarize:
- what sheets were classified into each layer
- what new helper sheets were created
- what conflicts or ambiguities still need my decision
- what the next best build step should be
