// Registry-driven workbook snapshot for structural node gates.
//
// Every sheet, family, typed column, and model this exposes is DERIVED from
// `corvette_form_generator.workbook_domain.registry` plus the workbook's own
// `model_master` / `model_workbook_sources` rows. Nothing here names a model,
// a sheet, or a column literally.
//
// That is the point. The retired version of this snapshot hardcoded three
// canonical source sheets and a 25-entry "future model" sheet list, so adding a
// model, renaming a source sheet, or registering a new family left the gate
// asserting over a stale subset while reporting green. A derived snapshot
// widens automatically; what it cannot do is notice that the derivation itself
// changed, which is why the callers pin named expectations on top of it.
import { execFileSync } from "node:child_process";

const SNAPSHOT_PROGRAM = `
import json
from pathlib import Path

from corvette_form_generator.editor_ops import extract_workbook, model_sheet_registry
from corvette_form_generator.workbook import workbook_truthy
from corvette_form_generator.workbook_domain import registry as reg

# Injected by the caller: the approved one-source blocker clusters, keyed by
# model. Kept out of this module so the policy lives beside its assertion.
BLOCKER_CLUSTER_RPOS = json.loads(__BLOCKER_CLUSTER_RPOS__)

extract = extract_workbook(Path("stingray_master.xlsx"))
sheets = extract["sheets"]
model_registry, sheet_family = model_sheet_registry(extract)

# Typed-column ownership for every family the registry knows, writable or not.
types_by_family = {}
for family, meta in reg.EDITOR_SHEET_META.items():
    types_by_family[family] = dict(meta.get("types", {}))
for family, meta in reg.READONLY_SHEET_META.items():
    types_by_family[family] = dict(meta.get("types", {}))

# Read-only families are addressed by their own fixed sheet name.
readonly_sheets = {
    meta["sheet"]: family for family, meta in reg.READONLY_SHEET_META.items()
}

registered = dict(reg.registered_sheet_families(extract))
registered.update(readonly_sheets)


def rows(name):
    return sheets.get(name, {}).get("rows", [])


def clean(value):
    return "" if value is None else str(value).strip()


def type_name(value):
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return type(value).__name__


# ── Typed-cell conformance over every registered sheet ────────────────
# A cell violates its family's declared type when the raw Excel value is not
# already that Python type. Text "True" and text "10" are the drift class the
# 2026-06-10 retype pass cleared from the model source sheets; this walk is
# what proves it stayed cleared, and finds it wherever else it lives.
type_violations = []
typed_columns_checked = 0
for sheet, family in sorted(registered.items()):
    declared = types_by_family.get(family) or {}
    sheet_rows = rows(sheet)
    for column, kind in sorted(declared.items()):
        values = [r.get(column) for r in sheet_rows if r.get(column) not in (None, "")]
        if not values:
            continue
        typed_columns_checked += 1
        offenders = []
        for value in values:
            if kind == "bool" and not isinstance(value, bool):
                offenders.append(value)
            elif kind == "int" and (isinstance(value, bool) or not isinstance(value, int)):
                offenders.append(value)
        if offenders:
            type_violations.append(
                {
                    "sheet": sheet,
                    "family": family,
                    "column": column,
                    "declared": kind,
                    "count": len(offenders),
                    "found_types": sorted({type_name(v) for v in offenders}),
                }
            )

# ── Model topology, derived from the workbook's own metadata rows ─────
models = {}
for row in rows("model_master"):
    model_key = clean(row.get("model_key"))
    if not model_key:
        continue
    models[model_key] = {
        "model_key": model_key,
        "registry_key": clean(row.get("registry_key")),
        "model_label": clean(row.get("model_label")),
        "model_year": row.get("model_year"),
        "expected_variant_count": row.get("expected_variant_count"),
        "default_model": row.get("default_model"),
        "active": bool(workbook_truthy(row.get("active"))),
        "source_roles": {},
        "variant_ids": [],
        "variant_display_orders": [],
        "inactive_variant_ids": [],
        "variants_missing_active_fact": [],
    }

for row in rows("model_workbook_sources"):
    model_key = clean(row.get("model_key"))
    if model_key not in models or not workbook_truthy(row.get("active")):
        continue
    role = clean(row.get("source_role"))
    if role:
        models[model_key]["source_roles"][role] = clean(row.get("sheet_name"))

variant_facts = {clean(r.get("variant_id")): r for r in rows("variant_master")}
for row in rows("model_variants"):
    model_key = clean(row.get("model_key"))
    if model_key not in models:
        continue
    variant_id = clean(row.get("variant_id"))
    entry = models[model_key]
    if not workbook_truthy(row.get("active")):
        entry["inactive_variant_ids"].append(variant_id)
        continue
    entry["variant_ids"].append(variant_id)
    entry["variant_display_orders"].append(row.get("display_order"))
    fact = variant_facts.get(variant_id)
    if fact is None or not workbook_truthy(fact.get("active")):
        entry["variants_missing_active_fact"].append(variant_id)

# ── Cross-model rule/group invariants, derived per model ──────────────
# An explicit "excludes" between two members of the same active exclusive
# group states a relationship the group already enforces. The duplicate is not
# inert: app.js skips same-group peers when scanning rules that target a
# choice, but not when scanning rules a choice is the source of, so the
# redundant row blocks one direction of a choose-one swap.
duplicate_group_excludes = []
for model_key, entry in sorted(model_registry.items()):
    family_sheets = {item["family"]: item["sheet"] for item in entry}
    group_sheet = family_sheets.get("exclusive_groups")
    member_sheet = family_sheets.get("exclusive_members")
    rule_sheet = family_sheets.get("rule_mapping")
    if not (group_sheet and member_sheet and rule_sheet):
        continue
    active_groups = {
        clean(r.get("group_id")) for r in rows(group_sheet) if workbook_truthy(r.get("active"))
    }
    group_by_option = {}
    for r in rows(member_sheet):
        if not workbook_truthy(r.get("active")):
            continue
        group_id = clean(r.get("group_id"))
        option_id = clean(r.get("option_id"))
        if group_id in active_groups and option_id:
            group_by_option.setdefault(option_id, set()).add(group_id)
    for r in rows(rule_sheet):
        if clean(r.get("rule_type")) != "excludes":
            continue
        # A replace row is a default-swap instruction, not a peer conflict.
        if clean(r.get("runtime_action")) == "replace":
            continue
        source_id = clean(r.get("source_id"))
        target_id = clean(r.get("target_id"))
        shared = sorted(
            group_by_option.get(source_id, set()) & group_by_option.get(target_id, set())
        )
        if shared:
            duplicate_group_excludes.append(
                {
                    "model_key": model_key,
                    "sheet": rule_sheet,
                    "rule_id": clean(r.get("rule_id")),
                    "group_ids": shared,
                    "source_id": source_id,
                    "target_id": target_id,
                }
            )

# ── Retired lifecycle columns, swept over every registered sheet ──────
# The rule normalization passes removed 'generation_action' and
# 'normalization_status'. The retired gate checked two named sheets; this
# walks every registered sheet so a reintroduction anywhere is caught.
RETIRED_COLUMNS = ("generation_action", "normalization_status", "price_semantic", "review_flag")
retired_column_sightings = []
for sheet in sorted(registered):
    headers = sheets.get(sheet, {}).get("headers", [])
    for column in RETIRED_COLUMNS:
        if column in headers:
            retired_column_sightings.append({"sheet": sheet, "column": column})

# ── Interior source sheet header parity ──────────────────────────────
# Models share interior sheets by role. Every sheet serving the interiors
# role must carry an identical header set, or a model reading one of them
# silently loses columns the others have.
interior_sheets = sorted(
    {
        entry["sheet"]
        for items in model_registry.values()
        for entry in items
        if entry["family"] == "interiors"
    }
)
interior_headers = {sheet: sheets.get(sheet, {}).get("headers", []) for sheet in interior_sheets}

# ── Replace-excludes rows, per model ─────────────────────────────────
# 'runtime_action=replace' means "selecting the source removes the target
# default". It is a real authoring mechanism, but a replace row between two
# members of one exclusive group is a stacked-closure row that generation-time
# derivation (rule_derivation.py) owns instead.
replace_excludes = []
for model_key, entry in sorted(model_registry.items()):
    family_sheets = {item["family"]: item["sheet"] for item in entry}
    rule_sheet = family_sheets.get("rule_mapping")
    group_sheet = family_sheets.get("exclusive_groups")
    member_sheet = family_sheets.get("exclusive_members")
    if not (rule_sheet and group_sheet and member_sheet):
        continue
    active_groups = {
        clean(r.get("group_id")) for r in rows(group_sheet) if workbook_truthy(r.get("active"))
    }
    group_by_option = {}
    for r in rows(member_sheet):
        if not workbook_truthy(r.get("active")):
            continue
        group_id = clean(r.get("group_id"))
        option_id = clean(r.get("option_id"))
        if group_id in active_groups and option_id:
            group_by_option.setdefault(option_id, set()).add(group_id)
    for r in rows(rule_sheet):
        if clean(r.get("rule_type")) != "excludes" or clean(r.get("runtime_action")) != "replace":
            continue
        source_id = clean(r.get("source_id"))
        target_id = clean(r.get("target_id"))
        replace_excludes.append(
            {
                "model_key": model_key,
                "sheet": rule_sheet,
                "rule_id": clean(r.get("rule_id")),
                "source_id": source_id,
                "target_id": target_id,
                "shared_groups": sorted(
                    group_by_option.get(source_id, set()) & group_by_option.get(target_id, set())
                ),
            }
        )

# ── Approved one-source blocker clusters ─────────────────────────────
# A source option that blocks many targets is authored as one 'excludes_any'
# rule group, not as a spray of direct excludes rows. The RPO sets below are
# the approved clusters, passed in from the caller so the policy stays a named
# expectation rather than something inferred from the rows being checked.
ungrouped_blocker_excludes = []
for model_key, entry in sorted(model_registry.items()):
    source_rpos = BLOCKER_CLUSTER_RPOS.get(model_key)
    if not source_rpos:
        continue
    family_sheets = {item["family"]: item["sheet"] for item in entry}
    rule_sheet = family_sheets.get("rule_mapping")
    group_sheet = family_sheets.get("rule_groups")
    member_sheet = family_sheets.get("rule_group_members")
    option_sheet = family_sheets.get("options")
    if not (rule_sheet and group_sheet and member_sheet and option_sheet):
        continue

    option_by_id = {clean(r.get("option_id")): r for r in rows(option_sheet)}
    ids_by_rpo = {}
    for option in option_by_id.values():
        ids_by_rpo.setdefault(clean(option.get("rpo")), set()).add(clean(option.get("option_id")))

    grouped_pairs = set()
    members = rows(member_sheet)
    for group in rows(group_sheet):
        if not workbook_truthy(group.get("active")):
            continue
        if clean(group.get("group_type")) != "excludes_any":
            continue
        group_id = clean(group.get("group_id"))
        group_source = clean(group.get("source_id"))
        for member in members:
            if not workbook_truthy(member.get("active")):
                continue
            if clean(member.get("group_id")) == group_id:
                grouped_pairs.add((group_source, clean(member.get("target_id"))))

    for source_rpo in source_rpos:
        source_ids = ids_by_rpo.get(source_rpo, set())
        for rule in rows(rule_sheet):
            if clean(rule.get("rule_type")) != "excludes":
                continue
            if clean(rule.get("runtime_action")) == "replace":
                continue
            source_id = clean(rule.get("source_id"))
            target_id = clean(rule.get("target_id"))
            if source_id not in source_ids:
                continue
            if (source_id, target_id) in grouped_pairs:
                continue
            ungrouped_blocker_excludes.append(
                {
                    "model_key": model_key,
                    "sheet": rule_sheet,
                    "rule_id": clean(rule.get("rule_id")),
                    "source_rpo": source_rpo,
                    "source_id": source_id,
                    "target_rpo": clean(option_by_id.get(target_id, {}).get("rpo")),
                    "target_id": target_id,
                }
            )

payload = {
    "sheetnames": list(sheets.keys()),
    "retired_column_sightings": retired_column_sightings,
    "interior_headers": interior_headers,
    "replace_excludes": replace_excludes,
    "ungrouped_blocker_excludes": ungrouped_blocker_excludes,
    "registered_sheet_families": registered,
    "source_role_families": dict(reg.SOURCE_ROLE_FAMILIES),
    "promotion_artifact_types": list(reg.REGISTRY_PROMOTION_ARTIFACT_TYPES),
    "typed_columns_checked": typed_columns_checked,
    "type_violations": type_violations,
    "models": models,
    "model_source_registry": {
        model_key: {item["role"]: item["sheet"] for item in entry}
        for model_key, entry in model_registry.items()
    },
    "duplicate_group_excludes": duplicate_group_excludes,
    "headers_by_sheet": {
        sheet: sheets.get(sheet, {}).get("headers", []) for sheet in sorted(registered)
    },
}
print(json.dumps(payload))
`;

/**
 * One derived snapshot of registry-owned workbook shape. Single Python launch.
 *
 * @param {object} options
 * @param {Record<string, string[]>} options.blockerClusterRpos approved
 *   one-source blocker clusters, keyed by model_key.
 */
export function workbookRegistrySnapshot({ blockerClusterRpos = {} } = {}) {
  const program = SNAPSHOT_PROGRAM.replace(
    "__BLOCKER_CLUSTER_RPOS__",
    JSON.stringify(JSON.stringify(blockerClusterRpos)),
  );
  const output = execFileSync(".venv/bin/python", ["-c", program], {
    encoding: "utf8",
    env: { ...process.env, PYTHONPATH: "scripts" },
    maxBuffer: 64 * 1024 * 1024,
  });
  return JSON.parse(output);
}
