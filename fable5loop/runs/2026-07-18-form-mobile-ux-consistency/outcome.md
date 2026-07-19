# Outcome Rubric · Form Mobile UX Consistency

Spec: `.hermes/plans/form-mobile-ux-consistency-spec.md` (approved 2026-07-18 by Sean; resolved decisions: desktop header unchanged / mobile-only action relocation; bottom-only mobile Next).

Task: fix five reported mobile UI issues in the customer order form (`form-app/`): tooltip detaching on scroll, absolutely-positioned hamburger with dead space, oversized inconsistent build-summary tile, header-crowding Reset/Download/Submit, and inconsistent sticky Next between Vehicle Setup and other steps.

## Gradable criteria

1. **Tooltip scroll fix**: with a floating tooltip open at ≤760px, any page scroll closes it (`is-open` removed, `data-open` cleared); no fixed-position panel remains detached over unrelated content. Evidence: JS state assertion + real-input scroll in browser.
2. **In-flow header**: at 375×812, `#openStepDrawerButton` computed `position` is `static`; no 52px topbar padding band; hamburger, build-summary pill, and brand block occupy an in-flow topbar grid (row 1 controls, row 2 brand).
3. **Always-visible total**: `#mobileSummaryButton` renders in the header at ≤760px showing the live build total; it opens `#summaryDrawer`; symmetric affordance to the hamburger (left steps / right summary).
4. **Action relocation (mobile only)**: at ≤760px the topbar toolbar is hidden and `#summaryActionsCard` (Reset / Download Build / Submit to Dealer) is visible in the summary drawer with disabled-state parity to the old header buttons; final step renders sticky Reset + Download + Submit; at 768px and 1280px the original header toolbar renders and `#summaryActionsCard` is hidden.
5. **Single sticky Next**: at ≤760px every step, including all three Vehicle Setup stages, shows exactly one primary forward control — the sticky bottom `step-footer` button; `#mobileNextStep` is hidden; the in-panel "Continue to …" action is hidden at ≤760px but still present ≥761px; full 12-step walk reaches the final step via footer clicks only.
6. **Gates green, no generated churn**: `tests/stingray-form-regression.test.mjs` and `tests/multi-model-runtime-switching.test.mjs` pass; `git status -- form-output form-app` shows only the three intended `form-app` runtime files modified (`app.js`, `index.html`, `styles.css`); `form-app/data.js` untouched.
7. **Dealer boundary preserved**: submit entry points open the unchanged `#dealerSubmitModal` (name/email/phone/comments fields + `#dealerTurnstile` mount); drawer submit closes the drawer before opening the modal; no payload/endpoint/Turnstile code changed.

## Maker result

All seven criteria met per maker verification (see `validation-output.txt` and verifier report). Changed files: `form-app/app.js`, `form-app/index.html`, `form-app/styles.css`, `tests/stingray-form-regression.test.mjs`.
