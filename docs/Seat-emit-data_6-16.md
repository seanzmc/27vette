# Why are seats defferred from the active-model-nonruntime-option-row-purge-spec?

Because I only deferred the seat rows that currently emit runtime behavior.

I should have worded that more narrowly: inactive duplicate seat rows are purge candidates; active emitted seat rows are deferred.

Evidence from the current generated data:

Stingray:

- Source has 11 seat rows for AQ9, AH2, AE4, AUP.
- All 11 are active=True.
- They emit 22 distinct choice/status keys into form-output/stingray-form-data.json.
- They also emit standard-equipment rows:
  - opt_aq9_003
  - opt_aq9_001
  - opt_ah2_001
- So deleting those rows as a simple purge would change the Seat step, standard equipment, and likely interior price math/seat replacement behavior.

Grand Sport:

- Some duplicate seat rows are inactive:
  - opt_aq9_004
  - opt_aq9_003
  - opt_ah2_003
  - opt_aq9_002
  - opt_ae4_001
  - opt_ae4_003
  - opt_ah2_002
- Those are in the safe-delete list because they do not emit choices.
- The active canonical seat rows are deferred:
  - opt_aq9_001
  - opt_ah2_001
  - opt_ae4_002
  - opt_aup_001
- Those do emit choices/standard equipment.

Z06:

- There are no inactive duplicate seat rows in the current source.
- The four seat rows are active and emitted:
  - opt_ae4_002
  - opt_ah2_001
  - opt_aq9_001
  - opt_aup_001
- Deleting them would directly change runtime choices and standard equipment.

Main distinction:

- interior_components owns component line items attached to selected interiors: stitching, suede, two-tone, R6X, etc.
- The option seat rows still own the customer seat-selection surface and generated standard-equipment/default behavior.
- So seat rows are not equivalent to N26/TU7/36S/37S/38S component-only rows unless we first migrate/canonicalize their active behavior elsewhere.

Recommended next adjustment:

- Keep the current purge pass limited to non-emitted rows and component-owned rows.
- Add a separate “seat canonicalization” pass if you want to remove active duplicate Stingray seat rows. That pass would need to preserve generated behavior via fewer canonical seat options plus OVS/variant overrides/price rules, then prove choices, standardEquipment, interior pricing, and dealer output are behavior-equivalent.
