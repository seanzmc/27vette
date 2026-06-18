# Cleanup risk ranking and recommendations

Ranked by risk to the core direction: workbook-owned data, one consistent workbook → generator → registry → runtime path, no stale/single-pass edge routes, and scalable/portable code.

Evidence inspected: docs/actual-tasks-remaining-6-17.md:43-77.

Risk ranking

1. Later rule-mapping cleanup: runtime_action / body_style_scope
   - Risk: Critical
   - Current live risk: Medium
   - Pass risk: Very high
   - Why it ranks highest:
     - runtime_action is explicitly still behavior-carrying.
     - body_style_scope may still affect scoped rule behavior.
     - Removing either too early could silently change generated rules or runtime behavior.
   - Core-philosophy concern:
     - This is exactly where hidden behavior can remain in transitional columns instead of being modeled as workbook-owned canonical rule/group/default metadata.
   - Safe next shape:
     - Report-only rule-shape audit first.
     - Classify each use as one of: exclusive group, requires_any, excludes_any, direct include, true direct exclude, default replacement, or still-needed scope.
     - Remodel one behavior class at a time.
   - Do not:
     - Delete columns broadly.
     - Suppress in generator/runtime.
     - Treat validator/test simplification as proof behavior moved.

2. Active standard-tech / connected-service ownership: sec_tech_001
   - Risk: High
   - Current live risk: High if touched; medium while left alone
   - Pass risk: High
   - Why:
     - Rows are still active emitted standard equipment.
     - The doc explicitly says not to delete until a workbook-owned replacement source model exists.
   - Core-philosophy concern:
     - Current shape is a known ownership gap: active runtime-facing standard/connected-service data is still represented as option rows.
   - Safe next shape:
     - Design the replacement workbook-owned standard-equipment/connected-service source first.
     - Prove generated-contract parity.
     - Then migrate.
   - Do not:
     - Treat these as nonruntime clutter.
     - Delete active sec_tech_001 rows without replacement ownership.

3. Interior stale-surface cleanup: interior_reference_path + architectureAudit/\*\_interiors_refactor.csv
   - Status: Completed 2026-06-18.
   - Result:
     - `ModelConfig.interior_reference_path` and the `base_model_config()` CSV-path assignment are retired.
     - `architectureAudit/stingray_interiors_refactor.csv` and `architectureAudit/grand_sport_interiors_refactor.csv` are deleted.
     - `tests/grand-sport-draft-data.test.mjs` guards active interior pipeline sources against reintroducing those stale config/file surfaces.
   - Residual guidance:
     - Do not add a replacement CSV/reference path; workbook-owned interior grouping stays in `model_interior_scope`, and component membership stays in `interior_components`.

4. Future-model scaffold display-order decision: ZR1/ZR1X duplicate sec_stan_001 orders
   - Risk: Medium-high
   - Current live risk: Low
   - Future promotion risk: High
   - Why:
     - Active promoted sheets are guarded, but future scaffold rows still have duplicate active (section_id, display_order) buckets.
     - This is safe only while ZR1/ZR1X remain unpromoted/scaffold.
   - Core-philosophy concern:
     - Future models should enter the same validation/generation path, not require special exceptions when promoted.
   - Safe next shape:
     - Either clean scaffold display orders deterministically now, or add a clearly scoped future-model validation/report gate.
   - Do not:
     - Let “future scaffold” become an unguarded alternate path.
     - Promote future models before deciding how their scaffold rows are validated.

5. Optional audit/report tooling: build_rule_sources.py, Grand Sport audit tests
   - Risk: Medium
   - Current live risk: Low
   - Codebase relevance risk: Medium-high
   - Why:
     - It is intentionally opt-in and not default readiness.
     - But optional tooling can become stale, misleading, or a shadow authority if it preserves old parser/report assumptions.
   - Core-philosophy concern:
     - Audit/report tools are acceptable only if they inspect workbook-owned behavior; they should not define or preserve an alternate rule taxonomy.
   - Safe next shape:
     - Classify each tool/test as:
       - retained opt-in provenance tool,
       - reusable validator/report,
       - stale one-pass artifact,
       - or obsolete test coupling.
   - Do not:
     - Delete just because not default readiness.
     - Let report-only expectations block workbook-owned cleanup.

