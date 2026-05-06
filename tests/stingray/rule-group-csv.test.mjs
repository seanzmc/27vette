import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const PACKAGE = "data/stingray";
const RULE_GROUPS = "logic/rule_groups.csv";
const RULE_GROUP_MEMBERS = "logic/rule_group_members.csv";

function emitFragment(packageDir = PACKAGE) {
  return JSON.parse(execFileSync(PYTHON, [SCRIPT, "--package", packageDir, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  }));
}

function runFragment(packageDir) {
  return spawnSync(PYTHON, [SCRIPT, "--package", packageDir, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
}

function tempPackage() {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-rule-group-csv-"));
  const packageDir = path.join(tempDir, "stingray");
  fs.cpSync(PACKAGE, packageDir, { recursive: true });
  return packageDir;
}

function writeRuleGroups(packageDir, rows) {
  fs.writeFileSync(
    path.join(packageDir, RULE_GROUPS),
    [
      "rule_group_id,group_type,source_selectable_id,body_style_scope,trim_level_scope,variant_scope,disabled_reason,active,legacy_group_id,legacy_notes",
      ...rows,
    ].join("\n") + "\n"
  );
}

function writeRuleGroupMembers(packageDir, rows) {
  fs.writeFileSync(
    path.join(packageDir, RULE_GROUP_MEMBERS),
    [
      "rule_group_id,target_selectable_id,member_order,active",
      ...rows,
    ].join("\n") + "\n"
  );
}

function fixturePackage() {
  const packageDir = tempPackage();
  writeRuleGroups(packageDir, [
    "rg_fixture_requires_any,requires_any,opt_5zu_001,,,,Requires TVS or 5ZZ.,true,grp_fixture_requires_any,Fixture requires any projected spoiler peer.",
  ]);
  writeRuleGroupMembers(packageDir, [
    "rg_fixture_requires_any,opt_5zz_001,20,true",
    "rg_fixture_requires_any,opt_tvs_001,10,true",
  ]);
  return packageDir;
}

test("production ruleGroup CSV schema emits the projected spoiler requires_any ruleGroups", () => {
  assert.equal(fs.existsSync(path.join(PACKAGE, RULE_GROUPS)), true);
  assert.equal(fs.existsSync(path.join(PACKAGE, RULE_GROUP_MEMBERS)), true);

  const fragment = emitFragment();

  assert.deepEqual(fragment.validation_errors, []);
	  assert.deepEqual(fragment.ruleGroups, [
	    {
	      group_id: "grp_5v7_spoiler_requirement",
	      group_type: "requires_any",
	      source_id: "opt_5v7_001",
      target_ids: ["opt_5zu_001", "opt_5zz_001"],
      body_style_scope: "",
      trim_level_scope: "",
      variant_scope: "",
      disabled_reason: "Requires 5ZU Body-Color High Wing Spoiler or 5ZZ Carbon Flash High Wing Spoiler.",
	      active: "True",
	      notes: "5V7 is available when either approved high wing spoiler is selected.",
	    },
	    {
	      group_id: "grp_5zu_paint_requirement",
	      group_type: "requires_any",
	      source_id: "opt_5zu_001",
	      target_ids: ["opt_g8g_001", "opt_gba_001", "opt_gkz_001"],
	      body_style_scope: "",
	      trim_level_scope: "",
	      variant_scope: "",
	      disabled_reason: "Requires Arctic White, Black, or Torch Red exterior paint.",
	      active: "True",
	      notes: "5ZU body-color spoiler requires one approved body color.",
	    },
	  ]);
	});

test("CSV ruleGroups emit the exact legacy requires_any runtime shape with deterministic member order", () => {
  const fragment = emitFragment(fixturePackage());

  assert.deepEqual(fragment.validation_errors, []);
  assert.deepEqual(fragment.ruleGroups, [
    {
      group_id: "grp_fixture_requires_any",
      group_type: "requires_any",
      source_id: "opt_5zu_001",
      target_ids: ["opt_tvs_001", "opt_5zz_001"],
      body_style_scope: "",
      trim_level_scope: "",
      variant_scope: "",
      disabled_reason: "Requires TVS or 5ZZ.",
      active: "True",
      notes: "Fixture requires any projected spoiler peer.",
    },
  ]);
});

const invalidCases = [
  [
    "duplicate group_id",
    ["rg_fixture_requires_any,requires_any,opt_5zu_001,,,,Requires TVS or 5ZZ.,true,grp_fixture_requires_any,Fixture.", "rg_fixture_requires_any,requires_any,opt_tvs_001,,,,Requires 5ZZ.,true,grp_fixture_duplicate,Fixture."],
    ["rg_fixture_requires_any,opt_tvs_001,10,true"],
    /rule_groups has duplicate rule_group_id: rg_fixture_requires_any/,
  ],
  [
    "missing group_id",
    [",requires_any,opt_5zu_001,,,,Requires TVS or 5ZZ.,true,grp_fixture_requires_any,Fixture."],
    ["rg_fixture_requires_any,opt_tvs_001,10,true"],
    /rule_groups has a row missing rule_group_id/,
  ],
  [
    "unsupported group_type",
    ["rg_fixture_requires_any,requires_all,opt_5zu_001,,,,Requires TVS or 5ZZ.,true,grp_fixture_requires_any,Fixture."],
    ["rg_fixture_requires_any,opt_tvs_001,10,true"],
    /rule_groups uses unsupported group_type: requires_all/,
  ],
  [
    "missing source_selectable_id",
    ["rg_fixture_requires_any,requires_any,,,,,Requires TVS or 5ZZ.,true,grp_fixture_requires_any,Fixture."],
    ["rg_fixture_requires_any,opt_tvs_001,10,true"],
    /rule_groups has a row missing source_selectable_id/,
  ],
  [
    "unknown member selectable",
    ["rg_fixture_requires_any,requires_any,opt_5zu_001,,,,Requires TVS or 5ZZ.,true,grp_fixture_requires_any,Fixture."],
    ["rg_fixture_requires_any,opt_missing_001,10,true"],
    /rule_group_members references missing selectable: opt_missing_001/,
  ],
  [
    "no active members",
    ["rg_fixture_requires_any,requires_any,opt_5zu_001,,,,Requires TVS or 5ZZ.,true,grp_fixture_requires_any,Fixture."],
    ["rg_fixture_requires_any,opt_tvs_001,10,false"],
    /rule group has no active members: rg_fixture_requires_any/,
  ],
  [
    "unsupported scope",
    ["rg_fixture_requires_any,requires_any,opt_5zu_001,coupe,,,Requires TVS or 5ZZ.,true,grp_fixture_requires_any,Fixture."],
    ["rg_fixture_requires_any,opt_tvs_001,10,true"],
    /rule_groups uses unsupported body_style_scope/,
  ],
  [
    "missing disabled_reason",
    ["rg_fixture_requires_any,requires_any,opt_5zu_001,,,,,true,grp_fixture_requires_any,Fixture."],
    ["rg_fixture_requires_any,opt_tvs_001,10,true"],
    /requires_any rule group is missing disabled_reason: rg_fixture_requires_any/,
  ],
];

for (const [name, groupRows, memberRows, pattern] of invalidCases) {
  test(`CSV ruleGroup validation rejects ${name}`, () => {
    const packageDir = tempPackage();
    writeRuleGroups(packageDir, groupRows);
    writeRuleGroupMembers(packageDir, memberRows);

    const result = runFragment(packageDir);

    assert.notEqual(result.status, 0);
    assert.match(result.stdout, pattern);
  });
}
