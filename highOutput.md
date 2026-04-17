I’m auditing the current architecture, then I’ll write the config sheets.

First pass done. Now I’m sampling canonical and staging schemas.

The runtime summary misfired, so I’m switching to exact range reads.

Key schema read is in. Now I’m sampling the legacy and staging tabs.

I’ve got the samples. Next I’m calculating cross-sheet exceptions.

I found the structural issues. One more pass is comparing base model coverage.

Audit is scoped. I’m creating the derived/config tabs now.

I’m writing the index, audit log, and helper-sheet schemas in one pass.

Write is in. I’m doing a quick verification pass on the new tabs.

**Done**
- I audited the current architecture, preserved all raw/staging tabs, populated `Workbook Index` with a config plan plus full sheet inventory, and created the new helper sheets: `Variant Option Matrix`, `Price Resolver`, `Package Composition`, `Variant Choice Availability`, and `Audit Exceptions`. (`Workbook Index!A1:E64`, `Variant Option Matrix!A1:H6`, `Price Resolver!A1:H6`, `Package Composition!A1:H6`, `Variant Choice Availability!A1:H6`, `Audit Exceptions!A1:M17`)
- I also logged the audit summary and eight open exceptions with provenance; no sheets were deleted in this pass. (`Audit Exceptions!A1:M17`, `Workbook Index!A8:B8`)

**Layers**
- Raw (29): `Pricing`; `Standard Equipment 1-4`; `Equipment Groups 1-4`; `Interior 1-4`; `Exterior 1-4`; `Mechanical 1-4`; `Wheels 1-4`; `Color and Trim 1-2`; `Dimensions`; `Specs`. Legacy (5): `All` and `All 1-4`. (`Workbook Index!A11:E44`)
- Staging (7): `Options Master`, `Options Long`, `Option Pricing`, `Color Trim Notes`, `Color Trim Seats`, `Color Trim Matrix`, `Color Trim Combos`. Canonical (7): `Variant Catalog`, `Order Schema Map`, `Option Catalog`, `Option Rules`, `Option Price Scopes`, `Choice Groups`, `Choice Group Members`. Derived (6): `Workbook Index`, `Variant Option Matrix`, `Price Resolver`, `Package Composition`, `Variant Choice Availability`, `Audit Exceptions`. (`Workbook Index!A45:E64`)

**Open Decisions**
- The main calls still needing your decision are: whether `Grand Sport X` (`1YG07` / `1YG67`) belongs in the canonical `Variant Catalog`; how to complete missing `choice_group_id` rows and `grp_model_selection`; whether to promote `review` rules; and how to formalize package composition from current sources. (`Audit Exceptions!A10:M16`)
- Clean checks already passed: no duplicate canonical primary keys, no blank canonical PKs, and no broken option mappings from rules, price scopes, choice members, or option-pricing rows into `Option Catalog`. (`Audit Exceptions!A3:D5`)

**Next Step**
- Best next build step: resolve AX-004 plus AX-001/002/003 first, then populate `Variant Option Matrix` as the first derived truth surface; after that, build `Price Resolver` and `Variant Choice Availability`. (`Workbook Index!A6:B7`, `Variant Option Matrix!A3:B4`, `Price Resolver!A3:B4`, `Variant Choice Availability!A3:B4`)

If you want, I can take the next pass by normalizing the variant/choice-group decisions and then building the first populated derived tables.
