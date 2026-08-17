import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

import { relationshipPairs, workbookInteriorRelationships } from "./lib/interior-relationships.mjs";

function makeElement() {
  return {
    textContent: "",
    innerHTML: "",
    value: "",
    dataset: {},
    listeners: {},
    hidden: false,
    addEventListener(type, listener) {
      this.listeners[type] = listener;
    },
    querySelectorAll() {
      return [];
    },
    querySelector() {
      return null;
    },
    closest() {
      return makeElement();
    },
    scrollTo() {},
    click() {
      this.listeners.click?.({ target: this });
    },
  };
}

function loadDataWindow() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync("form-app/data.js", "utf8"), context);
  return context.window;
}

function loadRuntime() {
  const dataWindow = loadDataWindow();
  const elements = new Map();
  const context = {
    window: {
      ...dataWindow,
      turnstile: {
        render(selector, options) {
          options.callback?.("test-turnstile-token");
          return "test-widget-id";
        },
        reset() {},
      },
      scrollX: 0,
      scrollY: 0,
      scrollTo() {},
    },
    fetch: async () => ({ ok: true, async json() { return { success: true }; } }),
    document: {
      querySelector(selector) {
        if (!elements.has(selector)) elements.set(selector, makeElement());
        return elements.get(selector);
      },
      createElement() {
        return makeElement();
      },
    },
    elements,
    Intl,
    Number,
    Set,
    Map,
    Boolean,
    Object,
    String,
    Date,
    URL: {
      createObjectURL() { return ""; },
      revokeObjectURL() {},
    },
    Blob: class TestBlob {},
  };
  const source = fs.readFileSync("form-app/app.js", "utf8").replace(
    /\ninit\(\);\s*$/,
    `
window.__testApi = {
  get activeModelKey() { return activeModelKey; },
  get state() { return state; },
  get data() { return data; },
  activateModel,
  activeChoiceRows,
  resetDefaults,
  reconcileSelections,
  handleChoice,
  currentOrder,
  compactOrder,
  missingRequired,
  missingRequirementDetails,
  computeAutoAdded,
  optionPrice,
  disableReasonForChoice,
};
init();
`
  );
  vm.runInNewContext(source, context);
  return context.window.__testApi;
}

function z06Runtime({ bodyStyle = "coupe", trimLevel = "1LZ" } = {}) {
  const runtime = loadRuntime();
  runtime.activateModel("z06");
  runtime.state.bodyStyle = bodyStyle;
  runtime.state.trimLevel = trimLevel;
  runtime.resetDefaults();
  runtime.reconcileSelections();
  return runtime;
}

function choice(runtime, rpo) {
  const found = runtime.activeChoiceRows().find((item) => item.rpo === rpo);
  assert.ok(found, `expected active Z06 choice ${rpo}`);
  return found;
}

function maybeChoice(runtime, rpo) {
  return runtime.activeChoiceRows().find((item) => item.rpo === rpo);
}

function selectedRpos(runtime) {
  const choices = runtime.activeChoiceRows();
  return [...runtime.state.selected].map((id) => choices.find((choice) => choice.option_id === id)?.rpo || id).sort();
}

function autoAddedRpos(runtime) {
  const choices = runtime.activeChoiceRows();
  return [...runtime.computeAutoAdded().keys()].map((id) => choices.find((choice) => choice.option_id === id)?.rpo || id).sort();
}


