import React, { useState, useMemo } from "react";
import {
  Layers,
  Table2,
  PlusCircle,
  Pencil,
  Trash2,
  History,
  Code2,
  ChevronRight,
  X,
  Check,
  Download,
  Database,
  Settings2,
  ListOrdered,
} from "lucide-react";

/* ─────────────────────────────────────────────────────────────
   1. SHEET NORMALIZATION + SCHEMAS
   ───────────────────────────────────────────────────────────── */

const humanize = (raw) =>
  raw
    .replace(/^grandSport/, "grand_sport")
    .replace(/^LZ_/, "lz_")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .split(/[_\s]+/)
    .map((w) =>
      ["lpo", "ovs", "lz", "lt", "zr1", "zr1x", "z06"].includes(w.toLowerCase())
        ? w.toUpperCase()
        : w.charAt(0).toUpperCase() + w.slice(1),
    )
    .join(" ");

// Column schemas keyed by sheet category. key = primary key columns.
const SCHEMAS = {
  options: {
    key: ["option_id"],
    cols: [
      "option_id",
      "rpo",
      "price",
      "option_name",
      "description",
      "detail_raw",
      "section_id",
      "selectable",
      "display_order",
      "active",
      "display_behavior",
    ],
    enums: {
      selectable: ["True", "False"],
      active: ["True", "False"],
      display_behavior: [
        "",
        "default_selected",
        "hidden",
        "display_only",
        "auto_only",
      ],
    },
  },
  ovs: {
    key: ["option_id", "variant_id"],
    cols: ["option_id", "variant_id", "status"],
    enums: { status: ["standard", "available", "unavailable"] },
  },
  rule_mapping: {
    key: ["rule_id"],
    cols: [
      "rule_id",
      "source_id",
      "rule_type",
      "target_id",
      "target_type",
      "original_detail_raw",
      "source_type",
      "target_selection_mode",
      "source_selection_mode",
      "target_section",
      "source_section",
      "generation_action",
      "body_style_scope",
      "runtime_action",
      "disabled_reason",
      "normalization_status",
    ],
    enums: {
      rule_type: ["includes", "excludes", "requires"],
      body_style_scope: ["", "coupe", "convertible"],
      runtime_action: ["", "replace"],
      normalization_status: ["active", "omitted", "replaced", "preserved"],
    },
  },
  rule_groups: {
    key: ["group_id"],
    cols: [
      "group_id",
      "group_type",
      "source_id",
      "body_style_scope",
      "trim_level_scope",
      "variant_scope",
      "disabled_reason",
      "active",
      "notes",
    ],
    enums: {
      group_type: ["requires_any", "excludes_any"],
      active: ["True", "False"],
    },
  },
  rule_group_members: {
    key: ["group_id", "target_id"],
    cols: ["group_id", "target_id", "display_order", "active"],
    enums: { active: ["True", "False"] },
  },
  exclusive_groups: {
    key: ["group_id"],
    cols: ["group_id", "selection_mode", "active", "notes"],
    enums: {
      selection_mode: ["single_within_group", "required_single_within_group"],
      active: ["True", "False"],
    },
  },
  exclusive_members: {
    key: ["group_id", "option_id"],
    cols: ["group_id", "option_id", "display_order", "active"],
    enums: { active: ["True", "False"] },
  },
  price_rules: {
    key: ["price_rule_id"],
    cols: [
      "price_rule_id",
      "condition_option_id",
      "price_rule_type",
      "target_option_id",
      "price_value",
      "body_style_scope",
      "trim_level_scope",
      "notes",
    ],
    enums: { price_rule_type: ["override"] },
  },
  variant_overrides: {
    key: ["option_id", "variant_id"],
    cols: [
      "option_id",
      "variant_id",
      "selectable",
      "display_behavior",
      "section_id",
      "active",
      "note",
    ],
    enums: {
      selectable: ["", "True", "False"],
      active: ["True", "False"],
      display_behavior: ["", "default_selected", "display_only", "hidden"],
    },
  },
  color_overrides: {
    key: ["interior_id", "option_id"],
    cols: ["interior_id", "option_id", "rule_type", "adds_rpo"],
    enums: { rule_type: ["requires"] },
  },
  interiors: {
    key: ["interior_id"],
    cols: [
      "interior_id",
      "Interior Name",
      "Material",
      "Price",
      "Trim",
      "Seat",
      "Interior Code",
      "Suede",
      "Stitch",
      "Two Tone",
      "section_id",
      "active_for_stingray",
      "requires_r6x",
      "included_option_id",
    ],
    enums: {
      active_for_stingray: ["True", "False"],
      requires_r6x: ["True", "False"],
    },
  },
};