6. Residual copy/product follow-up allowlist
   - Risk: Medium
   - Current live risk: Medium product/copy risk
   - Architecture risk: Low-medium
   - Rows called out:
     - AP9 description
     - D3V description
     - EYK/EYT badge copy
     - SFZ applicability
     - VYW logo applicability
     - ZZ3 Z06 includes-list difference
     - NWI description
     - PIN restrictions
   - Why:
     - Automatic convergence could remove product-specific detail or meaning.
   - Core-philosophy concern:
     - Workbook source rows own customer-facing copy and applicability. The danger is over-normalizing product differences into false parity.
   - Safe next shape:
     - Product-decision review table.
     - Classify each field as mechanical drift, intentional model difference, or needs human decision.
     - Keep allowlist until decided.
   - Do not:
     - Run broad auto-copy convergence over these rows.

7. Z06 option-id suffix / no-RPO ID drift
   - Risk: Low-medium
   - Current live risk: Low
   - Tooling scalability risk: Medium
   - Why:
     - Listed as mostly tooling/cosmetic unless strict cross-model option_id joins are desired.
     - Could matter later for editor tooling, asset mapping, cross-model comparison, or generated contract diff tooling.
   - Core-philosophy concern:
     - Stable IDs support portability and repeatable joins, but renaming IDs can create avoidable churn if no current consumer needs it.
   - Safe next shape:
     - First identify an actual consumer that benefits from normalization.
     - If none, document tolerated drift.
   - Do not:
     - Rename IDs casually in active generated contracts.

8. Stingray exclusive-group ID prefix/style drift
   - Risk: Low
   - Current live risk: Very low
   - Tooling risk: Low-medium only if editor/tooling depends on naming conventions
   - Why:
     - Called out as cosmetic unless editor/tooling needs normalization.
   - Core-philosophy concern:
     - Naming consistency helps maintainability, but this is not a source-of-truth or runtime-path blocker by itself.
   - Safe next shape:
     - Defer unless paired with a broader editor/tooling naming-normalization pass.
   - Do not:
     - Touch generated behavior or group semantics for style-only cleanup.

Priority order if optimizing architecture and portability

1. Rule-mapping behavior audit/remodel plan.
2. Interior stale-surface consumer audit and parity proof.
3. sec_tech_001 ownership model design.
4. Future-model scaffold display-order decision.
5. Optional audit/report tooling classification.
6. Residual copy/product decisions.
7. Z06 option-id/no-RPO ID normalization only if tooling needs it.
8. Stingray exclusive-group ID style cleanup only if tooling needs it.

Different priority if optimizing customer-facing product correctness first

1. Residual copy/product allowlist.
2. sec_tech_001 ownership, if standard-equipment display is suspected wrong.
3. Rule-mapping audit.
4. Interior stale-surface cleanup.
5. Future scaffold.
6. Optional audit tools.
7. Z06 ID drift.
8. Stingray ID style drift.

My recommendation

For the codebase philosophy you stated, do not start with copy. Start with a report-only architecture cleanup pass around rule behavior and stale edge routes:

A. Rule-shape audit for runtime_action / body_style_scope.
B. Interior stale-surface consumer audit.
C. Optional audit-tool classification.

Those three directly answer: workbook-owned data, one runtime path, and only relevant code.

What changed: nothing.
What did not change: workbook, generated artifacts, runtime, tests, docs.
Gates: not run; this was report-only ranking.
Manual verification pending: audit tooling classification remains; the interior stale-surface consumer audit/cleanup completed on 2026-06-18.
