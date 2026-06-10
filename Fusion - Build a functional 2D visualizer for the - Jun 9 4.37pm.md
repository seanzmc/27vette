# 2027 Corvette 2D Visualizer — Architecture & Implementation

## 0. Pipeline Overview & Ground Rules

The architecture is a strict two-stage pipeline that keeps `stingray_master.xlsx` canonical:

```
stingray_master.xlsx ──(Python parser, offline)──► manifest.json + per-model JSON bundles ──► React runtime
```

The runtime app **never** reads the workbook directly. All pricing, rules, availability, sections, and visual layer mappings are workbook-sourced data interpreted by a generic engine — nothing is hardcoded.

**One honest caveat up front:** the parser below is written against the documented sheet contract (model-specific schema tables, `form_*` form sheets, high-level cross-model sheets). Until it is run against the actual binary `.xlsx`, the generated JSON cannot be emitted here. To de-risk this, the repo ships a **mock-workbook generator** that produces a schema-conformant `.xlsx`, and the parser + engine test harness runs against it in CI — so the entire pipeline is validated end-to-end before the real workbook ever lands. Swap in the real file and re-run; nothing else changes.

**Stack** (deliberately more capable than vanilla JS):

| Layer | Choice | Why |
|---|---|---|
| Parser | Python 3.11 + **openpyxl** (read-only, data-only) | Streaming reads of large OVS sheets; precise control over header normalization and coercion. Pandas is fine for exploration, but a raw `df.fillna('').to_dict()` dump ships untyped, unvalidated rows to the frontend — we want a *transforming* parser, not a sheet copier. |
| Frontend | **Vite + React 18 + TypeScript** | Component model + compile-time data contracts via `--strict` types. |
| State | **Zustand** | Predictable real-time configurator state without Redux ceremony. |
| PDF | **@react-pdf/renderer** (data-driven) + optional html2canvas snapshot | See §8 for the reasoning. |
| Tests | Vitest (engine), Playwright (UI), parser self-checks | See §9. |

---

## 1. Excel→JSON Parser

### 1.1 Sheet taxonomy and canonical-source policy

The workbook has three classes of sheets, and the parser treats them differently:

1. **Cross-model / high-level sheets** — `model_master`, `model_registry_promotion`, `variant_master`, `section_master`, `runtime_steps`, `asset_map`, `PriceRef`, `color_overrides`, `order_summary_sections`, `standard_equipment_groups`.
2. **Model-specific schema tables** — consistent per-model sets: `{model}_options`, `{model}_ovs`, `{model}_rule_mapping`, `{model}_price_rules`, `{model}_rule_groups` (+ members), `{model}_exclusive_groups` (+ members), `{model}_variant_overrides`, interiors (`lt_interiors` / `LZ_Interiors`).
3. **Generated/derivative sheets** — `form_*`, `archive_*`, `*_raw`. These are **never canonical sources**. The parser reads them only to emit row-count/header diagnostics in `parser_report.json`.

**Promotion and the Z06 transition-state conflict:** runtime model membership is governed by `model_registry_promotion` — not `model_workbook_sources`, which can carry transition-state metadata (e.g., Z06 promoted in the registry but still flagged inactive in the source map). The parser resolves this deliberately: an explicit, version-controlled model→sheet registry is authoritative, with the promotion sheet as the runtime gate and `model_master` active rows as fallback. **ZR1/ZR1X** are carried as unpromoted scaffolds in the same registry, emitted only behind `--include-unpromoted` so the data contract is ready the day they flip on.

```python
@dataclass(frozen=True)
class ModelSheets:
    options: str
    ovs: str
    direct_rules: str
    price_rules: str
    rule_groups: str | None
    rule_group_members: str | None
    exclusive_groups: str | None
    exclusive_members: str | None
    variant_overrides: str | None
    interiors: str | None

MODEL_SHEETS = {
    "stingray":   ModelSheets("stingray_options", "stingray_ovs", "rule_mapping",
                              "price_rules", "rule_groups", "rule_group_members",
                              "exclusive_groups", "exclusive_group_members",
                              "variant_option_overrides", "lt_interiors"),
    "grandSport": ModelSheets("grandSport_options", "grandSport_ovs", "grandSport_rule_mapping",
                              "grandSport_price_rules", "grandSport_rule_groups",
                              "grandSport_rule_group_members", "grandSport_exclusive_groups",
                              "grandSport_exclusive_members", "grandSport_variant_overrides",
                              "lt_interiors"),
    "z06":        ModelSheets("z06_options", "z06_ovs", "z06_rule_mapping",
                              "z06_price_rules", "z06_rule_groups", "z06_rule_group_members",
                              "z06_exclusive_groups", "z06_exclusive_members",
                              "z06_variant_overrides", "LZ_Interiors"),
    # Unpromoted scaffolds, emitted only with --include-unpromoted:
    "zr1":  ModelSheets("zr1_options", "zr1_ovs", "zr1_rule_mapping", "zr1_price_rules",
                        None, None, None, None, None, "LZ_Interiors"),
    "zr1x": ModelSheets("zr1x_options", "zr1x_ovs", "zr1x_rule_mapping", "zr1x_price_rules",
                        None, None, None, None, None, "LZ_Interiors"),
}
```

