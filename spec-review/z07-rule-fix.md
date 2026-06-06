    Confirmed. The current runtime is wrong in exactly the way you’re describing.

    I reproduced these current local states:

    After selecting Z07:
    - Z07 selected
    - auto-added: J57, T0F, CFZ, FE7, XFS
    - J56 disabled reason: blank
    - Clicking J56 removes/suppresses J57, leaving Z07 selected with J56 selected. Wrong.

    After selecting PDB:
    - PDB selected
    - auto-added: J57, J6D, ROY
    - J56 disabled reason: blank
    - Clicking J56 removes/suppresses J57 and ROY, leaving PDB selected with J56 selected and a missing carbon-wheel requirement. Wrong.

    After selecting PDD/PDF:
    - PDD/PDF selected
    - auto-added Z07 + J57 + package aero/wheel defaults
    - J56 disabled reason: blank
    - Clicking J56 suppresses J57, leaving the package selected but breaking the package brake requirement. Wrong.

    After selecting Z07 then switching aero to T0G:
    - Z07 + T0G selected
    - auto-added: J57, CFV, FE7, XFS
    - T0E disabled reason: blank
    - 5ZV disabled reason: blank
    - Clicking either bounces back to T0F. Visually wrong / misleading.

    Root cause

    The workbook already says:
    - Z07 includes J57.
    - PDB includes J57.
    - PDD/PDF include Z07, and Z07 includes J57.
    - Z07 requires one of T0F/T0G.
    - T0E/T0F/T0G/5ZV are aero exclusive peers.
    - J56/J57 are brake exclusive peers.

    But the runtime’s current included-peer suppression lets a user-selected exclusive peer suppress an auto-included target unless the include is considered “locked.” For this case:
    - J57 is not being treated as locked against J56.
    - T0E/5ZV are only visually locked when T0F is the current included/defaulted aero peer, not when T0G is the user-selected allowed alternate.

    Spec-first fix plan

    Decision:
    - Workbook-first fix using existing rule-group/excludes_any mechanics.
    - No RPO-specific JavaScript exceptions.
    - No generated sheet hand edits.
    - Add tests first, then apply targeted workbook source rows through safe-save.

    Why workbook-first is the right fit:
    - The existing runtime already supports excludes_any groups.
    - disableReasonForChoice() checks selected and auto-added source IDs through selectedContextIds().
    - selectedContextIds() includes computeAutoAdded() IDs, so a Z07 group should apply even when Z07 is auto-added by PDD/PDF.
    - This lets the workbook explicitly say: “while Z07/PDB is selected, these peer options are not valid,” instead of relying on fragile inferred include/exclusive behavior.

    Exact source workbook changes proposed

    1. Add a Z07 grouped exclusion for non-Z07 aero choices.

    Sheet: z06_rule_groups

    Add:

    - group_id: z06_group_z07_excludes_non_z07_aero
    - group_type: excludes_any
    - source_id: opt_z07_001
    - body_style_scope: *
    - trim_level_scope: *
    - variant_scope: *
    - disabled_reason: something like Not available while Z07 Performance Package is selected. Choose T0F or T0G.
    - active: True
    - notes: Z07 permits only T0F/T0G aero choices; T0E/5ZV should remain disabled even after switching from default T0F to T0G.

    Sheet: z06_rule_group_members

    Add:
    - z06_group_z07_excludes_non_z07_aero -> opt_t0e_001
    - z06_group_z07_excludes_non_z07_aero -> opt_5zv_001

    Effect:
    - Z07 selected directly: T0E/5ZV disabled.
    - Z07 + T0G: T0E/5ZV stay disabled.
    - PDD/PDF: since they include Z07, T0E/5ZV are also blocked by the auto-added Z07 path.
    - T0G remains allowed because it is not in the exclusion group and is still in Z07 requires_any {T0F,T0G}.

    2. Add a Z07 grouped exclusion for J56.

    Sheet: z06_rule_groups

    Add:

    - group_id: z06_group_z07_excludes_j56_brakes
    - group_type: excludes_any
    - source_id: opt_z07_001
    - body_style_scope: *
    - trim_level_scope: *
    - variant_scope: *
    - disabled_reason: J56 performance brakes are not available while Z07 is selected; Z07 includes J57 carbon ceramic brakes.
    - active: True
    - notes: Z07 always includes J57; J56 must not be selectable or restorable while Z07 remains selected.

    Sheet: z06_rule_group_members

    Add:
    - z06_group_z07_excludes_j56_brakes -> opt_j56_001

    Effect:
    - Direct Z07: J56 disabled and cannot suppress J57.
    - PDD/PDF: because they include Z07, J56 disabled through auto-added Z07.
    - If J56 was selected before Z07/PDD/PDF, reconcile should remove it because it now has an exclusion reason.

    3. Add a PDB grouped exclusion for J56.

    Sheet: z06_rule_groups

    Add:

    - group_id: z06_group_pdb_excludes_j56_brakes
    - group_type: excludes_any
    - source_id: opt_pdb_001
    - body_style_scope: *
    - trim_level_scope: *
    - variant_scope: *
    - disabled_reason: J56 performance brakes are not available while PDB is selected; PDB includes J57 carbon ceramic brakes.
    - active: True
    - notes: PDB includes J57 directly and must not allow switching back to J56 while selected.

    Sheet: z06_rule_group_members

    Add:
    - z06_group_pdb_excludes_j56_brakes -> opt_j56_001

    Effect:
    - PDB selected: J56 disabled and cannot suppress J57.
    - PDB does not need Z07, so it needs its own strict brake block.

    Why I would not add old-style direct peer excludes

    I would avoid adding direct z06_rule_mapping excludes like:
    - Z07 excludes T0E
    - Z07 excludes 5ZV
    - Z07 excludes J56
    - PDB excludes J56

    Those would probably work, but after the normalization work, grouped blockers are the cleaner shape for “one source blocks a small set of targets.” The workbook already has excludes_any group support, and there are existing tests encouraging approved one-source blocker clusters to use excludes_any instead of direct-exclude sprawl.

    Tests to add/update first

    File: tests/z06-runtime-rule-corrections.test.mjs

    Add/assert:

    1. Z07 brake lock:
    - Select Z07.
    - Assert J57 is auto-added.
    - Assert J56 has non-empty disabled reason mentioning Z07/J57.
    - Click J56.
    - Reconcile.
    - Assert J56 is not selected.
    - Assert J57 is still auto-added.
    - Assert no J57/carbon-wheel regression.

    2. PDB brake lock:
    - Select PDB.
    - Assert J57 auto-added.
    - Assert J56 disabled.
    - Click J56.
    - Reconcile.
    - Assert PDB remains selected.
    - Assert J56 not selected.
    - Assert J57 remains auto-added.
    - Assert ROY remains auto-added unless switched to ROZ/STZ.

    3. PDD/PDF inherited Z07 brake lock:
    - Select PDD and PDF in separate subcases.
    - Assert Z07 auto-added.
    - Assert J57 auto-added.
    - Assert J56 disabled.
    - Click J56.
    - Reconcile.
    - Assert package remains selected.
    - Assert J56 not selected.
    - Assert J57 remains auto-added.

    4. Aero visual congruency:
    - Select Z07.
    - Select T0G.
    - Assert T0G selected.
    - Assert T0F not auto-added.
    - Assert T0E disabled.
    - Assert 5ZV disabled.
    - Click T0E and 5ZV in separate subcases.
    - Assert neither can stick.
    - Assert Z07 remains selected.
    - Assert T0G ideally remains selected, or if product direction prefers falling back to T0F then assert that explicitly. My recommendation: since they are disabled, click should be ignored and T0G should remain selected.

    Generated-data tests:
    - In tests/z06-form-data-draft.test.mjs, assert the three new excludes_any groups emit with the expected target IDs.
    - Possibly mirror in tests/z06-contract-preview.test.mjs if that contract currently checks grouped rule shape.

    Implementation path after approval

    1. Add RED tests.
    2. Add a targeted safe-save workbook script, or use an existing targeted migration style if one already owns nearby Z06 rule corrections.
       - It should only upsert these z06_rule_groups and z06_rule_group_members rows.
       - It should not call the future-model whole-sheet option review writer.
       - It should verify exact rows after reopening workbook.
    3. Run script with --write only after checking no Excel lock.
    4. Regenerate:
       - .venv/bin/python scripts/generate_z06_form.py if present/current for Z06 artifacts.
       - .venv/bin/python scripts/generate_stingray_form.py for live form-app/data.js.
    5. Run focused gates:
       - node --test tests/z06-runtime-rule-corrections.test.mjs
       - node --test tests/z06-form-data-draft.test.mjs tests/z06-contract-preview.test.mjs
       - node --test tests/multi-model-runtime-switching.test.mjs
    6. Browser smoke:
       - Z07 -> J56 disabled/non-clickable
       - Z07 -> T0G -> T0E/5ZV remain disabled
       - PDB -> J56 disabled/non-clickable
       - PDD/PDF -> J56 disabled/non-clickable through Z07

    Boundaries:
    - No runtime hardcoded RPO exception unless tests prove the existing excludes_any path cannot express this.
    - No direct generated sheet edits.
    - No cleanup of unrelated Z06 package pricing/interior/accessory issues in this pass.
    - No change to dealer submission shape.

    Approval needed:
    Approve this as a focused workbook-first pass:
    - Add Z07 excludes_any group for T0E/5ZV.
    - Add Z07 excludes_any group for J56.
    - Add PDB excludes_any group for J56.
    - Add targeted runtime/generated-data tests and regenerate.
