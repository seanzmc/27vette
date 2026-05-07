# Stingray Experimental App Smoke Test

This experimental app shell uses CSV-shadow first-slice data for browser smoke testing only. It does not change production `form-app/data.js` and is not a CSV cutover.

The workflow builds an ignored app shell under `build/experimental/form-app/`. Production Excel/Python generation remains the source of truth. The experimental `data.js` is generated from the CSV-shadow first-slice overlay, while the static shell files are copied from `form-app/`.

## Build

```sh
.venv/bin/python scripts/build_stingray_experimental_app.py
```

Expected output:

```text
build/experimental/form-app/
  index.html
  app.js
  styles.css
  data.js
```

`index.html`, `app.js`, and `styles.css` are copied from `form-app/`. `data.js` is generated from the CSV-shadow overlay. `build/experimental/` is ignored by git.

## Serve

```sh
cd build/experimental/form-app
python3 -m http.server 8000
```

Open the local server in a browser, usually:

```text
http://localhost:8000/
```

Do not use this workflow for external deployment.

## Cleanup

```sh
rm -rf build/experimental/form-app
```

Or remove all ignored experimental output:

```sh
rm -rf build/experimental
```

## Test Commands

Run the shadow and experimental test bundle:

```sh
node --test tests/stingray/first-slice-csv.test.mjs
node --test tests/stingray/first-slice-parity.test.mjs
node --test tests/stingray/first-slice-legacy-fragment.test.mjs
node --test tests/stingray/first-slice-shadow-data.test.mjs
node --test tests/stingray/shadow-regression.test.mjs
node --test tests/stingray/shadow-data-js-artifact.test.mjs
node --test tests/stingray/experimental-app-shell.test.mjs
```

Optional production safety checks:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

These tests do not cut over production.

## Manual Smoke Checklist

- App loads with no console errors.
- The Stingray form renders normally.
- Body style and trim controls work.
- Coupe + B6P auto-adds D3V and SL9.
- Coupe + BCP auto-adds D3V where production behavior expects it.
- Coupe + BCP prices BCP at $695 where production behavior expects it.
- Coupe + BCP + B6P prices BCP at $595 where production behavior expects it.
- Convertible + BCP without ZZ3 shows the ZZ3 requirement.
- Convertible + BCP + ZZ3 clears the ZZ3 requirement.
- Coupe + BCP + BC4 triggers LS6 engine-cover exclusivity.
- One unrelated scenario still behaves normally, such as Z51 / FE3 behavior.
- Export JSON still works.
- Export CSV still works.
- No unexpected console errors appear after selections and exports.

## What Not To Do

- Do not copy `build/experimental/form-app/data.js` into production `form-app/data.js`.
- Do not deploy `build/experimental/` as production.
- Do not treat this workflow as CSV cutover.
- Do not edit production `data.js` by hand.
- Do not use this workflow to migrate new option families.

## Troubleshooting

If the build command fails, run the overlay script directly:

```sh
.venv/bin/python scripts/stingray_csv_shadow_overlay.py --as-data-js --out /tmp/stingray-data.js
```

If the browser shows stale behavior, hard refresh or restart the local server.

If the app fails to load, confirm `build/experimental/form-app/data.js` exists.

If tests fail, do not proceed to manual smoke until the test failure is understood.