### 1.2 Robustness primitives: aliases, coercion, wildcards

Real workbooks drift. Every header is snake-cased and resolved through an alias table; every value is coerced; `*`/`all` wildcards are preserved as match-everything tokens:

```python
ALIASES = {
    "option_id":  ["option_id", "option_key", "id", "choice_id"],
    "rule_type":  ["rule_type", "type", "action", "runtime_action", "relationship"],
    "price":      ["price", "msrp", "amount"],
    "status":     ["status", "availability", "ovs_status"],
    "layer_order":["layer_order", "z_index", "z", "stack_order"],
    # ... full table covers model_key, variant_id, body_style, trim, rpo,
    #     asset_path, layer_key, display_order, message, severity, etc.
}

def as_money(value, default=0.0):
    """'$69,995' -> 69995.0; 'NC'/'Included'/'N/C'/'Standard'/'--' -> 0.0;
       '(500)' -> -500.0; numerics pass through."""
    ...

def as_bool(value, default=False):
    """TRUE/'yes'/1/'active'/'promoted' -> True; FALSE/'no'/0/'inactive' -> False."""
    ...

def normalize_status(value):
    """S/std/standard/included -> 'standard'; A/optional/LPO -> 'available';
       NA/not_available/excluded -> 'unavailable'."""
    ...

def normalize_rule_type(value):
    """include(s)/auto_include -> 'includes'; require(s)/required -> 'requires';
       exclude(s)/incompatible -> 'excludes'; replace(s) -> 'replace';
       requires_any/one_of_required -> 'requires_any'; excludes_any -> 'excludes_any';
       default/default_select -> 'default'."""
    ...
```

A `pick(row, canonical_key)` helper resolves through the alias chain, so a workbook revision renaming `msrp` → `price` doesn't break the build.

### 1.3 OVS compaction

The per-model OVS matrices run **1.4k–1.7k rows each**. Shipping them raw to the browser is wasteful and pushes interpretation downstream. The parser compacts each matrix to:

```json
{
  "ovsDefaultStatus": "available",
  "availabilityExceptions": {
    "1YC07": { "Z51": {"status": "standard", "standard": true},
               "FE7": {"status": "unavailable"} }
  }
}
```

i.e., a per-model **default status + sparse exceptions** keyed by variant → option. The runtime looks up exceptions first and falls back to the default — same semantics, a fraction of the payload, and a single normalized `Availability` shape (`status`, `selectable`, `visible`, `standard`, `defaultSelected`, `priceOverride?`).

Model-specific `{model}_variant_overrides` rows are merged on top of the OVS matrix at parse time (matching by variant id / body style / trim with wildcard tolerance), so the runtime sees one resolved availability surface.

### 1.4 Referential-integrity validation

Before emitting JSON, the parser validates:

- every rule `source_option_id` / `target_option_id` / group member resolves to a known option (by id or RPO index);
- every OVS row references a known option and variant;
- no duplicate option ids within a model;
- every `asset_map` `asset_path` **exists on disk** (asset-pipeline check — catches typos before the browser 404s);
- price rules reference resolvable targets.

Findings are written to `parser_report.json` and embedded as `validation[]` in each bundle; **errors produce a non-zero exit code**, making the parser CI-gateable.

### 1.5 Core parser skeleton

