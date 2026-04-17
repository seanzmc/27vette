Use the 27vette skill.

Now that the workbook has been classified, refine the canonical layer only.

Focus on:
- Variant Catalog
- Option Catalog
- Option Rules
- Option Price Scopes
- Choice Groups
- Choice Group Members

Tasks:
1. Check that stable IDs exist and are consistently used:
   - variant_id
   - option_id
   - rule_id
   - price_scope_id
   - choice_group_id
2. Flag duplicates, blanks, malformed IDs, and rows that appear to represent the same entity twice.
3. Do not delete source rows silently.
4. Where possible, normalize obvious duplicates or add helper columns that clarify canonical identity.
5. Move ambiguous cases to Audit Exceptions instead of guessing.
6. Preserve notes and provenance.

At the end, summarize:
- what was standardized
- what remains ambiguous
- which sheet is strongest now
- which canonical sheet still needs the most cleanup
