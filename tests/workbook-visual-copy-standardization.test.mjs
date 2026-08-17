// Cross-model copy standardization over the workbook's option sheets.
//
// Checkpoint 2 of the fast layered validation suite (spec §9) removed the
// hardcoded three-sheet list this file used to open with. Six models are
// workbook-active; the copy rules below are model-neutral; so the sweep was
// asserting over half the inventory while reporting green, and registering a
// seventh model would have widened nothing. The sheet list now comes from each
// model's own `model_workbook_sources` registration through the §6.2
// workbook-truth snapshot.
//
// Two kinds of assertion live here and they are kept visibly apart:
//
//  - GENERIC SWEEPS, which state a rule ("shared copy matches") and discover
//    their cases from the workbook. They now cover every active model.
//  - NAMED APPROVED-COPY DECISIONS (R-1 through R-6 and the label sets below),
//    which are product literals. §4.4 says that is where product-specific
//    literals belong, and each names the models it applies to by model_key
//    rather than by sheet name, so it neither widens by accident nor pins a
//    sheet the workbook may rename.
import assert from "node:assert/strict";
import test from "node:test";

import { activeModelKeys, modelSourceSheet, workbookRows } from "./lib/workbook-truth.mjs";

const MODEL_KEYS = activeModelKeys();
assert.ok(MODEL_KEYS.length > 0, "the workbook declares no active model");

const optionSheet = (modelKey) => modelSourceSheet(modelKey, "source_option_sheet");
const OPTION_SHEETS = MODEL_KEYS.map(optionSheet);

const rowsBySheet = new Map(OPTION_SHEETS.map((sheetName) => [sheetName, workbookRows(sheetName)]));

function isActive(row) {
  return row.active === true || String(row.active).toLowerCase() === "true";
}

function rowFor(sheetName, optionId) {
  const row = rowsBySheet.get(sheetName).find((candidate) => candidate.option_id === optionId && isActive(candidate));
  assert.ok(row, `${sheetName} is missing active ${optionId}`);
  return row;
}

/**
 * Sheets that carry an option as an active row.
 *
 * The named decisions below apply to the models that sell the option, which is
 * a workbook fact rather than a list to maintain. Before Checkpoint 2 the same
 * decisions were expressed as loops over three hardcoded sheets, which both
 * under-covered the three models added since and would have failed outright on
 * a model that does not carry the row.
 */
function sheetsCarrying(optionId) {
  const sheets = OPTION_SHEETS.filter((sheetName) =>
    rowsBySheet.get(sheetName).some((row) => row.option_id === optionId && isActive(row)),
  );
  assert.ok(sheets.length > 0, `no active model carries ${optionId}`);
  return sheets;
}

function activeRowsByOptionId(sheetName) {
  const byOptionId = new Map();
  for (const row of rowsBySheet.get(sheetName).filter(isActive)) {
    const rows = byOptionId.get(row.option_id) ?? [];
    rows.push(row);
    byOptionId.set(row.option_id, rows);
  }
  return byOptionId;
}

/**
 * Options every active model carries as exactly one active row.
 *
 * A pairwise definition ("shared by two or more models") was measured and
 * rejected: it pulls in the numbered standard-equipment rows, whose copy is
 * legitimately per-model, and would need an allowlist five times this one. The
 * strict definition keeps the rule meaningful — an option every model sells
 * should read the same everywhere unless a reviewed decision says otherwise.
 */
function strictSharedOptionIds() {
  const maps = OPTION_SHEETS.map((sheetName) => activeRowsByOptionId(sheetName));
  const [first, ...rest] = maps;
  return [...first.keys()]
    .filter((optionId) => first.get(optionId).length === 1)
    .filter((optionId) => rest.every((map) => map.get(optionId)?.length === 1))
    .sort();
}