```python
class WorkbookReader:
    def __init__(self, path: Path):
        self.wb = load_workbook(path, read_only=True, data_only=True)

    def read_sheet(self, name: str) -> list[dict]:
        if name not in self.wb.sheetnames:
            return []
        ws = self.wb[name]
        rows = ws.iter_rows(values_only=True)
        header = None
        for raw in rows:                      # first non-empty row = header
            if any(clean(v) is not None for v in raw):
                header = make_unique([snake(clean(v)) or f"col_{i+1}"
                                      for i, v in enumerate(raw)])
                break
        if not header:
            return []
        out = []
        for raw in rows:
            if not any(clean(v) is not None for v in raw):
                continue
            out.append({h: clean(raw[i] if i < len(raw) else None)
                        for i, h in enumerate(header)})
        return out


def build_model(sheets, registry_row, model_master, report):
    key = registry_row["key"]
    ss = MODEL_SHEETS[key]
    variants  = parse_variants(sheets, key)               # variant_master, scoped
    sections  = parse_sections(sheets, key)               # section_master + presentation
    steps     = parse_steps(sheets, key, sections)        # runtime_steps, with fallback (§1.6)
    options   = parse_options(sheets.get(ss.options, []))
    interiors = parse_interiors(sheets, key, ss.interiors)  # + model_interior_scope,
                                                            #   interior_components
    availability = compact_ovs(
        parse_availability(sheets.get(ss.ovs, []),
                           sheets.get(ss.variant_overrides or "", []),
                           variants, options))
    inject_interiors(interiors, options, availability, variants)

    rules  = parse_direct_rules(sheets.get(ss.direct_rules, []), options, ss.direct_rules)
    rules += parse_group_rules(sheets.get(ss.rule_groups or "", []),
                               sheets.get(ss.rule_group_members or "", []), options)
    rules += parse_color_override_rules(sheets, key, options)   # interior↔color compat
    rules  = apply_runtime_exceptions(rules, sheets, key)       # runtime_rule_exceptions

    return {
        "key": key, "label": pick(model_master.get(key, {}), "label") or key,
        "year": 2027, "isDefault": registry_row["isDefault"],
        "variants": variants, "steps": steps, "sections": sections,
        "options": options, "availability": availability,
        "rules": rules,
        "exclusiveGroups": parse_exclusive_groups(
            sheets.get(ss.exclusive_groups or "", []),
            sheets.get(ss.exclusive_members or "", []), options),
        "priceRules": parse_price_rules(sheets.get(ss.price_rules, []), options),
        "defaultSelectionRules": parse_default_rules(sheets, key, options),
        "interiors": interiors,
        "assets": parse_assets(sheets, key),                # asset_map, model-filtered
        "standardEquipmentGroups": parse_standard_equipment(sheets, key),
        "validation": validate_refs(options, rules, availability, report),
    }
```

The CLI emits `manifest.json` (model registry, cross-model `PriceRef`, summary-layout sheets `order_summary_sections` / `step_order_summary_map`, schema version) plus **one self-contained bundle per model** — preferable to a single monolithic JSON because each model can be lazy-loaded and re-parsed independently.

```bash
pip install openpyxl
python parser/parse_workbook.py stingray_master.xlsx --out app/public/data
# exits non-zero on referential-integrity errors; writes parser_report.json
```

### 1.6 Defensive fallbacks

- If `runtime_steps` lacks rows for a model, steps are **derived from sections'** `step_key`/`display_order`.
- If `model_registry_promotion` is empty/missing, fall back to active `model_master` rows, then a last-resort default of the three promoted models.
- Rules and assets resolve targets through an RPO index when option ids don't match directly.

---

## 2. Data Schema Design (`types/schema.ts`)

The TypeScript types are the data contract; the frontend compiles under `tsc --strict` against them, and the parser embeds `schemaVersion` so the app can refuse mismatched data (§9).

