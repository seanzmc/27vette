# Chat Pickup

We were working on the 27vette Stingray CSV/shadow migration, converting production Excel/generated behavior into a modular CSV-owned data package while keeping form-app/data.js, app.js, the generator, workbook, and production artifacts untouched unless explicitly approved. We have been using a disciplined pass system: evidence/spec first, approval, then narrow implementation, with RED-first tests and the full Stingray ladder after each pass.

Key decisions:

- Production behavior remains the oracle.
- No source switch / no cutover yet.
- CSV projection is shadow/experimental only.
- Ownership must be explicit: projected-owned, production-guarded, preserved cross-boundary.
- Rule-only legacy IDs are not fake selectables.
- Package includes/priceRules only project when source and targets are projected-owned.
- RuleGroups only project when source and all emitted targets are projected-owned.
- Section metadata generally stays production-owned unless separately reviewed.

Major migrated/projected areas include Engine Appearance, center caps, suede trunk liners, car covers, spoiler choices (TVS, T0A, 5ZZ, 5ZU, 5V7) and grp_spoiler_high_wing, roof choices/defaults (CC3, C2Z, D84, D86, CF7, CM9), several LPO accessories, badge/script rows, SB7/SHT/SNG/SFZ/R88, PEF/CAV/RIA, PDY/RYT/S08, SBT/SC7, PCU/STI/VQK/VWE, and many focused tests.

Where we left off: Pass 102 was approved as a control-plane-only pass: add validation/tests so structured non-choice references must resolve to either an active choice, a guarded legacy option ID, or a valid data.interiors[].interior*id. The 30 3LT*\* IDs are valid interior source IDs, not missing options and not production_guarded rows. Next implementation should add tests/stingray/interior-source-namespace-control-plane.test.mjs or extend the non-choice reference test, and likely touch scripts/stingray_csv_shadow_overlay.py.

Important personal/project context: I’m Sean, Corvette specialist at Stingray Chevrolet in Plant City, FL. I’m building structured Corvette order/configuration systems and prefer careful, stepwise, evidence-backed migrations with tests and explicit success criteria.