/* ─────────────────────────────────────────────────────────────
   2. FORM STRUCTURE — model activation sequence, steps, sections
   ───────────────────────────────────────────────────────────── */

const MODELS = [
  {
    key: "stingray",
    label: "Stingray",
    active: true,
    runtime: true,
    default: true,
    order: 1,
  },
  {
    key: "grand_sport",
    label: "Grand Sport",
    active: true,
    runtime: true,
    default: false,
    order: 2,
  },
  {
    key: "z06",
    label: "Z06",
    active: true,
    runtime: true,
    default: false,
    order: 3,
  },
  {
    key: "zr1",
    label: "ZR1",
    active: false,
    runtime: false,
    default: false,
    order: 4,
  },
  {
    key: "zr1x",
    label: "ZR1X",
    active: false,
    runtime: false,
    default: false,
    order: 5,
  },
];

const STEPS = [
  {
    key: "body_style",
    label: "Body Style",
    order: 1,
    sections: ["sec_context_body_style"],
  },
  {
    key: "trim_level",
    label: "Trim Level",
    order: 2,
    sections: ["sec_context_trim_level"],
  },
  {
    key: "paint",
    label: "Exterior Paint",
    order: 3,
    sections: ["sec_pain_001"],
  },
  {
    key: "exterior_appearance",
    label: "Exterior Appearance",
    order: 4,
    sections: ["sec_badg_001", "sec_engi_001", "sec_exte_001", "sec_roof_001"],
  },
  {
    key: "wheels",
    label: "Wheels & Brake Calipers",
    order: 5,
    sections: [
      "sec_cali_001",
      "sec_perf_support_001",
      "sec_whee_001",
      "sec_whee_002",
      "sec_z06_pkg_001",
    ],
  },
  {
    key: "packages_performance",
    label: "Performance & Aero",
    order: 6,
    sections: [
      "sec_exha_001",
      "sec_perf_001",
      "sec_perf_aero_001",
      "sec_perf_brake_001",
      "sec_perf_ground_001",
      "sec_perf_z52_001",
      "sec_spec_001",
      "sec_spoi_001",
      "sec_susp_001",
    ],
  },
  {
    key: "aero_exhaust_stripes_accessories",
    label: "Stripes",
    order: 7,
    sections: [
      "sec_gsce_001",
      "sec_gsha_001",
      "sec_hash_001",
      "sec_jake_001",
      "sec_stri_001",
    ],
  },
  { key: "seat", label: "Seats", order: 8, sections: ["sec_seat_002"] },
  {
    key: "base_interior",
    label: "Interior Color",
    order: 9,
    sections: [
      "sec_intc_001",
      "sec_intc_002",
      "sec_intc_003",
      "sec_lzint_001",
      "sec_lzint_002",
      "sec_lzint_003",
    ],
  },
  {
    key: "seat_belt",
    label: "Seat Belt",
    order: 10,
    sections: ["sec_seat_001"],
  },
  {
    key: "interior_trim",
    label: "Interior Trim",
    order: 11,
    sections: ["sec_colo_001", "sec_cust_002", "sec_inte_001", "sec_onst_001"],
  },
  {
    key: "accessories",
    label: "Accessories",
    order: 12,
    sections: ["sec_lpoe_001", "sec_lpoi_001", "sec_lpow_001"],
  },
  {
    key: "delivery",
    label: "Custom Delivery",
    order: 13,
    sections: ["sec_cust_001"],
  },
  { key: "summary", label: "Summary", order: 14, sections: [] },
];

