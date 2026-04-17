Use the 27vette skill.

Build the derived logic layer from the canonical sheets.

Primary goal:
Create and populate Variant Option Matrix as the central helper sheet.

Use:
- Variant Catalog
- Option Catalog
- Option Rules
- Option Price Scopes
- Choice Groups
- Choice Group Members

For this pass:
1. Create one row per variant_id + option_id where the option is relevant to that variant.
2. Include columns for:
   - variant_option_id
   - variant_id
   - option_id
   - rpo_code
   - model_family
   - body_style
   - trim
   - primary_section
   - option_kind
   - primary_name
   - standard_flag
   - available_flag
   - orderable_flag
   - package_only_flag
   - included_flag
   - choice_group_id
   - resolved_price if determinable
   - requires_count
   - excludes_count
   - includes_count
   - conditional_flag
   - display_status
   - review_flag
   - notes
3. If any logic cannot be confidently resolved, write the issue to Audit Exceptions.
4. Do not invent unsupported availability or pricing.
5. Preserve provenance where useful.

Afterward, summarize:
- how many rows were generated
- which fields were fully resolved
- where assumptions were avoided
- what dependencies remain before presentation sheets can be built
