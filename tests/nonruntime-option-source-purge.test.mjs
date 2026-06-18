import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import test from "node:test";

function workbookRows(sheetName) {
  const output = execFileSync(
    ".venv/bin/python",
    [
      "-c",
      `from openpyxl import load_workbook\nimport json\n\ndef clean(value):\n    if value is None:\n        return \"\"\n    if isinstance(value, bool):\n        return \"True\" if value else \"False\"\n    if isinstance(value, float) and value.is_integer():\n        return str(int(value))\n    return str(value).strip()\n\nwb = load_workbook(\"stingray_master.xlsx\", read_only=True, data_only=True)\nws = wb[${JSON.stringify(sheetName)}]\nheaders = [clean(cell.value) for cell in next(ws.iter_rows(min_row=1, max_row=1))]\nrows = []\nfor raw in ws.iter_rows(min_row=2, values_only=True):\n    row = {header: clean(value) for header, value in zip(headers, raw) if header}\n    if any(row.values()):\n        rows.append(row)\nwb.close()\nprint(json.dumps(rows))`,
    ],
    { encoding: "utf8" }
  );
  return JSON.parse(output);
}

const approvedDeletes = {
  stingray: {
    optionSheet: "stingray_options",
    ovsSheet: "stingray_ovs",
    optionIds: [
      "opt_38s_001",
      "opt_36s_001",
      "opt_37s_001",
      "opt_n26_001",
      "opt_tu7_001",
      "opt_r9w_001",
      "opt_r6p_001",
      "opt_prb_001",
      "opt_r9y_001",
      "opt_r9v_001",
      "opt_r9l_001",
      "opt_j6a_002",
      "opt_eyt_002",
      "opt_cm9_002",
      "opt_nga_002",
      "opt_efr_002",
      "opt_cf7_002",
      "opt_719_002",
      "opt_fe1_002",
      "opt_qeb_002",
    ],
    componentRpos: ["36S", "37S", "38S", "N26", "TU7"],
    deferredOptionIds: [
      "opt_u5g_001",
      "opt_004",
      "opt_ive_001",
      "opt_008",
      "opt_ue1_001",
      "opt_u2k_001",
      "opt_vv4_001",
      "opt_ppw_001",
    ],
  },
  grand_sport: {
    optionSheet: "grandSport_options",
    ovsSheet: "grandSport_ovs",
    optionIds: [
      "opt_aq9_004",
      "opt_aq9_003",
      "opt_ah2_003",
      "opt_aq9_002",
      "opt_ae4_001",
      "opt_ae4_003",
      "opt_ah2_002",
      "opt_38s_001",
      "opt_36s_001",
      "opt_37s_001",
      "opt_n26_001",
      "opt_tu7_001",
      "opt_r9w_001",
      "opt_r6p_001",
      "opt_prb_001",
      "opt_r9y_001",
      "opt_r9v_001",
      "opt_r9l_001",
      "opt_u5g_001",
      "opt_ue1_001",
      "opt_u2k_001",
      "opt_vv4_001",
      "opt_009",
      "opt_j6a_002",
      "opt_eyt_002",
      "opt_cm9_002",
      "opt_nga_002",
      "opt_efr_002",
      "opt_cf7_002",
      "opt_719_002",
      "opt_swm_002",
    ],
    componentRpos: ["36S", "37S", "38S", "N26", "TU7"],
    deferredOptionIds: ["opt_aq9_001", "opt_ah2_001", "opt_ae4_002", "opt_aup_001", "opt_ive_001"],
  },
  z06: {
    optionSheet: "z06_options",
    ovsSheet: "z06_ovs",
    optionIds: ["opt_36s_001", "opt_37s_001", "opt_38s_001", "opt_n26_001", "opt_n2z_001", "opt_tu7_001"],
    componentRpos: ["36S", "37S", "38S", "N26", "N2Z", "TU7"],
    deferredOptionIds: [
      "opt_ae4_002",
      "opt_ah2_001",
      "opt_aq9_001",
      "opt_aup_001",
      "opt_129",
      "opt_ive_001",
      "opt_u2k_002",
      "opt_u5g_002",
      "opt_ue1_002",
      "opt_vv4_002",
    ],
  },
};

const optionRowsBySheet = new Map();
const ovsRowsBySheet = new Map();
for (const config of Object.values(approvedDeletes)) {
  optionRowsBySheet.set(config.optionSheet, workbookRows(config.optionSheet));
  ovsRowsBySheet.set(config.ovsSheet, workbookRows(config.ovsSheet));
}
const sectionPresentationRows = workbookRows("section_presentation");
const componentRows = workbookRows("interior_components");