const SECTION_NAMES = {
  sec_context_body_style: "Body Style",
  sec_context_trim_level: "Trim Level",
  sec_pain_001: "Paint",
  sec_badg_001: "Badges",
  sec_engi_001: "Engine Appearance",
  sec_exte_001: "Exterior Accents",
  sec_roof_001: "Roof",
  sec_cali_001: "Caliper Color",
  sec_perf_support_001: "Mechanical (Wheels)",
  sec_whee_001: "Wheel Accessory",
  sec_whee_002: "Wheels",
  sec_z06_pkg_001: "Z06 CF Wheel & Brake Packages",
  sec_exha_001: "Exhaust",
  sec_perf_001: "Mechanical",
  sec_perf_aero_001: "Aero Packages",
  sec_perf_brake_001: "Performance Brakes",
  sec_perf_ground_001: "Ground Effects",
  sec_perf_z52_001: "Z52 Packages",
  sec_spec_001: "Special Edition",
  sec_spoi_001: "Spoiler",
  sec_susp_001: "Suspension",
  sec_gsce_001: "GS Center Stripes",
  sec_gsha_001: "GS Hash Marks",
  sec_hash_001: "Hash Marks",
  sec_jake_001: "Jake Graphics Package",
  sec_stri_001: "Stripes",
  sec_seat_002: "Seats",
  sec_intc_001: "1LT Interior",
  sec_intc_002: "2LT Interior",
  sec_intc_003: "3LT Interior",
  sec_lzint_001: "1LZ Interior",
  sec_lzint_002: "2LZ Interior",
  sec_lzint_003: "3LZ Interior",
  sec_seat_001: "Seat Belt",
  sec_colo_001: "Color Override",
  sec_cust_002: "Custom Stitch",
  sec_inte_001: "Interior Trim",
  sec_onst_001: "OnStar",
  sec_lpoe_001: "LPO Exterior",
  sec_lpoi_001: "LPO Interior",
  sec_lpow_001: "LPO Wheels",
  sec_cust_001: "Custom Delivery",
};

/* ─────────────────────────────────────────────────────────────
   3. MODEL-SPECIFIC SHEET REGISTRY
   ───────────────────────────────────────────────────────────── */

const MODEL_SHEETS = {
  stingray: [
    { sheet: "stingray_options", schema: "options" },
    { sheet: "stingray_ovs", schema: "ovs" },
    { sheet: "rule_mapping", schema: "rule_mapping" },
    { sheet: "rule_groups", schema: "rule_groups" },
    { sheet: "rule_group_members", schema: "rule_group_members" },
    { sheet: "exclusive_groups", schema: "exclusive_groups" },
    { sheet: "exclusive_group_members", schema: "exclusive_members" },
    { sheet: "price_rules", schema: "price_rules" },
    { sheet: "variant_option_overrides", schema: "variant_overrides" },
    { sheet: "color_overrides", schema: "color_overrides" },
    { sheet: "lt_interiors", schema: "interiors" },
  ],
  grand_sport: [
    { sheet: "grandSport_options", schema: "options" },
    { sheet: "grandSport_ovs", schema: "ovs" },
    { sheet: "grandSport_rule_mapping", schema: "rule_mapping" },
    { sheet: "grandSport_rule_groups", schema: "rule_groups" },
    { sheet: "grandSport_rule_group_members", schema: "rule_group_members" },
    { sheet: "grandSport_exclusive_groups", schema: "exclusive_groups" },
    { sheet: "grandSport_exclusive_members", schema: "exclusive_members" },
    { sheet: "grandSport_price_rules", schema: "price_rules" },
    { sheet: "grandSport_variant_overrides", schema: "variant_overrides" },
    { sheet: "color_overrides", schema: "color_overrides" },
    { sheet: "lt_interiors", schema: "interiors" },
  ],
  z06: [
    { sheet: "z06_options", schema: "options" },
    { sheet: "z06_ovs", schema: "ovs" },
    { sheet: "z06_rule_mapping", schema: "rule_mapping" },
    { sheet: "z06_rule_groups", schema: "rule_groups" },
    { sheet: "z06_rule_group_members", schema: "rule_group_members" },
    { sheet: "z06_exclusive_groups", schema: "exclusive_groups" },
    { sheet: "z06_exclusive_members", schema: "exclusive_members" },
    { sheet: "z06_price_rules", schema: "price_rules" },
    { sheet: "z06_variant_overrides", schema: "variant_overrides" },
    { sheet: "color_overrides", schema: "color_overrides" },
    { sheet: "LZ_Interiors", schema: "interiors" },
  ],
  zr1: [
    { sheet: "zr1_options", schema: "options" },
    { sheet: "zr1_ovs", schema: "ovs" },
    { sheet: "zr1_rule_mapping", schema: "rule_mapping" },
    { sheet: "zr1_rule_groups", schema: "rule_groups" },
    { sheet: "zr1_rule_group_members", schema: "rule_group_members" },
    { sheet: "zr1_exclusive_groups", schema: "exclusive_groups" },
    { sheet: "zr1_exclusive_members", schema: "exclusive_members" },
    { sheet: "zr1_price_rules", schema: "price_rules" },
    { sheet: "zr1_variant_overrides", schema: "variant_overrides" },
    { sheet: "color_overrides", schema: "color_overrides" },
    { sheet: "LZ_Interiors", schema: "interiors" },
  ],
  zr1x: [
    { sheet: "zr1x_options", schema: "options" },
    { sheet: "zr1x_ovs", schema: "ovs" },
    { sheet: "zr1x_rule_mapping", schema: "rule_mapping" },
    { sheet: "zr1x_rule_groups", schema: "rule_groups" },
    { sheet: "zr1x_rule_group_members", schema: "rule_group_members" },
    { sheet: "zr1x_exclusive_groups", schema: "exclusive_groups" },
    { sheet: "zr1x_exclusive_members", schema: "exclusive_members" },
    { sheet: "zr1x_price_rules", schema: "price_rules" },
    { sheet: "zr1x_variant_overrides", schema: "variant_overrides" },
    { sheet: "color_overrides", schema: "color_overrides" },
    { sheet: "LZ_Interiors", schema: "interiors" },
  ],
};

