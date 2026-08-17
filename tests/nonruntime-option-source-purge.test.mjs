// Source hygiene after the non-runtime option-row purge.
//
// Checkpoint 2 of the fast layered validation suite (spec §9) rewrote this
// file. It opened with `approvedDeletes`: three per-model inventories naming 57
// deleted option ids, 21 deferred ones, and the component RPOs they belonged
// to — a parallel copy of a completed workbook migration, kept in JavaScript,
// covering three of the six active models.
//
// The catalog's recorded disposition asked Checkpoint 2 to choose between an
// absence-parity check and a single named acceptance lock. Neither fits, and
// the reason is worth stating: absence is not recorded anywhere in the
// workbook, so a parity check has no expected side to read; and §4.4 reserves
// acceptance locks for customer or safety decisions, while a retained
// non-runtime source row is invisible to the customer by definition. What the
// inventory was really guarding is a set of source-hygiene RULES, and those can
// be stated without naming a single id:
//
//  - an RPO an interior component owns has no retained inactive option row;
//  - the purged non-runtime sections carry no option rows at all;
//  - the shared standard-equipment section retains no inactive duplicate;
//  - each seat RPO has exactly one row.
//
// Stated that way they sweep every active model instead of three, and they
// catch a reintroduction the id list could not: a row for an id that was never
// on it. The other half of the retired file — "deferred rows must remain" —
// moved to `source-to-contract-parity`, which proves every emitted choice and
// standard-equipment row traces to an active source row for all six models.
import assert from "node:assert/strict";
import test from "node:test";

import { activeModelKeys, modelSourceRows, workbookRows } from "./lib/workbook-truth.mjs";

const MODEL_KEYS = activeModelKeys();
assert.ok(MODEL_KEYS.length > 0, "the workbook declares no active model");

// The two sections the purge emptied. These are the one named product literal
// left in this file: they record which sections were retired, which is a
// decision, not something the current rows can be asked about — an empty
// section and a section that never existed look identical from the data.
const PURGED_SECTION_IDS = ["sec_cust_002", "sec_onst_001"];

// The shared section that once held duplicate inactive standard-equipment rows.
const SHARED_STANDARD_SECTION_ID = "sec_stan_002";
const SEAT_SECTION_ID = "sec_seat_002";

const optionRowsByModel = new Map(
  MODEL_KEYS.map((modelKey) => [modelKey, modelSourceRows(modelKey, "source_option_sheet")]),
);
const ovsRowsByModel = new Map(
  MODEL_KEYS.map((modelKey) => [modelKey, modelSourceRows(modelKey, "status_sheet")]),
);
const componentRows = workbookRows("interior_components");
const sectionPresentationRows = workbookRows("section_presentation");

const isActive = (row) => row.active === "True";

test("component-owned RPOs keep no retained inactive option row", () => {
  // An RPO owned by an active `interior_components` row is presented through
  // the interior, not as an option choice. An inactive option row for the same
  // RPO is a corpse of the pre-purge shape: invisible in the runtime, but live
  // enough to be reactivated by mistake and to make ownership ambiguous.
  let swept = 0;
  for (const modelKey of MODEL_KEYS) {
    const owned = new Set(
      componentRows.filter((row) => row.model_key === modelKey && isActive(row)).map((row) => row.rpo),
    );
    assert.ok(owned.size > 0, `${modelKey} declares no active interior component`);
    swept += owned.size;
    assert.deepEqual(
      optionRowsByModel
        .get(modelKey)
        .filter((row) => owned.has(row.rpo) && !isActive(row))
        .map((row) => `${row.option_id}:${row.rpo}:${row.section_id}`)
        .sort(),
      [],
      `${modelKey} retains inactive component-owned source options`,
    );
  }
  assert.ok(swept > 0, "the sweep examined no component-owned RPO");
});

test("purged non-runtime sections carry no option or status source rows", () => {
  for (const modelKey of MODEL_KEYS) {
    const purgedOptionIds = new Set(
      optionRowsByModel
        .get(modelKey)
        .filter((row) => PURGED_SECTION_IDS.includes(row.section_id))
        .map((row) => row.option_id),
    );
    assert.deepEqual([...purgedOptionIds].sort(), [], `${modelKey} retains purged-section option rows`);

    // The OVS half matters independently: a status row outliving its option
    // row is how a purge half-lands, and it is invisible to an option-sheet
    // check on its own.
    const optionIds = new Set(optionRowsByModel.get(modelKey).map((row) => row.option_id));
    assert.deepEqual(
      ovsRowsByModel
        .get(modelKey)
        .filter((row) => !optionIds.has(row.option_id))
        .map((row) => row.option_id)
        .sort(),
      [],
      `${modelKey} retains status rows for options its option sheet no longer has`,
    );
  }
});

test("no active presentation suppressor survives for a purged section", () => {
  assert.deepEqual(
    sectionPresentationRows
      .filter((row) => PURGED_SECTION_IDS.includes(row.section_id) && isActive(row))
      .map((row) => `${row.model_key}:${row.section_id}`)
      .sort(),
    [],
    "a purged section still has an active presentation suppressor behind it",
  );
});

test("the shared standard-equipment section retains no inactive duplicate", () => {
  for (const modelKey of MODEL_KEYS) {
    assert.deepEqual(
      optionRowsByModel
        .get(modelKey)
        .filter((row) => row.section_id === SHARED_STANDARD_SECTION_ID && !isActive(row))
        .map((row) => row.option_id)
        .sort(),
      [],
      `${modelKey} retains inactive duplicate standard-equipment rows`,
    );
  }
});

test("each seat RPO has exactly one source row per model", () => {
  // The retired form of this pinned Stingray's four seat ids, their selectable
  // and active flags, and a separate list of seven retired seat rows. The rule
  // underneath is single ownership: the pre-purge shape had several rows per
  // seat RPO, and that is what must not come back. Which seats are offered and
  // in what order is a separate decision, owned by
  // `workbook-visual-copy-standardization` R-6.
  for (const modelKey of MODEL_KEYS) {
    const seatRows = optionRowsByModel
      .get(modelKey)
      .filter((row) => row.section_id === SEAT_SECTION_ID);
    assert.ok(seatRows.length > 0, `${modelKey} has no seat section rows`);

    const byRpo = new Map();
    for (const row of seatRows) {
      byRpo.set(row.rpo, [...(byRpo.get(row.rpo) ?? []), row.option_id]);
    }
    assert.deepEqual(
      [...byRpo].filter(([, ids]) => ids.length > 1).map(([rpo, ids]) => `${rpo}: ${ids.join(", ")}`),
      [],
      `${modelKey} has more than one seat source row for a single RPO`,
    );
    assert.equal(
      seatRows.every(isActive),
      true,
      `${modelKey} retains an inactive seat source row`,
    );
  }
});