test("Z06 gas guzzler tax defaults into every build and prices up with T0F/T0G", () => {
  const runtime = z06Runtime();
  const r8e = choice(runtime, "R8E");
  assert.equal(r8e.step_key, "standard_equipment", "R8E should stay outside customer option steps");
  assert.equal(runtime.data.steps.some((step) => step.step_key === "standard_equipment"), false, "standard equipment is not a visible option step");
  assert.equal(r8e.selectable, "True", "R8E should use default-selection plumbing");
  assert.equal(runtime.state.selected.has(r8e.option_id), true, "R8E should default into the selected build state");
  assert.equal(autoAddedRpos(runtime).includes("R8E"), false, "R8E should not be duplicated as an auto-added item");
  assert.equal(runtime.optionPrice(r8e.option_id), 2600, "R8E should default to the base gas guzzler tax");

  const initialOrderItem = runtime.currentOrder().selected_options.find((item) => item.rpo === "R8E");
  assert.ok(initialOrderItem, "R8E should appear in selected order-summary output");
  assert.equal(initialOrderItem.price, 2600);
  assert.equal(initialOrderItem.section_key, "required_charges");

  runtime.handleChoice(choice(runtime, "T0F"));
  runtime.reconcileSelections();
  assert.equal(runtime.optionPrice(r8e.option_id), 3000, "T0F should raise R8E to $3,000");

  const t0gRuntime = z06Runtime();
  t0gRuntime.handleChoice(choice(t0gRuntime, "T0G"));
  t0gRuntime.reconcileSelections();
  assert.equal(t0gRuntime.optionPrice(r8e.option_id), 3000, "T0G should raise R8E to $3,000");

  for (const rpo of ["Z07", "PDD", "PDF"]) {
    const packageRuntime = z06Runtime();
    packageRuntime.handleChoice(choice(packageRuntime, rpo));
    packageRuntime.reconcileSelections();
    assert.equal(
      packageRuntime.optionPrice(r8e.option_id),
      3000,
      `${rpo} should raise R8E to $3,000 when T0F/T0G is on the build through auto-adds`
    );
  }
});