// Seed rows for demonstration (a small sample mirroring real workbook content).
const SEED_ROWS = {
  stingray_options: [
    {
      option_id: "opt_z51_001",
      rpo: "Z51",
      price: "5395",
      option_name: "Z51 Performance Package",
      description: "",
      detail_raw: "",
      section_id: "sec_perf_001",
      selectable: "True",
      display_order: "30",
      active: "True",
      display_behavior: "",
    },
    {
      option_id: "opt_gkz_001",
      rpo: "GKZ",
      price: "0",
      option_name: "Torch Red",
      description: "Touch-Up Paint Number WA-9075",
      detail_raw: "",
      section_id: "sec_pain_001",
      selectable: "True",
      display_order: "10",
      active: "True",
      display_behavior: "",
    },
  ],
  stingray_ovs: [
    { option_id: "opt_z51_001", variant_id: "1lt_c07", status: "available" },
  ],
  price_rules: [
    {
      price_rule_id: "pr_z51tvs_001",
      condition_option_id: "opt_z51_001",
      price_rule_type: "override",
      target_option_id: "opt_tvs_001",
      price_value: "0",
      body_style_scope: "",
      trim_level_scope: "",
      notes: "Z51 selected sets TVS price to 0",
    },
  ],
  grandSport_options: [
    {
      option_id: "opt_fey_001",
      rpo: "FEY",
      price: "20695",
      option_name: "Z52 Track Performance Package",
      description: "",
      detail_raw: "",
      section_id: "sec_perf_z52_001",
      selectable: "True",
      display_order: "70",
      active: "True",
      display_behavior: "",
    },
  ],
  z06_options: [
    {
      option_id: "opt_z07_001",
      rpo: "Z07",
      price: "9500",
      option_name: "Z07 Performance Package",
      description: "",
      detail_raw: "",
      section_id: "sec_perf_z52_001",
      selectable: "True",
      display_order: "10",
      active: "True",
      display_behavior: "",
    },
  ],
};

/* ─────────────────────────────────────────────────────────────
   openpyxl SCRIPT GENERATOR
   ───────────────────────────────────────────────────────────── */

const pyStr = (v) =>
  `"${String(v ?? "")
    .replace(/\\/g, "\\\\")
    .replace(/"/g, '\\"')
    .replace(/\n/g, "\\n")}"`;

function buildOpenpyxlScript(ops) {
  const opsJson = ops
    .map((op) => {
      const base = `{"action": ${pyStr(op.action)}, "sheet": ${pyStr(op.sheet)}, "key": {${Object.entries(
        op.key || {},
      )
        .map(([k, v]) => `${pyStr(k)}: ${pyStr(v)}`)
        .join(", ")}}`;
      const row = op.row
        ? `, "row": {${Object.entries(op.row)
            .map(([k, v]) => `${pyStr(k)}: ${pyStr(v)}`)
            .join(", ")}}`
        : "";
      return `    ${base}${row}},`;
    })
    .join("\n");

  return `"""Auto-generated by Stingray Workbook Editor — applies ${ops.length} operation(s)."""
from openpyxl import load_workbook

WORKBOOK_PATH = "stingray_master.xlsx"

OPERATIONS = [
${opsJson}
]

def header_map(ws):
    return {str(c.value): i + 1 for i, c in enumerate(ws[1]) if c.value is not None}

def find_row(ws, headers, key):
    cols = {k: headers[k] for k in key}
    for r in range(2, ws.max_row + 1):
        if all(str(ws.cell(row=r, column=c).value or "") == str(v) for (k, v), c
               in zip(key.items(), cols.values())):
            return r
    return None

def apply(op, wb):
    ws = wb[op["sheet"]]
    headers = header_map(ws)
    if op["action"] == "add":
        ws.append([op["row"].get(h, "") for h in headers])
        print(f"  + added row in {op['sheet']}: {op['key']}")
    elif op["action"] == "update":
        r = find_row(ws, headers, op["key"])
        if r is None:
            print(f"  ! row not found in {op['sheet']}: {op['key']}"); return
        for col, val in op["row"].items():
            if col in headers:
                ws.cell(row=r, column=headers[col], value=val)
        print(f"  ~ updated row {r} in {op['sheet']}: {op['key']}")
    elif op["action"] == "delete":
        r = find_row(ws, headers, op["key"])
        if r is None:
            print(f"  ! row not found in {op['sheet']}: {op['key']}"); return
        ws.delete_rows(r)
        print(f"  - deleted row {r} in {op['sheet']}: {op['key']}")

def main():
    wb = load_workbook(WORKBOOK_PATH)
    for op in OPERATIONS:
        apply(op, wb)
    wb.save(WORKBOOK_PATH)
    print(f"Saved {len(OPERATIONS)} change(s) to {WORKBOOK_PATH}")

if __name__ == "__main__":
    main()
`;
}