```ts
export interface Manifest {
  schemaVersion: "2027-corvette-config-v1";
  generatedAt: string;
  workbook: string;
  models: ModelRegistryEntry[];        // key, label, isDefault, bundlePath, displayOrder
  priceRef: PriceRefEntry[];           // cross-model trim normalization
  summaryLayout: SummarySection[];     // order_summary_sections / step_order_summary_map
  warnings: string[];
}

export interface ModelBundle {
  key: string; label: string; year: number; isDefault: boolean;
  variants: Variant[];                 // id, trim, bodyStyle, displayName, basePrice, displayOrder
  steps: RuntimeStep[];
  sections: Section[];                 // id, label, selectionMode ('single'|'multi'), required, stepKey
  options: Record<string, ConfigOption>;
  ovsDefaultStatus: AvailabilityStatus;
  availabilityExceptions: Record<string /*variantId*/,
                                 Record<string /*optionId*/, Availability>>;
  rules: RuntimeRule[];
  exclusiveGroups: ExclusiveGroup[];   // memberIds, minSelections, maxSelections, scope
  priceRules: PriceRule[];             // action: set_price|delta|included|waive|base_price_override
  defaultSelectionRules: DefaultSelectionRule[];
  interiors: Record<string, Interior>;
  assets: AssetRef[];
  validation: ValidationFinding[];
}

export type RuleType =
  | "includes" | "requires" | "excludes" | "replace"
  | "default" | "requires_any" | "excludes_any";

export interface RuntimeRule {
  id: string;
  type: RuleType;
  sourceId?: string;
  targetId?: string;
  memberIds?: string[];                       // group rules
  runtimeAction?: "auto_add" | "block";       // workbook-specified UX policy (§4.4)
  scope?: RuleScope;                          // modelKeys/variantIds/bodyStyles/trims, '*' aware
  message?: string;                           // workbook customer copy
  severity?: "info" | "warning" | "error";
  sourceSheet?: string;                       // provenance for debugging
}

export interface AssetRef {
  id: string; role: "base" | "layer" | "option_card" | "model_card";
  src: string; alt?: string;
  layerKey?: string;        // shadow|body|roof|wheels|calipers|stripes|badges
  layerOrder: number;
  optionId?: string; rpo?: string;
  variantId?: string; bodyStyle?: string; trim?: string;   // '*' wildcards allowed
}
```

The engine's output type makes the derived-state architecture explicit:

```ts
export interface EvaluationResult {
  selectedIds: string[];
  autoSelected: Record<string, string>;   // optionId -> human-readable reason
  locked: Record<string, string>;         // standard/required equipment, with reason
  disabledReasons: Record<string, string[]>;
  violations: Violation[];
  quote: Quote;                           // lines[] + subtotal
}
```

---

## 3. State Management — Zustand with Pure Derivation

The architectural rule: **the user's selection list is the only mutable state.** Availability, pricing, conflicts, the layer stack, and the PDF payload are all *pure derivations* of `(model, variantId, userSelectedIds)`. This makes invalid UI states structurally unrepresentable — the UI can't display a price that disagrees with the engine because there is no second copy to drift.

```ts
export const useConfiguratorStore = create<ConfiguratorState>((set, get) => ({
  data: null, modelKey: "", variantId: "", userSelectedIds: [],
  evaluation: null, lastMessage: undefined,

  loadData: (data) => { /* pick default model/variant, seed defaults, recompute */ },

  setVariant: (variantId) => {
    const { data, modelKey, userSelectedIds } = get();
    // Carry-forward policy: keep selections still legal on the new variant,
    // drop the rest, re-seed workbook defaults for emptied required sections.
    const carried = carryForward(data!.models[modelKey], variantId, userSelectedIds);
    set({ variantId, userSelectedIds: carried,
          evaluation: evaluateConfiguration(data!.models[modelKey], variantId, carried) });
  },

  toggleOption: (optionId) => {
    const { data, modelKey, variantId, userSelectedIds, evaluation } = get();
    const blocked = evaluation!.disabledReasons[optionId];
    if (!evaluation!.selectedIds.includes(optionId) && blocked?.length) {
      set({ lastMessage: blocked[0] });   // workbook customer copy, surfaced as toast
      return;
    }
    const next = userSelectedIds.includes(optionId)
      ? userSelectedIds.filter(id => id !== optionId)
      : [...userSelectedIds, optionId];
    set({ userSelectedIds: next,
          evaluation: evaluateConfiguration(data!.models[modelKey], variantId, next),
          lastMessage: undefined });
  },
}));
```

Note the re-derivation property quietly fixes a classic configurator bug: because auto-included options are recomputed from rules on every evaluation (not pushed into the user list), **deselecting a package automatically sheds its auto-includes** — they were never user state to begin with. A single-pass "push the include into the selection array" approach orphans those options; this design cannot.

When switching **variants**, legal selections are carried forward and workbook defaults re-seeded — never a blind reset (users hate losing a paint choice because they toggled coupe↔convertible).

---

## 4. Rule Engine