// Reviewed copy differences: the option is shared but the wording is not, and
// that is a product decision rather than drift. `no dead allowlist entries`
// below keeps this list honest in the other direction — an entry that stops
// describing a real difference has to be removed rather than left to rot.
const COPY_FIELD_ALLOWLIST = new Map([
  ["opt_ap9_001:description", "Other models leave the target blank; keep Stingray detail for later product review."],
  ["opt_d3v_001:description", "Other models leave the target blank; keep Stingray engine-lighting copy for later review."],
  ["opt_efr_001:description", "R-4 keeps model-specific Stingray EFR description."],
  ["opt_eyk_001:description", "Model-specific emblem/badging copy."],
  ["opt_eyt_001:description", "Model-specific emblem/badging copy."],
  ["opt_nga_001:description", "R-5 uses per-model exhaust-exit wording."],
  ["opt_nwi_001:description", "NWI exhaust-tip wording remains a separate copy decision."],
  ["opt_pin_001:description", "Other models leave the target blank; keep Stingray restriction copy for later review."],
  ["opt_sfz_001:option_name", "Model applicability differs: Stingray front-only vs the wide-body models front+rear."],
  ["opt_sfz_001:description", "Model applicability differs: Stingray front-only vs the wide-body models front+rear."],
  ["opt_vyw_001:description", "Model-specific floor-mat logo applicability."],
  ["opt_zz3_001:description", "Z06 lacks the LS6 engine cover referenced by Stingray/Grand Sport copy."],
]);

test("shared active option names and descriptions match across promoted models except reviewed allowlist", () => {
  for (const optionId of strictSharedOptionIds()) {
    for (const field of ["option_name", "description"]) {
      const allowlistKey = `${optionId}:${field}`;
      if (COPY_FIELD_ALLOWLIST.has(allowlistKey)) continue;

      const values = Object.fromEntries(OPTION_SHEETS.map((sheetName) => [sheetName, rowFor(sheetName, optionId)[field] ?? ""]));
      assert.equal(
        new Set(Object.values(values)).size,
        1,
        `${optionId} ${field} should match across promoted models: ${JSON.stringify(values)}`
      );
    }
  }
});

test("no dead allowlist entries", () => {
  // An allowlist is a set of reviewed exceptions, and an exception that no
  // longer describes anything is a decision nobody is making any more. Without
  // this, resolving a copy difference in the workbook leaves a permanent hole
  // in the sweep — the exact way the retired three-sheet list went stale
  // without anyone noticing.
  const live = new Set();
  for (const optionId of strictSharedOptionIds()) {
    for (const field of ["option_name", "description"]) {
      const values = OPTION_SHEETS.map((sheetName) => rowFor(sheetName, optionId)[field] ?? "");
      if (new Set(values).size > 1) live.add(`${optionId}:${field}`);
    }
  }
  assert.deepEqual(
    [...COPY_FIELD_ALLOWLIST.keys()].filter((key) => !live.has(key)).sort(),
    [],
    "allowlisted copy differences that no longer exist should be removed",
  );
});

test("shared active descriptions do not differ only by trailing period", () => {
  for (const optionId of strictSharedOptionIds()) {
    const values = OPTION_SHEETS.map((sheetName) => String(rowFor(sheetName, optionId).description ?? ""));
    const normalized = values.map((value) => value.replace(/\.$/, ""));
    assert.notEqual(
      new Set(normalized).size === 1 && new Set(values).size > 1,
      true,
      `${optionId} description differs only by trailing period: ${JSON.stringify(values)}`
    );
  }
});

