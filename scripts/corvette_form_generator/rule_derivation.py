"""Generation-time swap-rule derivation from includes-closure graph mechanics.

The workbook authors only primitive facts: real incompatibilities (plain
``excludes`` rows), the includes graph, and true default-replacements.  This
module owns the transitive derivation: if a selectable option S transitively
includes B (via active ``includes`` rules) and an active primitive excludes
rule says "A excludes B", then selecting S must evict A — a swap, expressed as
a derived ``runtime_action="replace"`` rule.

Emission is allowlist-gated (anti-surprise contract):

- EVERY closure candidate is recorded in the per-model derivation manifest
  with full provenance (``derived_via`` = includes path + primitive rule id).
- Only candidates on ``EMISSION_ALLOWLIST`` are emitted as rules; all other
  candidates land in the manifest as ``candidate_not_emitted`` and require
  separate approval before joining the allowlist.
- Authored rules always shadow derived rules for the same (source, target)
  pair; shadowed candidates are recorded as ``shadowed_by_authored``.
- An allowlisted pair that is NOT a closure candidate for its model is a hard
  generation error (stale allowlist).

Provenance is manifest-only: emitted derived rules are shaped identically to
authored replace rules in the runtime contract (no ``derived*`` fields).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from corvette_form_generator.model_config import validate_model_key
from corvette_form_generator.output import write_json_output

# Approved derived-swap emissions: (model_key, source_id, target_id).
# Spec: docs/archive/completed-specs/derived-swap-eviction-spec-2026-07-02.md §2 A1/A3 — the only
# approved pairs this pass are the five Z06 CBF equivalents. Additions
# require explicit approval of the checkpoint manifest's candidate queue.
EMISSION_ALLOWLIST: frozenset[tuple[str, str, str]] = frozenset(
    {
        ("z06", "opt_t0f_001", "opt_cbf_001"),
        ("z06", "opt_t0g_001", "opt_cbf_001"),
        ("z06", "opt_z07_001", "opt_cbf_001"),
        ("z06", "opt_pdd_001", "opt_cbf_001"),
        ("z06", "opt_pdf_001", "opt_cbf_001"),
    }
)

MANIFEST_SUFFIX = "derived-swap-manifest.json"


class StaleDerivationAllowlistError(ValueError):
    """An allowlisted (source, target) pair is no longer a closure candidate."""


def _active(rule: dict[str, Any]) -> bool:
    return rule.get("active", "True") == "True"


def _includes_graph(raw_rules: list[dict[str, Any]]) -> dict[str, list[str]]:
    graph: dict[str, list[str]] = {}
    for rule in raw_rules:
        if rule.get("rule_type") != "includes" or not _active(rule):
            continue
        source_id = rule.get("source_id", "")
        target_id = rule.get("target_id", "")
        if source_id and target_id:
            graph.setdefault(source_id, [])
            if target_id not in graph[source_id]:
                graph[source_id].append(target_id)
    return graph


def _primitive_excludes(raw_rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Active plain excludes rows (never runtime_action="replace" stacks)."""
    return [
        rule
        for rule in raw_rules
        if rule.get("rule_type") == "excludes"
        and _active(rule)
        and rule.get("runtime_action", "") != "replace"
    ]


def _closure_paths(source_id: str, graph: dict[str, list[str]]) -> dict[str, list[str]]:
    """Map of reachable option id -> includes path (cycle-guarded BFS, deterministic)."""
    paths: dict[str, list[str]] = {}
    queue: list[tuple[str, list[str]]] = [(source_id, [source_id])]
    seen = {source_id}
    while queue:
        current, path = queue.pop(0)
        for nxt in graph.get(current, []):
            if nxt in seen:
                continue
            seen.add(nxt)
            next_path = path + [nxt]
            paths[nxt] = next_path
            queue.append((nxt, next_path))
    return paths


def _derived_reason(source_label: str, target_label: str, via_label: str) -> str:
    return f"{target_label} was removed: {source_label} includes {via_label}, which replaces it."


