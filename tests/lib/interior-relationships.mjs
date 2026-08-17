// Interior/option relationships read from the workbook, for runtime sweeps.
//
// Spec `docs/superpowers/specs/2026-08-17-fast-layered-validation-suite.md` §4.2
// and §4.3. A §4.3 runtime sweep discovers its cases from data — but if it
// discovers them from the same generated payload it is exercising, a generator
// that drops a row removes the case and the expectation together and the sweep
// stays green over shrinking coverage. That is the "sets derived from the source
// they are meant to police" failure mode.
//
// So the expected relationships come from the model's own registered
// rule-mapping and colour-override sheets, read directly. The runtime half then
// has an independent statement of what must be true.
//
// The one documented normalization is resolvability: generation drops a row
// whose interior, option, or added RPO is outside the model's emitted scope
// (`rules.py` filters on `valid_ids`; `inspection.build_color_overrides` on the
// interior/option/adds triple). Callers pass the emitted identity sets so the
// expected side applies the same rule and nothing else.
//
// Note on `active`: none of `rule_mapping`, `price_rules`, or `color_overrides`
// carries an `active` column — a row's presence is its activation. There is no
// activation filter to mirror here, and inventing one would silently drop rows.
import { cell, modelSourceSheet, workbookRows } from "./workbook-truth.mjs";

/**
 * Workbook-authored relationships between interiors and options for one model.
 *
 * @param {object} options
 * @param {string} options.modelKey            model_master key, e.g. "stingray"
 * @param {Set<string>} options.interiorIds    interior ids present in the output under test
 * @param {Set<string>} options.optionIds      option ids present in the output under test
 * @returns {{
 *   includes: Map<string, Set<string>>,   interior id -> options it includes
 *   excludes: Map<string, Set<string>>,   interior id -> options unavailable with it
 *   overrides: Map<string, Map<string, string>>, interior id -> option id -> added RPO
 * }}
 */
export function workbookInteriorRelationships({ modelKey, interiorIds, optionIds }) {
  const ruleRows = workbookRows(modelSourceSheet(modelKey, "rule_mapping_sheet"));
  const overrideRows = workbookRows(modelSourceSheet(modelKey, "color_overrides_sheet"));

  const includes = new Map();
  const excludes = new Map();
  const overrides = new Map();

  const add = (map, key, value) => {
    if (!map.has(key)) map.set(key, new Set());
    map.get(key).add(value);
  };

  for (const row of ruleRows) {
    const ruleType = cell(row.rule_type).toLowerCase();
    const sourceId = cell(row.source_id);
    const targetId = cell(row.target_id);

    // An interior includes an option: source is the interior.
    if (ruleType === "includes" && interiorIds.has(sourceId) && optionIds.has(targetId)) {
      add(includes, sourceId, targetId);
    }
    // An option is unavailable with an interior: source is the option and the
    // interior is the target. The direction matters — this is not the inverse
    // of the row above, and reading it backwards produces an empty set.
    if (ruleType === "excludes" && optionIds.has(sourceId) && interiorIds.has(targetId)) {
      add(excludes, targetId, sourceId);
    }
  }

  for (const row of overrideRows) {
    const interiorId = cell(row.interior_id);
    const optionId = cell(row.option_id);
    const addsRpo = cell(row.adds_rpo);
    if (!interiorIds.has(interiorId) || !optionIds.has(optionId) || !optionIds.has(addsRpo)) {
      continue;
    }
    if (!overrides.has(interiorId)) overrides.set(interiorId, new Map());
    overrides.get(interiorId).set(optionId, addsRpo);
  }

  return { includes, excludes, overrides };
}

/** Sorted array form, so two relationship maps compare with deepEqual. */
export function relationshipPairs(map) {
  const pairs = [];
  for (const [key, values] of map) {
    for (const value of values instanceof Map ? values.keys() : values) {
      pairs.push(`${key}::${value}`);
    }
  }
  return pairs.sort();
}