test("approved product decisions R-1 through R-5 are workbook-owned", () => {
  assert.equal(rowFor(optionSheet("z06"), "opt_uv6_001").section_id, "sec_1lte_001", "R-1 Z06 UV6 drift is intentional");
  assert.equal(rowFor(optionSheet("stingray"), "opt_uv6_001").section_id, "sec_2lte_001", "R-1 Stingray UV6 remains 2LT");
  assert.equal(rowFor(optionSheet("grand_sport"), "opt_uv6_001").section_id, "sec_2lte_001", "R-1 Grand Sport UV6 remains 2LT");

  // These two hold on every active model, so the loop widens from three sheets
  // to six rather than being scoped down.
  for (const sheetName of sheetsCarrying("opt_sc7_001")) {
    const sc7 = rowFor(sheetName, "opt_sc7_001");
    assert.equal(sc7.section_id, "sec_lpoe_001", `${sheetName} SC7 section`);
    assert.equal(sc7.description, "LPO. Genuine Corvette Accessory", `${sheetName} SC7 punctuation`);
  }
  for (const sheetName of sheetsCarrying("opt_drz_001")) {
    const drz = rowFor(sheetName, "opt_drz_001");
    assert.equal(drz.option_name, "Auto-Dimming Rear Camera Mirror", `${sheetName} DRZ name`);
    assert.equal(drz.description, "Inside rearview with full camera display", `${sheetName} DRZ description`);
  }

  const stingrayEfr = rowFor(optionSheet("stingray"), "opt_efr_001");
  assert.equal(stingrayEfr.option_name, "Carbon Flash Painted Accents", "Stingray EFR name");
  assert.equal(
    stingrayEfr.description,
    "Includes side vents and front/rear grille accents. Includes tonneau grille with convertible.",
    "Stingray EFR description"
  );

  // EDU is not sold on every model. "Where the model carries the row" is the
  // scope, discovered from the sheets rather than pinned to a model list, so
  // the rule widens by itself when a model gains the option.
  for (const sheetName of sheetsCarrying("opt_edu_001")) {
    assert.equal(rowFor(sheetName, "opt_edu_001").option_name, "Body-Color and Carbon Flash Accents", `${sheetName} EDU name`);
  }
  assert.equal(
    rowFor(optionSheet("stingray"), "opt_edu_001").description,
    "Body-color side vents and front splitter; Carbon Flash-painted rockers and front/rear grille accents.",
    "Stingray EDU keeps approved model copy"
  );
  for (const sheetName of [optionSheet("grand_sport"), optionSheet("z06")]) {
    assert.equal(
      rowFor(sheetName, "opt_edu_001").description,
      "Body-color side vents and front splitter, Carbon Flash-painted rockers and front/rear grille accents",
      `${sheetName} EDU description`
    );
  }

  assert.equal(
    rowFor(optionSheet("stingray"), "opt_nga_001").description,
    "Standard, Corner Exit. NPP Performance exhaust is standard on all 2027's",
    "Stingray NGA description"
  );
  assert.equal(rowFor(optionSheet("grand_sport"), "opt_nga_001").description, "Standard, Corner Exit", "Grand Sport NGA description");
  assert.equal(rowFor(optionSheet("z06"), "opt_nga_001").description, "Standard, Quad Center Exit", "Z06 NGA description");
});

test("approved R-6 seat presentation and order are workbook-owned across promoted models", () => {
  // R-6 is a decision about what the customer sees: four seat choices, in this
  // sequence, with this copy. It is keyed by RPO and stated as a relative
  // order, because the two things the retired tuple also pinned — the physical
  // option_id and the absolute display_order — are per-model authoring details
  // with no customer meaning. Grand Sport X really does use a different AE4 row
  // id, and ZR1/ZR1X really do space their orders 10/25/40/80; the retired form
  // called all three a failure. This form covers all six models instead of
  // three and still fails on a reordered, renamed, added, or dropped seat.
  const expectedSeats = [
    ["AQ9", "GT1 Bucket Seats", ""],
    ["AH2", "GT2 Bucket Seats", ""],
    ["AE4", "Competition Sport Bucket Seats", ""],
    ["AUP", "Asymmetrical Seats", "Competition Driver Seat, GT2 Passenger Seat"],
  ];

  for (const sheetName of OPTION_SHEETS) {
    const activeSeatRows = rowsBySheet
      .get(sheetName)
      .filter((row) => row.section_id === "sec_seat_002" && isActive(row))
      .sort((left, right) => Number(left.display_order) - Number(right.display_order));

    assert.deepEqual(
      activeSeatRows.map((row) => [row.rpo, row.option_name, row.description ?? ""]),
      expectedSeats,
      `${sheetName} active seat presentation/order`
    );
    const orders = activeSeatRows.map((row) => Number(row.display_order));
    assert.deepEqual(orders, [...orders].sort((a, b) => a - b), `${sheetName} seat display order is not ascending`);
    assert.equal(new Set(orders).size, orders.length, `${sheetName} seat display order has a collision`);
  }
});

