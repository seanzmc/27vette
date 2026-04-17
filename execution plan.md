# Script Séance-style execution plan for the 2027 Corvette workbook

Here's what I found, then the flow I'd recommend. I'll keep this practical — agent prompts you can paste into Codex/Claude Code, your actions between them, and the optimizations that move you toward a customer-facing ordering form fastest.

## Where you actually are right now

This is more built out than the roadmap implies. Treating the roadmap as "where we're going" and the workbook as "where we are":

| Clean sheet | Populated rows | State |
|---|---|---|
| Option Catalog Clean | 271 | **Mostly migrated.** 111 rows are parked in `Option Catalog Identity Review` waiting for a judgment call |
| Option Price Scopes Clean | 5 real | **Pilot only** (AE4 proof of concept). Not migrated. |
| Option Rules Clean | 43 real | **Pilot only.** Legacy Option Rules has 693 review-level rows flagged in Audit Exceptions |
| Choice Groups Clean | 15 real | **Partial.** Mostly AE4/AH2 interior scaffolding |
| Choice Group Members Clean | 71 real | **Partial.** Same scope as above |
| Variant Catalog | 26 | **Complete** (all 2027 variants exist) |
| Data Dictionary Clean | 53 | **Current** |
| Audit Exceptions | 5 active | 3 already resolved |

So the real status is: **Option Catalog identity migration is the only category that's more than a pilot.** Pricing, rules, and choice groups are proof-of-concept only. That's important because it tells you where agent work actually saves you time vs. where you need to make structural decisions yourself first.

## The critical reframe for your customer-facing form goal

Your end goal is a form that lets a customer pick a variant and get a valid, priced build. Working backwards, the form needs three things:

1. **For any variant, the list of options that can appear** → `Variant Option Matrix`
2. **For any option in any context, a price** → `Price Resolver`
3. **For any choice group in a variant, the valid members** → `Variant Choice Availability`

All three helper sheets depend on the same five clean sheets being trustworthy. So the fastest path to a form is not "finish every clean sheet completely" — it's **"get each clean sheet trustworthy for one model family, build the helpers for that family, ship a form for that family, then replicate."**

That's the Phase 3 pressure-test the roadmap mentions, but scoped as a shippable slice rather than an academic proof. This matters because the AE4/AH2 interior work is already the proof of concept — it just isn't wired through to a form yet.

## Recommended execution flow

I'd organize this into **five agent runs**, each gated by your review. I'm modeling these after the two-phase agent spec pattern you use for Script Séance (Phase 1: report → you review; Phase 2: implement).

### Run 1 — Resolve the Identity Review queue (your action, agent-assisted)

**Why first:** 111 options are sitting in `Option Catalog Identity Review` labeled things like "reference_only_nonselectable" and "generic naming needs human judgment." Every downstream sheet that references an option can only reference options that exist in the canonical catalog. Moving these forward or explicitly rejecting them unblocks everything else.

**Agent prompt (Phase 1 — report):**

```
Read Option Catalog Identity Review. Group the 111 skipped rows by skip_reason.
For each group, produce:
- the skip_reason
- the count
- 3 representative example rows
- a recommended disposition (promote to catalog | keep as reference_only row in
  catalog with flag set | leave out entirely)
- the rationale

Do not modify any sheets. Output a single markdown report I can review.
Validation: this is a read-only pass. No writes.
```

**Your action after review:** Tell the agent which dispositions to apply per group.

**Agent prompt (Phase 2 — implement):** Write the approved rows into Option Catalog Clean with appropriate `reference_only_flag` / `form_selectable_flag` values, preserve provenance in `notes`, and clear the Identity Review queue for resolved rows.

---

### Run 2 — Pick one model family and scope the slice

**Why:** The roadmap says "start with one model family" for presentation, but the same discipline should start at the canonical layer. Trying to migrate all 963 rows of Options Master at once is where accuracy dies. Stingray is the natural choice — highest volume, most trim variety, and your existing AE4 pilot is Stingray-applicable.