// Checkpoint 1 of the fast layered validation suite (spec §9) rewrote this
// test. It used to walk a 22-row interior/seatbelt table copied into this file
// and assert the retired behaviour that an included seatbelt colour locks out
// every peer and permits only Black. PR #19 landed the Seatbelt_Rules.txt
// authority: a peer the workbook does not mark unavailable IS selectable, adds
// D30 where a colour-override row says so, and replaces the included colour.
//
// Nothing here names an interior, a seatbelt, or D30. Cases, peers, and
// expectations are read from the model's registered workbook sheets, so a
// workbook change to any seatbelt relationship moves the coverage with it
// instead of failing a stale literal — and an omission in the generated payload
// fails the parity assertions rather than silently shrinking the sweep (§4.3).
test("every interior-included option obeys its workbook include, exclude, and override rows", () => {
  const probe = z06Runtime({ trimLevel: "3LZ" });
  const data = probe.data;
  const interiorsById = new Map(data.interiors.map((interior) => [interior.interior_id, interior]));

  const groupForOption = new Map();
  for (const group of data.exclusiveGroups) {
    for (const optionId of group.option_ids) groupForOption.set(optionId, group);
  }
  const optionIds = new Set(data.choices.map((row) => row.option_id));

  // The expected relationships are read from the model's registered sheets, not
  // from the payload under test. `z06-runtime-contract` already owns include
  // parity; excludes and colour overrides had no independent owner until PR
  // review pointed it out, so a dropped row of either kind removed the case and
  // its expectation at once.
  const workbook = workbookInteriorRelationships({
    modelKey: "z06",
    interiorIds: new Set(interiorsById.keys()),
    optionIds,
  });

  const registryExcludes = new Map();
  for (const rule of data.rules) {
    if (rule.rule_type !== "excludes" || rule.active !== "True") continue;
    if (!optionIds.has(rule.source_id) || !interiorsById.has(rule.target_id)) continue;
    if (!registryExcludes.has(rule.target_id)) registryExcludes.set(rule.target_id, new Set());
    registryExcludes.get(rule.target_id).add(rule.source_id);
  }
  const registryOverrides = new Map();
  for (const override of data.colorOverrides) {
    if (!interiorsById.has(override.interior_id) || !optionIds.has(override.option_id)) continue;
    if (!registryOverrides.has(override.interior_id)) registryOverrides.set(override.interior_id, new Map());
    registryOverrides.get(override.interior_id).set(override.option_id, override.adds_rpo);
  }

  assert.ok(relationshipPairs(workbook.includes).length > 0, "no interior include row resolves for z06");
  assert.ok(relationshipPairs(workbook.excludes).length > 0, "no interior exclude row resolves for z06");
  assert.ok(relationshipPairs(workbook.overrides).length > 0, "no colour-override row resolves for z06");
  assert.deepEqual(
    relationshipPairs(registryExcludes),
    relationshipPairs(workbook.excludes),
    "published interior exclude rules drifted from the workbook rule-mapping sheet",
  );
  assert.deepEqual(
    relationshipPairs(registryOverrides),
    relationshipPairs(workbook.overrides),
    "published colour overrides drifted from the workbook colour-override sheet",
  );

  const cases = [...workbook.includes]
    .flatMap(([interiorId, included]) => [...included].map((includedOptionId) => ({ interiorId, includedOptionId })))
    .filter(({ includedOptionId }) => groupForOption.has(includedOptionId))
    .map(({ interiorId, includedOptionId }) => ({
      interior: interiorsById.get(interiorId),
      includedOptionId,
      group: groupForOption.get(includedOptionId),
    }));

  assert.ok(cases.length > 0, "no workbook-authored interior include resolves into an exclusive group");

  for (const { interior, includedOptionId, group } of cases) {
    const interiorId = interior.interior_id;
    const runtime = z06Runtime({ trimLevel: interior.trim_level });

    // Select the interior through its own seat option, read from the interior
    // row rather than parsed out of the interior id.
    runtime.handleChoice(choice(runtime, interior.seat_code));
    runtime.state.selectedInterior = interiorId;
    runtime.reconcileSelections();

    assert.equal(
      runtime.computeAutoAdded().has(includedOptionId),
      true,
      `${interiorId} should auto-add its included option ${includedOptionId}`,
    );
    assert.equal(
      runtime.optionPrice(includedOptionId),
      0,
      `${interiorId} should price its included option at zero`,
    );

    // Peers the workbook marks unavailable for this interior, and the D30-style
    // RPO each remaining peer adds, both read from the registry rows.
    const blockedPeers = new Set(
      data.rules
        .filter(
          (rule) =>
            rule.rule_type === "excludes" &&
            rule.active === "True" &&
            rule.target_id === interiorId &&
            group.option_ids.includes(rule.source_id),
        )
        .map((rule) => rule.source_id),
    );
    const addsByPeer = new Map(
      data.colorOverrides
        .filter((override) => override.interior_id === interiorId && group.option_ids.includes(override.option_id))
        .map((override) => [override.option_id, override.adds_rpo]),
    );

    let selectedPeer = null;
    for (const peerId of group.option_ids) {
      if (peerId === includedOptionId) continue;
      const peer = runtime.activeChoiceRows().find((row) => row.option_id === peerId);
      assert.ok(peer, `${interiorId} peer ${peerId} should be present in the runtime`);

      const reason = runtime.disableReasonForChoice(peer);
      runtime.handleChoice(peer);
      runtime.reconcileSelections();

      if (blockedPeers.has(peerId)) {
        assert.equal(
          runtime.state.selected.has(peerId),
          false,
          `${interiorId} should refuse ${peerId}, which the workbook marks unavailable`,
        );
        assert.notEqual(reason, "", `${interiorId} should explain why ${peerId} is unavailable`);
        assert.equal(
          selectedPeer === null || runtime.state.selected.has(selectedPeer),
          true,
          `${interiorId} lost its selected peer when a blocked peer was clicked`,
        );
        continue;
      }

      assert.equal(reason, "", `${interiorId} should offer ${peerId}: no workbook row blocks it`);
      assert.equal(
        runtime.state.selected.has(peerId),
        true,
        `${interiorId} should accept ${peerId}, which no workbook row blocks`,
      );
      assert.equal(
        runtime.computeAutoAdded().has(includedOptionId),
        false,
        `${interiorId} should drop its included option once a peer is chosen`,
      );

      // §4.3 item 7: at most one peer of a single-selection group is selected.
      assert.equal(group.selection_mode, "single_within_group");
      // Copied into this realm: `group.option_ids` comes from the vm context,
      // and a cross-realm array fails a prototype-sensitive deep compare.
      const selectedPeers = [...group.option_ids].filter((id) => runtime.state.selected.has(id));
      assert.deepEqual(selectedPeers, [peerId], `${interiorId} holds more than one peer of ${group.group_id}`);

      const addsRpo = addsByPeer.get(peerId);
      if (addsRpo) {
        const added = runtime.state.selected.has(addsRpo) || runtime.computeAutoAdded().has(addsRpo);
        assert.equal(added, true, `${interiorId} ${peerId} should add ${addsRpo} per its colour-override row`);
      }
      selectedPeer = peerId;
    }
  }
});