test("source sheets use concise section-aware brake caliper labels", () => {
  const expectedByOptionId = {
    opt_j6a_001: "Black Painted Calipers",
    opt_j6f_001: "Bright Red-Painted Calipers",
    opt_j6e_001: "Velocity Yellow-Painted Calipers",
    opt_j6n_001: "Edge Red-Painted Calipers",
    opt_j6b_001: "Blue-Painted Calipers",
  };

  // Widened from two hardcoded sheets to every model that carries the caliper.
  for (const [optionId, expectedName] of Object.entries(expectedByOptionId)) {
    for (const sheetName of sheetsCarrying(optionId)) {
      const matchingRows = rowsBySheet.get(sheetName).filter((row) => row.option_id === optionId);
      assert.equal(matchingRows.length, 1, `${sheetName} should contain exactly one ${optionId}`);
      assert.equal(matchingRows[0].option_name, expectedName, `${sheetName} ${optionId}`);
    }
  }
});

test("source sheets use concise removable-roof labels with consistent order", () => {
  // Same treatment as the seats: copy is a decision, absolute display_order is
  // not. Grand Sport X spaces these 10/20/30 where the others use 10/11/12 —
  // the decision is that the body-colour panel precedes the carbon-fibre panel
  // precedes the transparent one, which both spacings honour. ZR1/ZR1X carry
  // only C2Z, so the roof rows they lack are not asserted against them.
  const ROOF_SEQUENCE = [
    ["opt_cf7_001", "Body-Color Roof Panel", "Removable"],
    ["opt_c2z_001", "Visible Carbon Fiber Roof Panel", "Removable with body-color surround"],
    ["opt_cc3_001", "Transparent Roof Panel", "Removable"],
  ];

  for (const [optionId, expectedName, expectedDescription] of ROOF_SEQUENCE) {
    for (const sheetName of sheetsCarrying(optionId)) {
      const row = rowFor(sheetName, optionId);
      assert.equal(row.option_name, expectedName, `${sheetName} ${optionId} name`);
      assert.equal(row.description, expectedDescription, `${sheetName} ${optionId} description`);
    }
  }

  for (const sheetName of OPTION_SHEETS) {
    const orders = ROOF_SEQUENCE.map(([optionId]) =>
      rowsBySheet.get(sheetName).find((row) => row.option_id === optionId && isActive(row)),
    )
      .filter(Boolean)
      .map((row) => Number(row.display_order));
    assert.deepEqual(
      orders,
      [...orders].sort((left, right) => left - right),
      `${sheetName} removable-roof rows are out of sequence`
    );

    assert.equal(
      rowsBySheet.get(sheetName).some((row) => row.option_id === "opt_cf7_002"),
      false,
      `${sheetName} should not retain inactive CF7 standard mirror source row`
    );
  }
});

test("Stingray and Grand Sport engine appearance orders match reviewed Grand Sport source copy", () => {
  const expectedEngineRows = [
    ["B6P", 1, "opt_b6p_001", "opt_b6p_001", "Includes carbon fiber trim, (D3V) engine lighting and (SL9) engine specification plaque, LPO"],
    ["ZZ3", 5, "opt_zz3_001", "opt_zz3_001", "Includes window under tonneau cover, (BC7) Black LS6 engine cover and (SL9) engine specification plaque, LPO"],
    ["D3V", 10, "opt_d3v_001", "opt_d3v_001", ""],
    ["SL9", 11, "opt_sl9_001", "opt_sl9_001", "LPO. Genuine Corvette Accessory"],
    ["BC7", 19, "opt_bc7_001", "opt_bc7_001", ""],
    ["BCP", 20, "opt_bcp_001", "opt_bcp_002", "Includes engine lighting"],
    ["BCS", 30, "opt_bcs_001", "opt_bcs_002", "Includes engine lighting"],
    ["BC4", 40, "opt_bc4_001", "opt_bc4_002", "New for 2027. Includes engine lighting"],
    ["SLK", 50, "opt_slk_001", "opt_slk_001", "LPO. Genuine Corvette Accessory"],
    ["SLN", 60, "opt_sln_001", "opt_sln_001", "LPO. Features Jake Logo. Genuine Corvette Accessory"],
    ["VUP", 70, "opt_vup_001", "opt_vup_001", "LPO. Genuine Corvette Accessory"],
  ];

  for (const [rpo, expectedOrder, stingrayOptionId, grandSportOptionId, expectedGrandSportDescription] of expectedEngineRows) {
    const stingrayRow = rowFor(optionSheet("stingray"), stingrayOptionId);
    const grandSportRow = rowFor(optionSheet("grand_sport"), grandSportOptionId);
    assert.equal(stingrayRow.section_id, "sec_engi_001", `stingray_options ${rpo} section`);
    assert.equal(grandSportRow.section_id, "sec_engi_001", `grandSport_options ${rpo} section`);
    assert.equal(Number(stingrayRow.display_order), expectedOrder, `stingray_options ${rpo} display order`);
    assert.equal(Number(grandSportRow.display_order), expectedOrder, `grandSport_options ${rpo} display order`);
    assert.equal(grandSportRow.description ?? "", expectedGrandSportDescription, `grandSport_options ${rpo} description`);
  }
});