/* ─────────────────────────────────────────────────────────────
   COMPONENT
   ───────────────────────────────────────────────────────────── */

export default function StingrayWorkbookEditor() {
  const [tab, setTab] = useState("structure");
  const [modelKey, setModelKey] = useState("stingray");
  const [sheetIdx, setSheetIdx] = useState(0);
  const [rowsBySheet, setRowsBySheet] = useState(() => ({ ...SEED_ROWS }));
  const [editing, setEditing] = useState(null); // {mode:'add'|'edit', index?, draft}
  const [pendingOps, setPendingOps] = useState([]);
  const [audit, setAudit] = useState([]);
  const [showScript, setShowScript] = useState(false);

  const model = MODELS.find((m) => m.key === modelKey);
  const sheets = MODEL_SHEETS[modelKey];
  const sheetEntry = sheets[Math.min(sheetIdx, sheets.length - 1)];
  const schema = SCHEMAS[sheetEntry.schema];
  const rows = rowsBySheet[sheetEntry.sheet] || [];

  const rowKey = (row) =>
    Object.fromEntries(schema.key.map((k) => [k, row[k] || ""]));
  const keyLabel = (row) =>
    schema.key
      .map((k) => row[k])
      .filter(Boolean)
      .join(" / ");

  const log = (action, sheet, key, detail) =>
    setAudit((a) => [
      { ts: new Date().toLocaleTimeString(), action, sheet, key, detail },
      ...a,
    ]);

  const queueOp = (op) => setPendingOps((q) => [...q, op]);

  const setRows = (next) =>
    setRowsBySheet((m) => ({ ...m, [sheetEntry.sheet]: next }));

  const startAdd = () =>
    setEditing({
      mode: "add",
      draft: Object.fromEntries(schema.cols.map((c) => [c, ""])),
    });

  const startEdit = (i) =>
    setEditing({ mode: "edit", index: i, draft: { ...rows[i] } });

  const saveDraft = () => {
    const draft = editing.draft;
    const missing = schema.key.filter((k) => !String(draft[k] || "").trim());
    if (missing.length) {
      alert(`Required key field(s) missing: ${missing.join(", ")}`);
      return;
    }
    if (editing.mode === "add") {
      setRows([...rows, draft]);
      queueOp({
        action: "add",
        sheet: sheetEntry.sheet,
        key: rowKey(draft),
        row: draft,
      });
      log(
        "ADD",
        sheetEntry.sheet,
        keyLabel(draft),
        `${schema.cols.length} fields`,
      );
    } else {
      const next = rows.slice();
      next[editing.index] = draft;
      setRows(next);
      queueOp({
        action: "update",
        sheet: sheetEntry.sheet,
        key: rowKey(draft),
        row: draft,
      });
      log("UPDATE", sheetEntry.sheet, keyLabel(draft), "row updated");
    }
    setEditing(null);
  };

  const removeRow = (i) => {
    const row = rows[i];
    if (!window.confirm) {
      // sandbox may block confirm; proceed
    }
    setRows(rows.filter((_, j) => j !== i));
    queueOp({ action: "delete", sheet: sheetEntry.sheet, key: rowKey(row) });
    log("DELETE", sheetEntry.sheet, keyLabel(row), "row removed");
  };

  const script = useMemo(() => buildOpenpyxlScript(pendingOps), [pendingOps]);

  const downloadScript = () => {
    const blob = new Blob([script], { type: "text/x-python" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "apply_workbook_changes.py";
    a.click();
    URL.revokeObjectURL(url);
  };

  const previewCols = schema.cols.slice(0, 6);

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans">
      {/* Header */}
      <header className="border-b border-slate-800 bg-slate-900 px-6 py-4 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <Database className="text-amber-400" size={22} />
          <div>
            <h1 className="text-lg font-bold">
              Stingray Master Workbook Editor
            </h1>
            <p className="text-xs text-slate-400">
              stingray_master.xlsx · openpyxl write pipeline
            </p>
          </div>
        </div>
        <nav className="flex gap-1 bg-slate-800 rounded-lg p-1">
          {[
            { id: "structure", label: "Form Structure", icon: ListOrdered },
            { id: "operations", label: "Model Operations", icon: Settings2 },
            {
              id: "audit",
              label: `Audit & Export (${pendingOps.length})`,
              icon: History,
            },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-1 px-3 py-2 rounded-md text-sm font-medium transition ${
                tab === id
                  ? "bg-amber-500 text-slate-900"
                  : "text-slate-300 hover:bg-slate-700"
              }`}
            >
              <Icon size={15} /> {label}
            </button>
          ))}
        </nav>
      </header>

      <main className="p-6 max-w-6xl mx-auto">
        {/* ── TAB 1: FORM STRUCTURE ── */}
        {tab === "structure" && (
          <div className="space-y-6">
            <section>
              <h2 className="text-sm font-bold uppercase tracking-wide text-amber-400 mb-3 flex items-center gap-2">
                <Layers size={15} /> Model Activation Sequence
              </h2>
              <div className="grid gap-3 grid-cols-1 sm:grid-cols-3 lg:grid-cols-5">
                {MODELS.map((m) => (
                  <div
                    key={m.key}
                    className={`rounded-xl border p-4 ${
                      m.active
                        ? "border-emerald-700 bg-emerald-950"
                        : "border-slate-800 bg-slate-900 opacity-70"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold">{m.label}</span>
                      <span className="text-xs text-slate-400">#{m.order}</span>
                    </div>
                    <div className="mt-2 flex flex-wrap gap-1 text-xs">
                      <span
                        className={`px-2 py-1 rounded-full ${m.active ? "bg-emerald-800 text-emerald-200" : "bg-slate-800 text-slate-400"}`}
                      >
                        {m.active ? "Active" : "Scaffold"}
                      </span>
                      {m.runtime && (
                        <span className="px-2 py-1 rounded-full bg-sky-900 text-sky-200">
                          Runtime
                        </span>
                      )}
                      {m.default && (
                        <span className="px-2 py-1 rounded-full bg-amber-900 text-amber-200">
                          Default
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section>
              <h2 className="text-sm font-bold uppercase tracking-wide text-amber-400 mb-3 flex items-center gap-2">
                <ChevronRight size={15} /> Runtime Steps & Interface Sections
              </h2>
              <div className="rounded-xl border border-slate-800 overflow-hidden">
                {STEPS.map((s, i) => (
                  <div
                    key={s.key}
                    className={`flex flex-wrap items-start gap-3 px-4 py-3 ${i % 2 ? "bg-slate-900" : "bg-slate-950"}`}
                  >
                    <span className="w-8 h-8 shrink-0 flex items-center justify-center rounded-full bg-slate-800 text-amber-400 text-sm font-bold">
                      {s.order}
                    </span>
                    <div className="min-w-0">
                      <div className="font-semibold text-sm">{s.label}</div>
                      <div className="text-xs text-slate-500 font-mono">
                        {s.key}
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-1 ml-auto max-w-md">
                      {s.sections.length === 0 ? (
                        <span className="text-xs text-slate-500 italic">
                          no sections (computed)
                        </span>
                      ) : (
                        s.sections.map((sec) => (
                          <span
                            key={sec}
                            className="text-xs px-2 py-1 rounded bg-slate-800 text-slate-300"
                            title={sec}
                          >
                            {SECTION_NAMES[sec] || sec}
                          </span>
                        ))
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}

        {/* ── TAB 2: MODEL OPERATIONS ── */}
        {tab === "operations" && (
          <div className="space-y-4">
            {/* Model + sheet pickers */}
            <div className="flex flex-wrap gap-2">
              {MODELS.map((m) => (
                <button
                  key={m.key}
                  onClick={() => {
                    setModelKey(m.key);
                    setSheetIdx(0);
                    setEditing(null);
                  }}
                  className={`px-3 py-2 rounded-lg text-sm font-semibold border transition ${
                    modelKey === m.key
                      ? "bg-amber-500 text-slate-900 border-amber-500"
                      : m.active
                        ? "bg-slate-900 border-slate-700 hover:border-amber-500"
                        : "bg-slate-900 border-slate-800 text-slate-500"
                  }`}
                >
                  {m.label}
                  {!m.active && " ·scaffold"}
                </button>
              ))}
            </div>

            <div className="flex flex-wrap gap-2">
              {sheets.map((s, i) => (
                <button
                  key={s.sheet}
                  onClick={() => {
                    setSheetIdx(i);
                    setEditing(null);
                  }}
                  className={`px-3 py-1 rounded-full text-xs font-medium border transition ${
                    i === sheetIdx
                      ? "bg-sky-600 border-sky-600 text-white"
                      : "bg-slate-900 border-slate-700 text-slate-300 hover:border-sky-500"
                  }`}
                  title={s.sheet}
                >
                  {humanize(s.sheet)}
                </button>
              ))}
            </div>

            {/* Sheet panel */}
            <div className="rounded-xl border border-slate-800 bg-slate-900">
              <div className="px-4 py-3 border-b border-slate-800 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <Table2 size={16} className="text-sky-400" />
                  <span className="font-bold">
                    {humanize(sheetEntry.sheet)}
                  </span>
                  <span className="text-xs font-mono text-slate-500">
                    ({sheetEntry.sheet})
                  </span>
                  <span className="text-xs px-2 py-1 rounded bg-slate-800 text-slate-400">
                    key: {schema.key.join(" + ")}
                  </span>
                </div>
                <button
                  onClick={startAdd}
                  className="flex items-center gap-1 px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-sm font-semibold"
                >
                  <PlusCircle size={15} /> Add Row
                </button>
              </div>

              {/* Row table */}
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs uppercase text-slate-400 border-b border-slate-800">
                      {previewCols.map((c) => (
                        <th key={c} className="px-3 py-2 whitespace-nowrap">
                          {c}
                        </th>
                      ))}
                      <th className="px-3 py-2 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.length === 0 && (
                      <tr>
                        <td
                          colSpan={previewCols.length + 1}
                          className="px-4 py-6 text-center text-slate-500 italic"
                        >
                          No rows loaded for this sheet — add one to queue an
                          openpyxl write.
                        </td>
                      </tr>
                    )}
                    {rows.map((r, i) => (
                      <tr
                        key={i}
                        className="border-b border-slate-800 hover:bg-slate-800"
                      >
                        {previewCols.map((c) => (
                          <td
                            key={c}
                            className="px-3 py-2 max-w-xs truncate text-slate-300"
                            title={r[c]}
                          >
                            {r[c] || <span className="text-slate-600">—</span>}
                          </td>
                        ))}
                        <td className="px-3 py-2 text-right whitespace-nowrap">
                          <button
                            onClick={() => startEdit(i)}
                            className="p-1 rounded hover:bg-slate-700 text-sky-400"
                            title="Edit"
                          >
                            <Pencil size={15} />
                          </button>
                          <button
                            onClick={() => removeRow(i)}
                            className="p-1 rounded hover:bg-slate-700 text-rose-400 ml-1"
                            title="Delete"
                          >
                            <Trash2 size={15} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Editor form */}
            {editing && (
              <div className="rounded-xl border border-amber-700 bg-slate-900 p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold text-amber-400">
                    {editing.mode === "add" ? "Add Row" : "Edit Row"} —{" "}
                    {humanize(sheetEntry.sheet)}
                  </h3>
                  <button
                    onClick={() => setEditing(null)}
                    className="p-1 rounded hover:bg-slate-800"
                  >
                    <X size={16} />
                  </button>
                </div>
                <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3">
                  {schema.cols.map((col) => {
                    const isKey = schema.key.includes(col);
                    const enumVals = schema.enums?.[col];
                    return (
                      <label key={col} className="text-xs">
                        <span
                          className={`block mb-1 font-medium ${isKey ? "text-amber-300" : "text-slate-400"}`}
                        >
                          {col}
                          {isKey && " *"}
                        </span>
                        {enumVals ? (
                          <select
                            value={editing.draft[col] || ""}
                            onChange={(e) =>
                              setEditing((ed) => ({
                                ...ed,
                                draft: { ...ed.draft, [col]: e.target.value },
                              }))
                            }
                            className="w-full px-2 py-2 rounded bg-slate-800 border border-slate-700 text-sm focus:border-amber-500 outline-none"
                          >
                            {enumVals.map((v) => (
                              <option key={v} value={v}>
                                {v === "" ? "(blank)" : v}
                              </option>
                            ))}
                          </select>
                        ) : (
                          <input
                            value={editing.draft[col] || ""}
                            onChange={(e) =>
                              setEditing((ed) => ({
                                ...ed,
                                draft: { ...ed.draft, [col]: e.target.value },
                              }))
                            }
                            disabled={isKey && editing.mode === "edit"}
                            className="w-full px-2 py-2 rounded bg-slate-800 border border-slate-700 text-sm focus:border-amber-500 outline-none disabled:opacity-50"
                            placeholder={isKey ? "required key" : ""}
                          />
                        )}
                      </label>
                    );
                  })}
                </div>
                <div className="mt-4 flex gap-2">
                  <button
                    onClick={saveDraft}
                    className="flex items-center gap-1 px-4 py-2 rounded-lg bg-amber-500 text-slate-900 font-semibold hover:bg-amber-400"
                  >
                    <Check size={16} />{" "}
                    {editing.mode === "add"
                      ? "Add & Queue Write"
                      : "Save & Queue Write"}
                  </button>
                  <button
                    onClick={() => setEditing(null)}
                    className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── TAB 3: AUDIT & EXPORT ── */}
        {tab === "audit" && (
          <div className="space-y-5">
            <section className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                <h2 className="font-bold flex items-center gap-2 text-amber-400">
                  <Code2 size={16} /> Pending openpyxl Operations (
                  {pendingOps.length})
                </h2>
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowScript((s) => !s)}
                    className="px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-sm"
                  >
                    {showScript ? "Hide Script" : "Preview Script"}
                  </button>
                  <button
                    onClick={downloadScript}
                    disabled={pendingOps.length === 0}
                    className="flex items-center gap-1 px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-sm font-semibold disabled:opacity-40"
                  >
                    <Download size={14} /> Download .py
                  </button>
                  <button
                    onClick={() => setPendingOps([])}
                    disabled={pendingOps.length === 0}
                    className="px-3 py-1 rounded-lg bg-rose-900 hover:bg-rose-800 text-sm disabled:opacity-40"
                  >
                    Clear Queue
                  </button>
                </div>
              </div>
              {pendingOps.length === 0 ? (
                <p className="text-sm text-slate-500 italic">
                  No queued writes. Edits made in Model Operations appear here.
                </p>
              ) : (
                <ul className="space-y-1 text-sm">
                  {pendingOps.map((op, i) => (
                    <li
                      key={i}
                      className="flex flex-wrap items-center gap-2 px-3 py-2 rounded bg-slate-800"
                    >
                      <span
                        className={`text-xs font-bold px-2 py-1 rounded ${
                          op.action === "add"
                            ? "bg-emerald-900 text-emerald-300"
                            : op.action === "update"
                              ? "bg-sky-900 text-sky-300"
                              : "bg-rose-900 text-rose-300"
                        }`}
                      >
                        {op.action.toUpperCase()}
                      </span>
                      <span className="font-mono text-xs text-slate-300">
                        {op.sheet}
                      </span>
                      <span className="text-xs text-slate-400">
                        {Object.entries(op.key)
                          .map(([k, v]) => `${k}=${v}`)
                          .join(", ")}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
              {showScript && (
                <pre className="mt-4 p-4 rounded-lg bg-slate-950 border border-slate-800 text-xs text-emerald-200 overflow-x-auto max-h-96 overflow-y-auto whitespace-pre">
                  {script}
                </pre>
              )}
            </section>

            <section className="rounded-xl border border-slate-800 bg-slate-900 p-4">
              <h2 className="font-bold flex items-center gap-2 text-amber-400 mb-3">
                <History size={16} /> Audit Trail
              </h2>
              {audit.length === 0 ? (
                <p className="text-sm text-slate-500 italic">
                  No changes recorded this session.
                </p>
              ) : (
                <ul className="space-y-1 text-sm max-h-80 overflow-y-auto">
                  {audit.map((e, i) => (
                    <li
                      key={i}
                      className="flex flex-wrap items-center gap-2 px-3 py-2 rounded bg-slate-800"
                    >
                      <span className="text-xs text-slate-500 font-mono">
                        {e.ts}
                      </span>
                      <span
                        className={`text-xs font-bold ${
                          e.action === "ADD"
                            ? "text-emerald-400"
                            : e.action === "UPDATE"
                              ? "text-sky-400"
                              : "text-rose-400"
                        }`}
                      >
                        {e.action}
                      </span>
                      <span className="font-mono text-xs text-slate-300">
                        {e.sheet}
                      </span>
                      <span className="text-xs text-slate-400">{e.key}</span>
                      <span className="text-xs text-slate-500 ml-auto">
                        {e.detail}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>
        )}
      </main>
    </div>
  );
}