**Your action (no agent yet):** Decide scope. I'd propose:
- **Family:** Stingray (Coupe + Convertible, 1LT through 3LT)
- **Categories, in this order:** Mechanical → Wheels → Exterior colors → Interior (seats + color/trim) → Equipment Groups → Standard Equipment
- **Explicitly out of scope for Run 2:** Z06, ZR1, ZR1X, Grand Sport, special heritage packages

This scope gives you ~8 variants and a manageable option universe per category. If the flow works end-to-end for Stingray, replicating for other families is mechanical.

---

### Run 3 — Migrate Option Rules for the Stingray slice

**Why before pricing:** Rules determine which options are even *offered* in a variant. Pricing a nonexistent option wastes cycles. Also, Audit Exceptions flagged 693 "review-level rules" from the legacy sheet — most of these are probably soft language ("available with") that the roadmap explicitly says does not belong in Option Rules Clean. An agent can triage these.

**Agent prompt (Phase 1 — report):**

```
   Context: we are migrating Option Rules from the legacy "Option Rules" sheet into
   "Option Rules Clean" for Stingray variants only (var_stingray_coupe_1lt through
   var_stingray_convertible_3lt — see Variant Catalog).

   Read:
   - Option Rules (legacy, 723 rows)
   - Option Catalog Clean (to confirm options exist canonically)
   - Audit Exceptions (note the 693 review-level warning)
   - workbookRoadmapV2.md section "Option Rules Clean" for what belongs vs. does not

   Produce a markdown report with three sections:
   1. Rules that cleanly map to rule_type in (requires | excludes | includes |
      not_available_with) and have both source and target options present in
      Option Catalog Clean. Group by rule_type. Show counts.
   2. Rules whose source phrasing is soft ("available with", "typically paired with")
      and should NOT migrate as hard rules. Recommend: keep as notes on the option,
      or drop.
   3. Rules that reference options missing from Option Catalog Clean. These are
      blockers — list the missing RPOs.

   Do not write to any sheet.
```

**Your action:** Review the three buckets. The soft-language bucket is the judgment call — some "available with" phrasing is actually a hard requirement in disguise, and a Corvette Specialist reading it will know. Mark them.

**Agent prompt (Phase 2 — implement):** Write approved rules into Option Rules Clean with source provenance in notes, scoped to Stingray via `scope_type=trim` and `scope_value`. Flag any remaining ambiguity in Audit Exceptions rather than forcing it through.

---

### Run 4 — Migrate Option Price Scopes for the Stingray slice

**Why this structure:** The AE4 pilot proved the schema works. The question is how the source Pricing sheet organizes prices by trim — the roadmap's `scope_value` pattern (`1LT|1LZ`, `3LT|3LZ`) suggests the source already groups trims that share pricing, which is a gift. An agent can probably do most of this mechanically.

**Agent prompt (Phase 1 — report):**

```
Context: migrate Stingray pricing from the "Pricing" and "Option Pricing" sheets
into "Option Price Scopes Clean". Follow the AE4 pattern already in the clean
sheet (see ps_clean_ae4_3lt3lz as reference).

Read the Pricing and Option Pricing sheets and produce a report:
1. How many distinct (option, trim-scope) combinations exist for Stingray options
   that also appear in Option Catalog Clean?
2. Which rows have clean trim-scoped prices (direct match to the AE4 pattern)?
3. Which rows have pricing that depends on other RPOs (would need
   condition_rpos_all or condition_rpos_any)?
4. Which rows have no-charge / included-standard entries? These need
   price_mode=no_charge or included.
5. Which rows are ambiguous or have soft pricing commentary?

Do not write. Group findings and flag blockers.
```

**Your action:** Approve Category 1–4 bulk migration; decide category-by-category on Category 5.

**Agent prompt (Phase 2 — implement):** Write bucket 1–4 rows into Option Price Scopes Clean. Anything ambiguous goes to Audit Exceptions, not forced into the clean sheet.

---

### Run 5 — Migrate Choice Groups + Members for the Stingray slice