def derive_swap_rules(
    model_key: str,
    raw_rules: list[dict[str, Any]],
    label_for_entity,
    entity_meta,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Compute derived swap rules and the per-model derivation manifest.

    ``label_for_entity(entity_id)`` returns a display label; ``entity_meta``
    is a callable returning the dict of section/type/mode fields used to
    shape a derived rule identically to authored rows.

    Returns ``(emitted_rules, manifest)``. Pure computation — no I/O.
    """

    graph = _includes_graph(raw_rules)
    primitives = _primitive_excludes(raw_rules)
    authored_pairs = {
        (rule.get("source_id", ""), rule.get("target_id", ""))
        for rule in raw_rules
        if _active(rule) and rule.get("rule_type") == "excludes"
    }

    candidates: list[dict[str, Any]] = []
    for source_id in sorted(graph):
        paths = _closure_paths(source_id, graph)
        for primitive in primitives:
            excl_source = primitive.get("source_id", "")  # A in "A excludes B"
            excl_target = primitive.get("target_id", "")  # B
            if excl_target not in paths or source_id in (excl_source, excl_target):
                continue
            candidates.append(
                {
                    "source_id": source_id,
                    "target_id": excl_source,
                    "conflict_id": excl_target,
                    "includes_path": paths[excl_target],
                    "primitive_rule_id": primitive.get("rule_id", ""),
                }
            )

    candidates.sort(key=lambda c: (c["source_id"], c["target_id"], c["conflict_id"]))

    candidate_pairs = {(c["source_id"], c["target_id"]) for c in candidates}
    for allow_model, allow_source, allow_target in sorted(EMISSION_ALLOWLIST):
        if allow_model != model_key:
            continue
        if (allow_source, allow_target) not in candidate_pairs:
            raise StaleDerivationAllowlistError(
                f"Derivation allowlist pair ({allow_model}, {allow_source}, {allow_target}) "
                "is not an includes-closure candidate in the current workbook. "
                "Remove or re-approve the stale allowlist entry."
            )

    emitted: list[dict[str, Any]] = []
    manifest_entries: list[dict[str, Any]] = []
    seen_emitted_pairs: set[tuple[str, str]] = set()
    for candidate in candidates:
        pair = (candidate["source_id"], candidate["target_id"])
        allowlisted = (model_key, *pair) in EMISSION_ALLOWLIST
        shadowed = pair in authored_pairs
        if shadowed:
            disposition = "shadowed_by_authored"
        elif allowlisted:
            disposition = "emitted" if pair not in seen_emitted_pairs else "duplicate_path_not_emitted"
        else:
            disposition = "candidate_not_emitted"
        manifest_entries.append(
            {
                "disposition": disposition,
                "source_id": candidate["source_id"],
                "target_id": candidate["target_id"],
                "derived_via": {
                    "includes_path": candidate["includes_path"],
                    "primitive_rule_id": candidate["primitive_rule_id"],
                    "conflict_id": candidate["conflict_id"],
                },
                "allowlisted": allowlisted,
            }
        )
        if disposition != "emitted":
            continue
        seen_emitted_pairs.add(pair)
        source_id, target_id = pair
        source_label = label_for_entity(source_id)
        target_label = label_for_entity(target_id)
        via_label = label_for_entity(candidate["conflict_id"])
        rule = {
            "rule_id": f"derived_{source_id}_replaces_{target_id}",
            "source_id": source_id,
            "rule_type": "excludes",
            "target_id": target_id,
            "disabled_reason": _derived_reason(source_label, target_label, via_label),
            "auto_add": "False",
            "active": "True",
            "runtime_action": "replace",
            "body_style_scope": "",
            "source_note": "",
        }
        rule.update(entity_meta(source_id, target_id))
        emitted.append(rule)

    manifest = {
        "model_key": model_key,
        "candidate_count": len(manifest_entries),
        "emitted_count": len(emitted),
        "shadowed_count": sum(1 for e in manifest_entries if e["disposition"] == "shadowed_by_authored"),
        "not_emitted_count": sum(1 for e in manifest_entries if e["disposition"] == "candidate_not_emitted"),
        "entries": manifest_entries,
    }
    return emitted, manifest


def write_derivation_manifest(output_dir: Path, model_key: str, manifest: dict[str, Any]) -> Path:
    slug = validate_model_key(model_key).replace("_", "-")
    inspection_dir = output_dir / "inspection"
    path = inspection_dir / f"{slug}-{MANIFEST_SUFFIX}"
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json_output(path, manifest)
    return path