test("Z06 GBA paint blocks CBF and EDU but not CFL ground effect", () => {
  const runtime = z06Runtime();
  runtime.handleChoice(choice(runtime, "GBA"));
  runtime.reconcileSelections();
  const cbf = choice(runtime, "CBF");
  assert.match(runtime.disableReasonForChoice(cbf), /GBA|black paint|CBF/i);
  runtime.handleChoice(cbf);
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(cbf.option_id), false, "CBF should not stick with GBA selected");

  const edu = choice(runtime, "EDU");
  assert.match(runtime.disableReasonForChoice(edu), /GBA|black paint|EDU/i);
  runtime.handleChoice(edu);
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(edu.option_id), false, "EDU should not stick with GBA selected");

  const cfl = choice(runtime, "CFL");
  assert.equal(runtime.disableReasonForChoice(cfl), "", "CFL should remain selectable with GBA selected");
});

test("Z06 CBF conflicts only with its explicit exterior and ground-effect blockers", () => {
  const runtime = z06Runtime();
  const cbf = choice(runtime, "CBF");
  assert.equal(runtime.disableReasonForChoice(cbf), "", "CBF should be normally selectable");

  runtime.handleChoice(cbf);
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(cbf.option_id), true, "CBF should remain selected without blockers");
  assert.match(runtime.disableReasonForChoice(choice(runtime, "EFY")), /CBF|ground effects|exterior accents/i);
  assert.match(runtime.disableReasonForChoice(choice(runtime, "CFV")), /CBF|ground effects|exterior accents/i);
  assert.match(runtime.disableReasonForChoice(choice(runtime, "CFZ")), /CBF|ground effects|exterior accents/i);
  assert.equal(runtime.disableReasonForChoice(choice(runtime, "EDU")), "", "CBF should not block EDU");
});

test("Z06 Z07 defaults T0F, allows T0G switching, and keeps J57 included at zero", () => {
  const runtime = z06Runtime();
  const z07 = choice(runtime, "Z07");

  assert.equal(runtime.disableReasonForChoice(z07), "", "Z07 should be selectable before choosing T0F/T0G");
  runtime.handleChoice(z07);
  runtime.reconcileSelections();

  assert.equal(runtime.state.selected.has(z07.option_id), true, "Z07 should be selected");
  assert.equal(autoAddedRpos(runtime).includes("J57"), true, "Z07 should auto-add J57");
  assert.equal(autoAddedRpos(runtime).includes("T0F"), true, "Z07 should default the required aero choice to T0F");
  assert.equal(autoAddedRpos(runtime).includes("CFZ"), true, "Z07 default T0F should auto-add CFZ");
  assert.equal(runtime.state.selected.has(choice(runtime, "T0E").option_id), false, "Z07 should replace the T0E default spoiler");
  assert.equal(runtime.optionPrice(choice(runtime, "J57").option_id), 0, "Z07-included J57 should price at zero");
  assert.doesNotMatch(
    runtime.missingRequirementDetails().map((item) => item.detail).join("\n"),
    /T0F|T0G|aero/i,
    "Z07 should satisfy its aero requirement with default T0F"
  );

  runtime.handleChoice(choice(runtime, "J57"));
  runtime.reconcileSelections();
  assert.equal(autoAddedRpos(runtime).includes("J57"), true, "auto-added J57 should not be removable while Z07 is selected");

  runtime.handleChoice(choice(runtime, "T0G"));
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(choice(runtime, "T0G").option_id), true, "T0G should be selectable as the Z07 aero alternate");
  assert.equal(autoAddedRpos(runtime).includes("T0F"), false, "T0G should suppress the T0F default");
  assert.equal(autoAddedRpos(runtime).includes("CFV"), true, "T0G should auto-add CFV");
});