This is the component where depth matters most, so the position is explicit: a **single-pass toggle check is insufficient**. Checking only the clicked option's excludes, applying includes one level deep, and skipping `requires` entirely cannot enforce a workbook of this complexity (chained includes, group constraints, rules firing on auto-added options). The engine must be a **pure, deterministic fixed-point evaluator**.

### 4.1 Pipeline

`evaluateConfiguration(model, variantId, userSelectedIds)` runs:

1. **OVS gate** — seed only user selections that are selectable on this variant (compact availability lookup: exceptions map → default status).
2. **Standard & default seeding** — `standard` availability ⇒ selected + **locked** ("Standard equipment"); `defaultSelected` and `default_selection_rules` ⇒ selected + tagged auto.
3. **Fixed-point cascade over direct rules** — loop until no changes (pass cap ≈ 30 + cycle detection on the change-signature, so a malformed workbook A⇄B oscillation degrades to a violation rather than a hang):
   - `includes`/`requires` with `runtime_action: auto_add` → add target if selectable, mark `autoSelected` + `locked` with the rule's customer message; if target is unavailable → **violation**.
   - `requires` with `runtime_action: block` → don't mutate; emit the workbook's block message (§4.4).
   - `excludes` / `excludes_any` → remove the conflicting option **unless it's locked** (you can never silently strip standard or rule-required equipment — that case becomes a hard violation instead).
   - `replace` → swap target out for source (single-section swap semantics: selecting a new paint deselects the old in a `selectionMode: 'single'` section).
4. **Exclusive groups** — enforce `min/max` selections; on overflow, keep the *most recent user* selection (or the locked member), drop the rest; conflicts between two locked members are violations.
5. **Group validation** — `requires_any`: if exactly one member is selectable, auto-satisfy; otherwise emit a violation listing the members. `excludes_any` handled in the cascade.
6. **Disabled-reason computation** — for every option, derive *why* it can't be selected right now (unavailable on variant, excluded by X, exclusive group full), so the UI can disable with an explanatory tooltip instead of a dead button.
7. **Pricing** (§5) — computed last, from the final selection set.

Every auto-mutation returns an **explanatory event** (toast with the reason + one-tap undo), so the engine is never "spooky."

### 4.2 Core loop (abridged)

```ts
let changed = true, passes = 0;
const seen = new Set<string>();          // cycle detection on selection signature
while (changed && passes++ < 30) {
  changed = false;
  for (const rule of model.rules) {
    if (!matchesScope(rule.scope, model, variant)) continue;
    if (rule.sourceId && !selected.has(rule.sourceId)) continue;

    switch (rule.type) {
      case "includes":
      case "requires":
        if (rule.targetId && !selected.has(rule.targetId)) {
          if (rule.runtimeAction === "block") {
            block(rule);                                  // surfaced pre-toggle (§4.4)
          } else if (selectable(rule.targetId)) {
            selected.add(rule.targetId);
            autoSelected[rule.targetId] = rule.message ?? `Required by ${label(rule.sourceId)}`;
            locked[rule.targetId] = autoSelected[rule.targetId];
            changed = true;
          } else violation(rule);                          // requires unavailable target
        }
        break;
      case "excludes":
        if (rule.targetId && selected.has(rule.targetId)) {
          if (locked[rule.targetId]) violation(rule);      // never strip locked equipment
          else { selected.delete(rule.targetId); changed = true; note(rule); }
        }
        break;
      // replace, default, excludes_any: analogous
    }
  }
  changed = enforceExclusiveGroups(...) || changed;
  const sig = [...selected].sort().join("|");
  if (seen.has(sig)) { violation(cycleViolation()); break; }
  seen.add(sig);
}
```

All scope matching (`modelKeys`, `variantIds`, `bodyStyles`, `trims`) honors `*`/`all` wildcards, mirroring the parser.

### 4.3 Conflict-resolution UX policy

A point most configurators leave vague — here it's an explicit hierarchy, and it's **workbook-driven** via the rule's `runtime_action` column, with defaults when unspecified:

1. **Auto-swap** within a single-select section or exclusive group (replacing paint with paint) — silent except for the visual change.
2. **Auto-add** for `includes`/`requires` marked `auto_add` — toast with the workbook's customer copy + undo.
3. **Block** for rules marked `block` or where auto-resolution would remove a *user-chosen* (not just auto-added) option — the click is rejected pre-mutation and the workbook message is shown. We never silently delete something the user explicitly picked.
4. **Violation banner** for states the engine cannot resolve (requires-unavailable, locked-vs-locked) — these also flag the PDF export.

