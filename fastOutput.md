I’ll load the 27vette guidance, audit the key tabs, then build the configuration sheets.

Audit is clear. Now I’m creating the control sheets and logging the first-pass architecture decisions.

Small shape issue on the batch write. I’m patching that and verifying the new tabs immediately after.

**Done**
- I audited the current architecture and added the configuration/control layer directly in the workbook.
- New sheets created: `Workbook Index`, `Variant Option Matrix`, `Price Resolver`, `Package Composition`, `Variant Choice Availability`, and `Audit Exceptions` (`Workbook Index!A1:H12`, `Variant Option Matrix!A1:L2`, `Price Resolver!A1:L2`, `Package Composition!A1:J2`, `Variant Choice Availability!A1:L2`, `Audit Exceptions!A1:H13`)

**Layer Classification**
- **Canonical:** `Order Schema Map`, `Variant Catalog`, `Option Catalog`, `Option Rules`, `Option Price Scopes`, `Choice Groups`, `Choice Group Members` (`Order Schema Map!A1:H17`, `Variant Catalog!A1:M27`, `Option Price Scopes!A1:Q40`, `Choice Groups!A1:J12`, `Choice Group Members!A1:F61`)
- **Staging:** `Option Pricing`, `Pricing`, `Options Master`, `Options Long`, `Color Trim Notes`, `Color Trim Seats`, `Color Trim Matrix`, `Color Trim Combos`, `Color and Trim 1-2` (`Option Pricing!A1:O40`)
- **Raw:** `Interior 1-4`, `Exterior 1-4`, `Mechanical 1-4`, `Wheels 1-4`, `Dimensions`, `Specs`
- **Legacy:** `All`, `All 1-4`, `Standard Equipment 1-4`, `Equipment Groups 1-4`
- **Presentation / control:** `Workbook Index`
- **Derived scaffolds:** `Variant Option Matrix`, `Price Resolver`, `Package Composition`, `Variant Choice Availability`, `Audit Exceptions` (`Workbook Index!A1:H12`)

**What I Logged**
- `Workbook Index` now contains per-sheet layer, purpose, trust flag, and recommended action, plus an in-workbook configuration plan (`Workbook Index!A1:H12`)
- `Audit Exceptions` logs first-pass issues including:
  - partial / blank-key rows in `Choice Groups`
  - missing variant-scoped choice availability
  - duplicate pricing semantics between `Option Pricing` and `Option Price Scopes`
  - note-driven pricing/rule ambiguity
  - missing package composition bridge (`Audit Exceptions!A1:H13`)

**Conflicts / Ambiguities Needing Your Decision**
- `Choice Groups` has partially built rows without stable IDs below the clean canonical block (`Choice Groups!A7:J12`, `Audit Exceptions!A2:H2`)
- Exterior color and wheel choice groups exist, but variant-scoped availability is not normalized yet (`Choice Groups!A5:J6`, `Choice Group Members!A53:F61`, `Audit Exceptions!A3:H4`)
- Some pricing logic is still split between canonical scopes and note-derived staging interpretations, especially around seat pricing behavior like `AH2` (`Option Price Scopes!A29:Q31`, `Audit Exceptions!A8:H8`)

**Next Best Build Step**
- Best next move is to build `Variant Option Matrix` first from `Variant Catalog` + `Option Catalog` + `Option Rules` + `Option Price Scopes`, with provenance retained back to staging where needed. That will give us the explicit variant-by-option availability backbone needed before resolving prices and package composition (`Variant Option Matrix!A1:L2`, `Order Schema Map!A4:H15`)

If you want, I can do that next pass and populate `Variant Option Matrix` and `Price Resolver`.