test("approved non-runtime option source rows are absent from option and OVS sheets", () => {
  for (const [modelKey, config] of Object.entries(approvedDeletes)) {
    const optionIds = new Set(optionRowsBySheet.get(config.optionSheet).map((row) => row.option_id));
    const ovsOptionIds = new Set(ovsRowsBySheet.get(config.ovsSheet).map((row) => row.option_id));
    for (const optionId of config.optionIds) {
      assert.equal(optionIds.has(optionId), false, `${modelKey} ${config.optionSheet} should not contain ${optionId}`);
      assert.equal(ovsOptionIds.has(optionId), false, `${modelKey} ${config.ovsSheet} should not contain ${optionId}`);
    }
  }
});

test("purged sections no longer have active-model option source rows", () => {
  for (const [modelKey, config] of Object.entries(approvedDeletes)) {
    const rows = optionRowsBySheet.get(config.optionSheet);
    assert.deepEqual(
      rows.filter((row) => row.section_id === "sec_cust_002").map((row) => row.option_id),
      [],
      `${modelKey} should not retain Custom Stitch option-source rows`
    );
    assert.deepEqual(
      rows.filter((row) => row.section_id === "sec_onst_001").map((row) => row.option_id),
      [],
      `${modelKey} should not retain inactive OnStar/service-plan option-source rows`
    );
    assert.deepEqual(
      rows.filter((row) => row.section_id === "sec_stan_002" && row.active !== "True").map((row) => row.option_id),
      [],
      `${modelKey} should not retain inactive duplicate standard-equipment rows`
    );
  }
});

test("component-owned RPOs remain owned by interior_components, not inactive option rows", () => {
  for (const [modelKey, config] of Object.entries(approvedDeletes)) {
    const optionRows = optionRowsBySheet.get(config.optionSheet);
    const inactiveComponentOptions = optionRows.filter((row) => config.componentRpos.includes(row.rpo) && row.active !== "True");
    assert.deepEqual(
      inactiveComponentOptions.map((row) => `${row.option_id}:${row.rpo}:${row.section_id}`),
      [],
      `${modelKey} should not retain inactive component-owned source options`
    );

    const activeComponents = componentRows.filter((row) => row.model_key === modelKey && row.active === "True");
    for (const rpo of config.componentRpos) {
      assert.equal(
        activeComponents.some((row) => row.rpo === rpo),
        true,
        `${modelKey} should retain active interior_components ownership for ${rpo}`
      );
    }
  }
});

test("obsolete custom-stitch presentation suppressors are gone after source-row purge", () => {
  for (const modelKey of ["stingray", "z06"]) {
    assert.equal(
      sectionPresentationRows.some((row) => row.model_key === modelKey && row.section_id === "sec_cust_002" && row.active === "True"),
      false,
      `${modelKey} should not need an active sec_cust_002 presentation suppressor after source purge`
    );
  }
});

test("Stingray active seats collapse to the canonical Grand Sport/Z06 source shape", () => {
  const seatRows = optionRowsBySheet
    .get("stingray_options")
    .filter((row) => row.section_id === "sec_seat_002" && row.active === "True")
    .sort((a, b) => Number(a.display_order) - Number(b.display_order));
  assert.deepEqual(
    seatRows.map((row) => [row.option_id, row.rpo, row.selectable, row.active]),
    [
      ["opt_aq9_001", "AQ9", "True", "True"],
      ["opt_ah2_001", "AH2", "True", "True"],
      ["opt_ae4_002", "AE4", "True", "True"],
      ["opt_aup_001", "AUP", "True", "True"],
    ]
  );

  const retiredSeatIds = [
    "opt_aq9_002",
    "opt_aq9_003",
    "opt_aq9_004",
    "opt_ah2_002",
    "opt_ah2_003",
    "opt_ae4_001",
    "opt_ae4_003",
  ];
  const optionIds = new Set(optionRowsBySheet.get("stingray_options").map((row) => row.option_id));
  const ovsOptionIds = new Set(ovsRowsBySheet.get("stingray_ovs").map((row) => row.option_id));
  for (const optionId of retiredSeatIds) {
    assert.equal(optionIds.has(optionId), false, `stingray_options should not retain retired seat row ${optionId}`);
    assert.equal(ovsOptionIds.has(optionId), false, `stingray_ovs should not retain retired seat row ${optionId}`);
  }

  const standardTechRows = optionRowsBySheet
    .get("stingray_options")
    .filter((row) => row.section_id === "sec_tech_001" && row.active === "True")
    .map((row) => row.option_id)
    .sort();
  assert.deepEqual(standardTechRows, ["opt_004", "opt_008", "opt_ive_001", "opt_ppw_001", "opt_u2k_001", "opt_u5g_001", "opt_ue1_001", "opt_vv4_001"]);
});

test("deferred active emitted standard-equipment rows remain in source sheets", () => {
  for (const [modelKey, config] of Object.entries(approvedDeletes)) {
    const optionRows = optionRowsBySheet.get(config.optionSheet);
    const optionIds = new Set(optionRows.map((row) => row.option_id));
    for (const optionId of config.deferredOptionIds) {
      assert.equal(optionIds.has(optionId), true, `${modelKey} deferred emitted row ${optionId} should remain`);
    }
  }
});
