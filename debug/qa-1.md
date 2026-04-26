# QA-1 Stingray Form

Issue: Standard Equipment too out of the way
Step/body/trim:
Selected options:
Expected: Standard Equipment should be prominently displayed on trim level step then collapsiblwe in the selected options list. Retain the breakdown as it is now, but add the trim level equipment dropdown. Moving the customer info (different issue) will bring it up into view.
Actual:
Screenshot:
Data issue or visual issue: visual issue

Issue: RPOs not necessary for standard equipment list.
Expected: Standard equipment should be listed without RPOs or ids and just be a list of features, with descriptons if applicable.
Data issue or visual issue: data issue

Issue: Section selection mode type needs a display text.
Expected: The section selection mode type should have a display text that is more user friendly than "single_select_req" and should be displayed in the UI.
Data issue or visual issue: data issue

Issue: Selection flow is not intuitive for users.
Expected: Body style and trim level advance immediately to the next step but the next option for the exterior color does not advance and the only way to advance is to click the next section in the sidebar, which is not intuitive. The next button should be added to the bottom of the options list and should advance to the next step.
Visual issue: visual issue

Issue: Customer Info fields should be their own step at the end of the form, not in the sidebar.
Expected: The customer info fields should be moved to their own step at the end of the form.

Issue: Options with label "Not available for selected body/trim" should be hidden, not just disabled.
Expected: Options that are not available for the selected body/trim should be hidden from the options.
Actual: Options that are not available for the selected body/trim are still visible but disabled, which crowds the UI and can be confusing for users.
Visual issue: visual issue

Issue: Inactive options with label "Display only source row" need the label to say what they are inactive and what option they require.
Step/body/trim: Exterior appearance / Convertible / 2LT
Selected options: BC7 is inactive with label "Display only source row" and becomes active automatically when ZZ3 is selected, the same label that shows when it is active should be in disabled mode when it is inactive.
Actual: Included with ZZ3 Convertible Engine Appearance Package.

Issue: Suspension needs to be a replaceable default
Expected: FE1 should be selected by default. When Z51 is selected, FE3 should be selected by default, FE4 becoems available and FE1 and FE2 should become unavailable.

Issue: Exhaust needs to be a replaceable default
Expected: NGA should be selected by default.

Issue: Options labeled "Inactive in the source workbook" should be hidden, not just disabled.

Issue: Need to fix duplicate text in names and descriptions for all options and make a decision on what fields to display and when.

**Issue**: Need to simplify the interior option display. Too many options with similar names and descriptions. Interiors should be tiered in selection to break it up by color, then material, then other options like two tone. This should make interior selection more interactive.

Issue: Interior Styling section does not need to exist because the color overrides will be applied automatically. Stitching is selected in the previous section.

Issue: N26 and TU7 need to be removed from Interior Trim section becasue they will be applied automatically when the corresponding interior color is selected.

Issue: BC7 should be selected by default when coupe is selected. It's duplicate BC7 option that is only available for convertibles should be removed and the main BC7 option should be available for both body styles with the appropriate rules to make it available when the corresponding packages are selected.

Issue: BCP BCS and BC4 need to have rules set up instead of having multiple versions of each with different prices.
Expected: BCP, BCS and BC4 should be priced as 695 standard, available on coupe. When B6P is selected, the price of all three should change to 595. The other rules for B6P should still apply.

Issue: Rules should only apply to the current selections. BCP showed "Requires B6P" then when B6P was selected, the label changed to Requires ZZ3 and remained unavailable. This is cross variant rule priority issue that needs to be fixed when the BCP, BCS and BC4 rules are fixed.

Issue: Don't show ZF1 as an option, instead show T0A as an option but it is unavailable unless Z51 is selected, then it is selected by default. TVS, and other spoiler options that say "T0A is removed when Z51 is selected" should still be selecatble but they should just override T0A when selected. This is a case where the same option needs to be available in multiple states and the rules should just override the default selection and availability when the corresponding options are selected.

# QA-1 Output

Implemented the approved QA-1 pass.

**What changed**
- Updated generated contract and workbook outputs in [generate_stingray_form.py](/Users/seandm/Projects/27vette/archived/scripts/generate_stingray_form.py), [stingray_master.xlsx](/Users/seandm/Projects/27vette/archived/stingray_master.xlsx), [data.js](/Users/seandm/Projects/27vette/form-app/data.js).
- Moved Customer Information into its own final form step.
- Added bottom `Next` navigation through the option flow.
- Added friendly selection-mode labels.
- Put Standard & Included prominently on Trim Level and collapsed under Selected RPOs, without RPO/id prefixes in the displayed equipment list.
- Hidden unavailable/inactive rows from option cards.
- Consolidated BC7 and BC4/BCP/BCS duplicate runtime options, added B6P price overrides, hid ZF1, made T0A visible/auto-added under Z51, and removed N26/TU7 from Interior Trim display.
- Added focused regression coverage in [stingray-form-regression.test.mjs](/Users/seandm/Projects/27vette/tests/stingray-form-regression.test.mjs).

**What did not change**
- No new app dependencies or package setup.
- No broad interior tiered-selection redesign yet; Interior Styling was removed and N26/TU7 are hidden, but the full color/material/two-tone tiering remains follow-up work.
- No mass copy rewrite for all option names/descriptions beyond the display-rule changes needed for this pass.

**Gate results**
- Generator: `validation_errors: 0`
- Workbook reopen check: generated sheets present, `form_validation` has `0` errors, `customer_info` present, `interior_style` absent.
- Regression tests: `node --test tests/stingray-form-regression.test.mjs` passed `5/5`.
- Browser smoke via Chromium passed: trim equipment shown, raw mode labels gone, unavailable/inactive rows hidden, ZF1 hidden, Z51 removes FE1 and auto-adds T0A, Customer Information reachable and editable.

Manual verification still pending: a human visual pass on the full interior-selection experience and final copy decisions for duplicate option labels/descriptions.
