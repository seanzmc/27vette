# Interior UI Job Task Log

Scope convention from user: write specs and future task documents for this interior UI job under `docs/interior/`.

## Completed / Implemented

### Priority A+B — Interior Color media, selected badge, compatibility copy

Spec: `docs/interior/firstSpec_PriorityPass.md`

Implementation status: implemented on branch `interior-media-pass1`.

Covered outcomes:

- Interior Color swatches render from workbook-owned WordPress URL metadata.
- Interior rows are emitted with `image_url`, `image_alt`, `image_fit`, and `image_position`.
- Runtime remains generic; no local `src-img/` runtime paths and no hardcoded RPO/image maps.
- Interior Color selected card shows visible `✓ Selected` badge.
- Single-choice groups no longer show `1 choice` copy.
- Compatibility copy includes `Change seats` action.

## Current Proposed Next Pass

### Priority C — Interior Composition Summary

Spec: `docs/interior/secondSpec_InteriorCompositionSummary.md`

Implementation status: spec only; pending approval.

Goal:

- Add a compact, inline summary across Seats, Interior Color, Seat Belt, and Interior Trim.
- Reuse current generated/runtime state and `currentOrder()` data.
- Avoid workbook/generator changes unless implementation proves a missing generated-data field.

## Deferred Future Tasks

### Priority D — Interior Trim / D30 / UQT Reframing

Status: deferred; no spec written yet.

Initial problem statement from critique:

- `UQT Performance Data and Video Recorder` feels more like performance/technology than interior trim.
- `D30 Color Combination Override` reads like a configurator/rule artifact and is confusing when shown as unavailable with a price.

Likely source-of-truth boundary:

- Must inspect workbook section ownership, generated choices, color override behavior, D30 display-only contract, and order-summary impact before proposing edits.
- Do not hide D30/UQT in runtime JavaScript without workbook/source evidence.

### Priority E — Step Rail Completion / Selected Indicators

Status: deferred; no spec written yet.

Initial problem statement from critique:

- Left rail identifies current step, but it does not communicate which interior choices are completed.

Likely implementation boundary:

- Runtime UI + tests only if completion can be derived from existing required/missing state.
- No workbook edits expected unless generated step metadata lacks required/optional semantics for completion.

## Standing Constraints For This Job

- Keep local `src-img/` as source/reference only.
- Runtime images should stay hosted on the WordPress site and linked through workbook-owned metadata.
- Prefer workbook-authored source rows for product/data/business behavior.
- Generated `form_*` sheets, `form-output/*`, and `form-app/data.js` are outputs.
- Runtime JavaScript should render/evaluate generated data generically.
- No dealer submission endpoint/payload/Turnstile changes without explicit approval.
- Keep passes small and labeled.