test("source sheets keep accessory branding in descriptions when the base product remains identifiable", () => {
  const expectedRows = {
    stingray_options: {
      opt_sln_001: ["Visible Carbon Fiber Engine Cross Brace", "LPO. Features Jake Logo. Genuine Corvette Accessory"],
      opt_vtb_001: ["Black Rear Fascia/Roof Protector", "LPO. Embroidered crossed flags logo. Genuine Corvette Accessory"],
      opt_rwh_001: ["Black Premium Indoor Car Cover", "LPO. Crossed flags logo. Genuine Corvette Accessory"],
      opt_sl1_001: ["Red Premium Indoor Car Cover", "LPO. Stingray logo. Genuine Corvette Accessory."],
      opt_wkq_001: [
        "Black Premium Indoor Car Cover with Access Panels",
        "LPO. Crossed flags logo. Access panels allow access to the front and rear trunks without removing the cover from the car. Genuine Corvette Accessory.",
      ],
      opt_rnx_001: [
        "Gray Premium Outdoor Car Cover with Access Panels",
        "LPO. Includes access panels and Corvette silhouette within the Stingray logo. Genuine Corvette Accessory.",
      ],
      opt_rwj_001: ["Gray Premium Outdoor Car Cover", "LPO. Crossed flags logo and Corvette silhouette. Genuine Corvette Accessory"],
      opt_pef_001: [
        "Contoured Liner Protection Package",
        "LPO. Includes (CAV) Jake logo contoured cargo area liners and (RIA) Jake logo all-weather floor liners. Genuine Corvette Accessory",
      ],
      opt_ria_001: ["All-Weather Floor Liners", "LPO. Jake logo. Genuine Corvette Accessory"],
      opt_cav_001: ["Contoured Cargo Area Liners", "LPO. Jake logo. Genuine Corvette Accessory"],
      opt_vyw_001: [
        "Premium Carpeted Floor Mats",
        "LPO. Features car silhouette logo on Stingray, Grand Sport, ZR1 and ZR1X models. Genuine Corvette Accessory.",
      ],
    },
    grandSport_options: {
      opt_pef_001: [
        "Contoured Liner Protection Package",
        "LPO. Includes (CAV) Jake logo contoured cargo area liners and (RIA) Jake logo all-weather floor liners. Genuine Corvette Accessory",
      ],
      opt_cav_001: ["Contoured Cargo Area Liners", "LPO. Jake logo. Genuine Corvette Accessory"],
      opt_sig_001: ["Clear Smoked Spoiler Extension", "LPO. Jake logo. Genuine Corvette Accessory"],
    },
    z06_options: {
      opt_pef_001: [
        "Contoured Liner Protection Package",
        "LPO. Includes (CAV) Jake logo contoured cargo area liners and (RIA) Jake logo all-weather floor liners. Genuine Corvette Accessory",
      ],
      opt_cav_001: ["Contoured Cargo Area Liners", "LPO. Jake logo. Genuine Corvette Accessory"],
    },
  };

  for (const [sheetName, rows] of Object.entries(expectedRows)) {
    for (const [optionId, [expectedName, expectedDescription]] of Object.entries(rows)) {
      const row = rowFor(sheetName, optionId);
      assert.equal(row.option_name, expectedName, `${sheetName} ${optionId} name`);
      assert.equal(row.description, expectedDescription, `${sheetName} ${optionId} description`);
    }
  }
});