**Why last among the clean sheets:** Choice groups are the trickiest because scope matters — the same RPO can legitimately appear in multiple groups (seat color in 1LT textile context vs. 3LT Nappa context). The AE4/AH2 interior pilot is exactly this pattern, so the template exists.

The categories to cover for Stingray:
- Seat options (GT1/GT2/Competition Sport)
- Interior color groups (scoped by seat choice, per the AE4 pattern)
- Exterior color groups (scoped by trim if prices differ)
- Wheel groups (scoped by trim)

**Agent prompt structure:** Same two-phase pattern — read `Color Trim Seats`, `Color Trim Matrix`, `Color Trim Combos` for interior; `Wheels 1-4` for wheels; `Exterior 1-4` for colors. Report proposed groups before writing.

---

### Run 6 — Build Variant Option Matrix (the bridge sheet)

This is the roadmap's "strongest recommendation" and for good reason: once it exists for Stingray, you can *see* your form. Every row is "for this variant, this option, here is its status, price, and constraints" — which is almost literally the form's data model.

**Agent prompt (Phase 1 — plan):**

```
Read workbookRoadmapV2.md section "Variant Option Matrix". Read all clean
canonical sheets. Read Variant Catalog filtered to Stingray variants.

Produce a plan for generating Variant Option Matrix rows. Specifically:
- the join logic from Variant Catalog × Option Catalog Clean
- how to resolve standard_flag, available_flag, orderable_flag,
  included_flag from Option Rules Clean
- how to pull resolved_price from Option Price Scopes Clean including
  fallback order when multiple scopes could apply
- how to populate choice_group_id from Choice Groups Clean given
  scope filtering
- what display_status each row should get per the roadmap's standardized
  values (Standard | Included | Optional | Package Only | Conditional |
  Not Available | Reference Only)
- which fields will be computed later vs. blank initially

Output as markdown. Do not write.
```

Once this plan is sound, Phase 2 writes the matrix, and that matrix is directly exportable to your form.

## Optimizations I'd add that aren't in the roadmap

A few things that will save you pain:

**Build an `Option Catalog Clean` lookup formula column in the legacy Option Rules and Option Pricing sheets.** Before any migration, add a helper column that does `XLOOKUP` against Option Catalog Clean by RPO. Every row that returns `#N/A` is a row that can't migrate because its option doesn't exist canonically yet. This gives you a migration readiness score per sheet at a glance, and catches the "blocker" cases that Run 3 surfaces without needing to run an agent.

**Treat `Audit Exceptions` as your real progress tracker, not a quality gate.** Right now it has 3 resolved and 5 open. After each run, the agent should append new exceptions (ambiguous rows it punted on) rather than silently dropping them. This makes "done" an honest state.

**Add a `scope_tested` flag to Variant Catalog.** A simple column marking which variants have end-to-end trust (all clean sheets populated, helpers built, form-ready). Stingray Coupe 1LT becomes your first true-flag variant. This is your replication checklist.

**Defer the customer-facing form work until Variant Option Matrix exists for one variant.** It's tempting to start the form now in parallel, but the form's schema is the matrix's schema. Once the matrix is right for Stingray Coupe 1LT, Formidable Forms / WordPress wiring is almost mechanical.

**For agent specs, name the validation gates explicitly.** In your Script Séance spec pattern you use `pnpm typecheck / lint / test`. For workbook agents, the equivalent validation gates are: (a) does every `option_id` in the written sheet exist in Option Catalog Clean, (b) does every `choice_group_id` in members exist in Choice Groups Clean, (c) do row counts in Audit Exceptions only go up (never silent drops). Codex/Claude Code should be told these explicitly so they check before declaring success.

## What to do right now

If you want to pick this up today, **Run 1** is the right starting point — it's the cheapest run, it unblocks everything, and most of the work is your judgment on 111 rows grouped into maybe 4-6 skip_reason buckets. You'll probably clear it in under an hour.

Want me to draft the actual Codex/Claude Code agent spec markdown file for Run 1 in your usual two-phase format so you can drop it straight into the tool?
