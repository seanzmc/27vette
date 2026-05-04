# Agent Instructions for form-app

## Production app scope

`form-app/` is the production static app surface.

- The app runs without a build step.
- Preserve existing runtime behavior and export contracts unless explicitly approved.
- Treat `data.js` as generated and production-sensitive.
- Do not replace `form-app/data.js` with CSV-shadow or experimental output unless cutover is explicitly approved.

## Editing rules

- Keep UI changes narrow and behavior-preserving unless the task asks for behavior changes.
- Do not hand-edit generated data for migration work.
- If app behavior changes, verify selection behavior, open requirements, conflicts, pricing, and JSON/CSV export impact for the affected scenario.

## Local verification

Open `form-app/index.html` directly or serve the folder with a simple static server.

Use browser/manual verification for user-facing UI changes.