test("Z06 Z07 locks out J56 while keeping included J57 active", () => {
  const runtime = z06Runtime();
  const z07 = choice(runtime, "Z07");

  runtime.handleChoice(z07);
  runtime.reconcileSelections();

  assert.equal(runtime.state.selected.has(z07.option_id), true, "Z07 should be selected");
  assert.equal(autoAddedRpos(runtime).includes("J57"), true, "Z07 should auto-add J57");
  assert.match(
    runtime.disableReasonForChoice(choice(runtime, "J56")),
    /Z07|J57|carbon ceramic/i,
    "J56 should explain that Z07/J57 makes it unavailable"
  );

  runtime.handleChoice(choice(runtime, "J56"));
  runtime.reconcileSelections();

  assert.equal(runtime.state.selected.has(choice(runtime, "J56").option_id), false, "J56 should not stick while Z07 remains selected");
  assert.equal(autoAddedRpos(runtime).includes("J57"), true, "J57 should remain auto-added after clicking J56");
  for (const carbonWheelRpo of ["ROY", "ROZ", "STZ"]) {
    assert.equal(runtime.disableReasonForChoice(choice(runtime, carbonWheelRpo)), "", `${carbonWheelRpo} should remain selectable through the J57 carbon-wheel path`);
  }
});

test("Z06 PDB locks out J56 while preserving J57 and ROY defaults", () => {
  const runtime = z06Runtime();
  const pdb = choice(runtime, "PDB");

  runtime.handleChoice(pdb);
  runtime.reconcileSelections();

  assert.equal(runtime.state.selected.has(pdb.option_id), true, "PDB should be selected");
  assert.equal(autoAddedRpos(runtime).includes("J57"), true, "PDB should auto-add J57");
  assert.equal(autoAddedRpos(runtime).includes("ROY"), true, "PDB should default ROY");
  assert.match(runtime.disableReasonForChoice(choice(runtime, "J56")), /PDB|J57|carbon ceramic/i, "J56 should be disabled by PDB/J57");

  runtime.handleChoice(choice(runtime, "J56"));
  runtime.reconcileSelections();

  assert.equal(runtime.state.selected.has(pdb.option_id), true, "PDB should remain selected after clicking disabled J56");
  assert.equal(runtime.state.selected.has(choice(runtime, "J56").option_id), false, "J56 should not stick while PDB remains selected");
  assert.equal(autoAddedRpos(runtime).includes("J57"), true, "J57 should remain auto-added after clicking J56");
  assert.equal(autoAddedRpos(runtime).includes("ROY"), true, "ROY should remain auto-added until switched to ROZ/STZ");
});