### 4.4 Validation surface

The same `EvaluationResult` drives: disabled option cards (with reasons), toast events, a violations banner, and a "configuration is valid" gate on PDF export.

---

## 5. Real-Time Pricing

Pricing is a pure function of the final evaluated selection — recomputed on every change, so it is real-time by construction:

```ts
export function calculateQuote(model, variantId, selectedIds): Quote {
  let base = variant.basePrice;                       // variant_master
  base = applyPriceRefNormalization(base, variant);   // cross-model PriceRef trim normalization

  const prices = new Map(selectedIds.map(id =>
    [id, availability(id).priceOverride ?? model.options[id].price]));

  for (const r of model.priceRules) {
    if (!matchesScope(r.scope, ...) ) continue;
    if (r.sourceId && !selected.has(r.sourceId)) continue;
    if (r.conditionOptionId && !selected.has(r.conditionOptionId)) continue;
    switch (norm(r.action)) {
      case "base_price_override": base = r.amount; break;
      case "set_price": prices.set(r.targetId, r.amount); break;
      case "delta":     prices.set(r.targetId, (prices.get(r.targetId) ?? 0) + r.amount); break;
      case "included": case "waive": prices.set(r.targetId, 0); break;
    }
  }
  return toLines(base, prices);   // ordered, labeled, RPO-tagged line items
}
```

Conditional pricing ("option A costs less when package B is present") falls out of `conditionOptionId`. Money is formatted via `Intl.NumberFormat` with a locale/currency setting, not hardcoded `$` strings.

**Pricing completeness (open considerations, parser-ready):** the schema reserves quote lines for **destination/delivery charge** (a `PriceRef` row, `type: "destination"`), tax estimation (explicitly labeled "excludes tax/title/license" if the workbook doesn't model it), and a single **rounding policy** (round-half-up to whole dollars at the line level, summed exactly). If the workbook adds these rows, no code changes are needed.

---

## 6. Visual Layering Strategy

### 6.1 Slot-based stacked `<img>` rendering

`asset_map` rows with `role=layer` drive the stack. Resolution is **slot-based — one winner per `layer_key`** (shadow < body < roof < wheels < calipers < stripes < badges), not a naive "stack everything that matches," which double-renders when assets overlap.

When multiple rows match the same slot (e.g., a generic wheel image and a Z06-trim-specific one), the winner is chosen by **specificity scoring**, CSS-cascade style:

```ts
function specificity(a: AssetRef): number {
  let s = 0;
  if (a.variantId && a.variantId !== "*") s += 8;
  if (a.bodyStyle && a.bodyStyle !== "*") s += 4;
  if (a.trim && a.trim !== "*")           s += 4;
  if (a.optionId || a.rpo)                s += 16;
  return s;
}
```

```tsx
export function VisualizerCanvas({ model, variant, selectedIds }: Props) {
  const layers = useMemo(
    () => resolveImageLayers(model, variant, selectedIds),
    [model, variant, selectedIds]);

  return (
    <div className="visualizer-stage" role="img"
         aria-label={describeConfiguration(model, variant, selectedIds)}>
      {layers.map(l => (
        <img key={l.layerKey} src={l.src} alt=""        /* stage carries the label */
             style={{ zIndex: l.layerOrder }} draggable={false} />
      ))}
    </div>
  );
}
```

```css
.visualizer-stage { position: relative; aspect-ratio: 16/9; overflow: hidden; }
.visualizer-stage img {
  position: absolute; inset: 0; width: 100%; height: 100%;
  object-fit: contain;
  pointer-events: none;     /* no drag/interaction artifacts on overlays */
  user-select: none;
  transition: opacity 180ms ease;   /* cross-fade on swap */
}
```

Layer-order convention (workbook-owned via `layer_order`): `0` shadow/base → `10` body paint → `20` roof → `30` wheels → `40` calipers → `50` stripes → `60` badges → `70` lighting overlays. Layers are filtered by body style/trim with wildcard tolerance; an option with no mapped asset still affects price/rules, it just adds no image.

### 6.2 Image loading UX (no pop-in)

A visual configurator lives or dies on swap quality, so this is handled explicitly:

- **Preload adjacent candidates:** when a section is open, `new Image().src = ...` (or `<link rel="preload">`) for that section's layer variants, so the first paint-swap is instant.
- **Atomic swaps via