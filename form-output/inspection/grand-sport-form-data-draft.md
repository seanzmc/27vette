# Grand Sport Form Data Draft

Generated: `2026-04-30T15:36:29+00:00`
Status: `draft_not_runtime_active`
Source sheet: `grandSport`

## Contract Surface

- Variants: 6
- Context choices: 8
- Steps: 14
- Sections: 34
- Choices: 1614
- Standard equipment rows: 545
- Rule groups: 0 (deferred)
- Exclusive groups: 0 (deferred)
- Rules: 0 (deferred)
- Price rules: 0 (deferred)
- Interiors: 0 (deferred)
- Color overrides: 0 (deferred)

## Draft Notes

- Candidate available/standard choices from preview: 1418
- Full variant-matrix draft choices: 1614
- Rule/detail hot spot rows preserved: 123
- Unresolved normalization issues: 0

## Validation Warnings

- `grand_sport_draft_status`: Grand Sport form data is a draft inspection artifact and is not runtime active.
- `rules_deferred`: Final Grand Sport compatibility rules are deferred; rule/detail evidence is preserved in draftMetadata.ruleDetailHotSpots.
- `interiors_deferred`: Final Grand Sport interior hierarchy and component pricing are deferred to a later phase.
- `pricing_deferred`: Final Grand Sport price rules are deferred unless directly represented in normalized option prices.

## Live Output Safety

- This draft writes only inspection artifacts under `form-output/inspection/`.
- It does not write `form-app/data.js` or activate Grand Sport in the app.