test("Z06 PDD and PDF inherit the Z07 J56 brake lock", () => {
  for (const rpo of ["PDD", "PDF"]) {
    const runtime = z06Runtime();
    const packageChoice = choice(runtime, rpo);

    runtime.handleChoice(packageChoice);
    runtime.reconcileSelections();

    assert.equal(runtime.state.selected.has(packageChoice.option_id), true, `${rpo} should be selected`);
    assert.equal(autoAddedRpos(runtime).includes("Z07"), true, `${rpo} should auto-add Z07`);
    assert.equal(autoAddedRpos(runtime).includes("J57"), true, `${rpo} should auto-add J57 through Z07`);
    assert.match(runtime.disableReasonForChoice(choice(runtime, "J56")), /Z07|J57|carbon ceramic/i, `${rpo} should disable J56 through Z07`);

    runtime.handleChoice(choice(runtime, "J56"));
    runtime.reconcileSelections();

    assert.equal(runtime.state.selected.has(packageChoice.option_id), true, `${rpo} should remain selected after clicking disabled J56`);
    assert.equal(runtime.state.selected.has(choice(runtime, "J56").option_id), false, `${rpo} should not allow J56 to stick`);
    assert.equal(autoAddedRpos(runtime).includes("J57"), true, `${rpo} should keep J57 auto-added`);
  }
});

test("Z06 Z07 keeps non-Z07 aero peers disabled after switching to T0G", () => {
  for (const blockedRpo of ["T0E", "5ZV"]) {
    const runtime = z06Runtime();
    runtime.handleChoice(choice(runtime, "Z07"));
    runtime.reconcileSelections();
    runtime.handleChoice(choice(runtime, "T0G"));
    runtime.reconcileSelections();

    assert.equal(runtime.state.selected.has(choice(runtime, "T0G").option_id), true, "T0G should be selected as the allowed Z07 aero alternate");
    assert.equal(autoAddedRpos(runtime).includes("T0F"), false, "T0F should not be auto-added while T0G is selected");
    assert.match(
      runtime.disableReasonForChoice(choice(runtime, blockedRpo)),
      /Z07|T0F|T0G|aero/i,
      `${blockedRpo} should stay disabled while Z07 is selected with T0G`
    );

    runtime.handleChoice(choice(runtime, blockedRpo));
    runtime.reconcileSelections();

    assert.equal(runtime.state.selected.has(choice(runtime, blockedRpo).option_id), false, `${blockedRpo} should not stick while disabled by Z07`);
    assert.equal(runtime.state.selected.has(choice(runtime, "T0G").option_id), true, "clicking a disabled non-Z07 aero peer should leave T0G selected");
    assert.equal(runtime.state.selected.has(choice(runtime, "Z07").option_id), true, "Z07 should remain selected");
  }
});

test("Z06 T0F does not require J57 as a prerequisite", () => {
  const runtime = z06Runtime();
  const t0f = choice(runtime, "T0F");

  assert.equal(runtime.disableReasonForChoice(t0f), "", "T0F should be selectable without first selecting J57");
});

test("Z06 package selections default ROY carbon wheels and make package peers consistent", () => {
  for (const rpo of ["PDB", "PDD", "PDF"]) {
    const runtime = z06Runtime();
    const packageChoice = choice(runtime, rpo);
    assert.equal(runtime.disableReasonForChoice(packageChoice), "", `${rpo} should be selectable`);
    runtime.handleChoice(packageChoice);
    runtime.reconcileSelections();

    assert.equal(runtime.state.selected.has(packageChoice.option_id), true, `${rpo} should be selected`);
    assert.equal(autoAddedRpos(runtime).includes("ROY"), true, `${rpo} should default to ROY`);
    assert.doesNotMatch(
      runtime.missingRequirementDetails().map((item) => item.detail).join("\n"),
      /ROY|ROZ|STZ|carbon fiber wheel/i,
      `${rpo} should satisfy its carbon fiber wheel requirement with default ROY`
    );
    for (const [wheelRpo, expectedDelta] of [["ROZ", 1000], ["STZ", 1500]]) {
      const carbonWheel = choice(runtime, wheelRpo);
      assert.equal(runtime.disableReasonForChoice(carbonWheel), "", `${wheelRpo} should be selectable after ${rpo}`);
      assert.equal(runtime.optionPrice(carbonWheel.option_id), expectedDelta, `${wheelRpo} should show the package-base delta when included by ${rpo}`);
    }
    runtime.handleChoice(choice(runtime, "ROZ"));
    runtime.reconcileSelections();
    assert.equal(runtime.state.selected.has(choice(runtime, "ROZ").option_id), true, `${rpo} should allow switching from ROY default to ROZ`);
    assert.equal(autoAddedRpos(runtime).includes("ROY"), false, `${rpo} should release ROY after ROZ is selected`);
    const peerRpos = ["PDB", "PDD", "PDF"].filter((peer) => peer !== rpo);
    for (const peerRpo of peerRpos) {
      assert.equal(runtime.disableReasonForChoice(choice(runtime, peerRpo)), "", `${peerRpo} should stay clickable while ${rpo} is selected`);
    }
  }
});

test("Z06 direct J57 enables carbon fiber wheels and blocks J6A", () => {
  const runtime = z06Runtime();
  runtime.handleChoice(choice(runtime, "J57"));
  runtime.reconcileSelections();

  assert.deepEqual(
    ["ROY", "ROZ", "STZ"].map((rpo) => runtime.disableReasonForChoice(choice(runtime, rpo))),
    ["", "", ""],
    "J57 should make all carbon fiber wheels selectable"
  );
  const j6a = choice(runtime, "J6A");
  assert.notEqual(runtime.disableReasonForChoice(j6a), "", "J57 should make J6A unavailable");
});

test("Z06 engine appearance, exhaust, and convertible PBC workbook rules are honored", () => {
  const coupe = z06Runtime({ bodyStyle: "coupe" });
  assert.equal(coupe.disableReasonForChoice(choice(coupe, "NWI")), "", "NWI should not require standard WUB");

  coupe.handleChoice(choice(coupe, "B6P"));
  coupe.reconcileSelections();
  assert.equal(coupe.optionPrice(choice(coupe, "D3V").option_id), 0, "B6P should zero D3V");
  assert.equal(coupe.optionPrice(choice(coupe, "SL9").option_id), 0, "B6P should zero SL9");

  const convertible = z06Runtime({ bodyStyle: "convertible" });
  const pbc = choice(convertible, "PBC");
  assert.match(convertible.disableReasonForChoice(pbc), /ZZ3/i, "PBC should require ZZ3 on convertible");
  convertible.handleChoice(choice(convertible, "ZZ3"));
  convertible.reconcileSelections();
  assert.equal(convertible.optionPrice(choice(convertible, "SL9").option_id), 0, "ZZ3 should zero SL9");
  assert.equal(convertible.disableReasonForChoice(pbc), "", "ZZ3 should satisfy PBC on convertible");
});

test("Z06 GBA paint incompatibilities and unreleased option visibility come from workbook data", () => {
  const runtime = z06Runtime();
  runtime.handleChoice(choice(runtime, "GBA"));
  runtime.reconcileSelections();

  for (const rpo of ["EFY", "ZYC", "D84", "D86"]) {
    assert.notEqual(runtime.disableReasonForChoice(choice(runtime, rpo)), "", `${rpo} should be unavailable with GBA`);
  }
  assert.equal(maybeChoice(runtime, "V8X"), undefined, "V8X should not appear as an active front-end choice");
  assert.equal(maybeChoice(runtime, "RYQ"), undefined, "RYQ should not appear as an active front-end choice");
});

test("Z06 source selectable=false standard rows are not customer-selectable", () => {
  const runtime = z06Runtime();
  const wub = choice(runtime, "WUB");
  assert.equal(wub.selectable, "False", "test fixture expects WUB to be source non-selectable");
  assert.notEqual(runtime.disableReasonForChoice(wub), "", "source non-selectable standard rows should be display-only");

  const before = selectedRpos(runtime);
  runtime.handleChoice(wub);
  runtime.reconcileSelections();
  assert.deepEqual(selectedRpos(runtime), before, "clicking source non-selectable standard row should not alter selected options");
});
