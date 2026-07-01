# Spec: Agent Instruction Token-Efficiency Reconfiguration

Status: COMPLETED 2026-07-01. Implemented and validated; see §11 Closure.
Recommended reasoning level for implementation: medium (mechanical rewrite against an approved content map; no runtime/business logic touched).

## 1. Goal

Reconfigure the repository's agent-facing instruction surfaces for maximum token
efficiency without losing context quality. Every session pays the full cost of
`AGENTS.md` (auto-loaded project context), and agents routinely pull `README.md`
and `Order-Guide_IngestPrompt.md` on top. The rewrite enforces:

1. A strict no-redundancy rule — each fact/rule/command lives in exactly one file.
2. A summarized file hierarchy limited to modules agents actually touch.
3. Removal of boilerplate — comments and log/echo lines inside command blocks,
   duplicated command transcripts, and repeated checklist ceremony.

## 2. Diagnosis (current-state evidence)

Files inspected: `AGENTS.md`, `README.md`, `Order-Guide_IngestPrompt.md`,
`.codex/config.toml`, `.codex/agents/*.toml`, `docs/` listing, repo root listing.

Measured sizes (bytes ≈ chars; ~4 chars/token):

| Surface | Bytes | ~Tokens | Load pattern |
|---|---|---|---|
| `AGENTS.md` | 22,740 | ~5,700 | auto-loaded every session |
| `README.md` | 21,036 | ~5,300 | read for commands/overview most passes |
| `Order-Guide_IngestPrompt.md` | 11,383 | ~2,800 | ingest passes |
| `.codex/agents/*.toml` (4) | 3,570 | ~900 | Codex delegations |

Worst common case: AGENTS.md + README ≈ 11,000 tokens of instructions before
any code is read.

### Redundancy inventory (the actual waste)

Content stated in BOTH `AGENTS.md` and `README.md`:

- Source-of-truth doctrine (workbook owns rules; scripts generic; runtime
  consumes contract): AGENTS §2–3 vs README "Architecture" prose (README:31–35).
- Generated-artifact rules (don't hand-edit; regenerate through pipeline):
  AGENTS §3, §8 vs README:120, 247, 272.
- Dealer-submission boundary: AGENTS §10 vs README:13.
- Workbook safety (Excel closed, lock files, `save_workbook_safely()`):
  AGENTS §7 vs README "Workbook Safety" (README:313–326).
- Script role descriptions: AGENTS §6 category list vs README "Repository
  Structure" per-script bullets (README:45–59) — near-total overlap.
- Ingest boundaries: AGENTS §11 vs `Order-Guide_IngestPrompt.md` vs
  `docs/ingest/README.md` — three copies of the same guardrails.
- ZR1/ZR1X unpromoted-scaffold caveat: stated 3x in README alone
  (README:12, 102, 116, 290) plus AGENTS §11.

Boilerplate inventory:

- README has 28 fenced code blocks; the four model-refresh blocks
  (README:238–311) repeat the same `cd <repo-root>` preamble and overlap the
  "Full default validation" block, which restates every test file already
  listed per-model.
- AGENTS.md repeats checklist framing ("Checklist:", "- [ ]") ~90 times;
  many items restate §1 First Principles verbatim per section.
- AGENTS §16 (Do/Don't) restates §3, §7, §8, §10 as a third copy.

Change class: docs/guidance only. Risk: medium-low (no runtime, workbook,
generated-artifact, or dealer changes; risk is context loss for future agents,
mitigated by the content-map + preservation checklist below).

## 3. Target Architecture (single-owner content map)

Each topic gets exactly ONE owning file; other files may hold a one-line
pointer, never a restatement.

| Topic | Sole owner |
|---|---|
| Agent conduct, spec-first, handoff format, validation strategy | `AGENTS.md` |
| Source-of-truth boundaries (workbook/generator/artifact/runtime/CSS) | `AGENTS.md` |
| Project overview, current state, roadmap | `README.md` |
| Repository map (summarized, relevant modules only) | `README.md` |
| Exact commands: generation, registry, promotion, validation, editor | `README.md` (one consolidated command table) |
| Workbook sheet inventory | `README.md` (compressed) |
| Ingest workflow detail | `Order-Guide_IngestPrompt.md` + `docs/ingest/` |
| Ingest boundary summary | `AGENTS.md` §11 → cut to 5 lines + pointer |
| Delegated-agent personas | `.codex/agents/*.toml` (already lean — no change) |

### 3.1 No-redundancy rule (durable, add to AGENTS.md)

Add a short standing rule to AGENTS.md: "Every instruction fact has one owning
file. When updating guidance, edit the owner and fix pointers; never duplicate
prose across AGENTS.md, README.md, or ingest docs." This makes the density
gain self-maintaining.

### 3.2 Summarized file hierarchy (relevant modules only)

Replace README "Repository Structure" (19 bullets) with a compact tree of the
surfaces agents actually edit or read:

```
stingray_master.xlsx        canonical workbook (source of truth)
scripts/
  generate_form.py          model artifacts   generate_registry.py  publish data.js
  promote_model.py          promotion         validate_workbook_*   gates
  apply_workbook_ops.py     gated writes      corvette_form_generator/  shared lib
form-output/                generated (never hand-edit)
form-app/                   static runtime; data.js is generated
tests/                      node + pytest gates
docs/, .hermes/plans/       specs and reviews
```

Drop from the map (still exist, just not instruction-relevant): `product/`,
`dist_updates/`, `backups/`, `archive/`, `asset_map-Sync`, visualizer internals
beyond one line for the workbook editor. One line notes "other dirs are
reference/archive; inspect if a task names them."

### 3.3 Boilerplate removal (comments and log statements)

- Strip all `#` comment lines and `echo`/status/log lines from fenced command
  blocks in README and ingest docs.
- Remove expected-output transcripts; state the gate name and pass criterion
  in one sentence instead.
- Collapse the four per-model refresh blocks + full-validation block into one
  parameterized block (`--model <stingray|grand_sport|z06>`) plus a single
  test-to-model table. Removes ~70 duplicated command lines.
- Convert AGENTS.md checklist ceremony to terse rule statements; keep "- [ ]"
  only in §4 (spec contents) and §15 (handoff), where the checklist IS the
  deliverable format.
- Delete AGENTS §16 as a section; fold its 3 non-duplicated items into the
  owning sections.

## 4. Exact files expected to change

- `AGENTS.md` — rewrite: keep §3 boundaries, §4 spec-first, §12 validation
  strategy, §15 handoff (compressed); merge §1+§5, §6→pointer to README
  command table, §7+§8 merged, §11 cut to summary+pointer, §16 deleted.
  Target ≤ 9,000 bytes (−60%).
- `README.md` — rewrite: dedupe doctrine to one-line pointers at AGENTS.md,
  compress repo map per §3.2, consolidate command blocks per §3.3, state
  ZR1/ZR1X caveat once. Target ≤ 10,000 bytes (−52%).
- `Order-Guide_IngestPrompt.md` — dedupe boundary prose already owned by
  AGENTS §11 and `docs/ingest/README.md`; strip transcript boilerplate.
  Target ≤ 7,000 bytes (−38%).
- No change: `.codex/agents/*.toml`, `.codex/config.toml` (already dense),
  `docs/ingest/pass-*` (historical), all code/tests/workbook/generated files.

Projected steady-state saving: ~5,500–6,500 tokens per typical session
(~50–55% of instruction load), no owned fact deleted.

## 5. Context-quality preservation checklist (hard constraints)

The rewrite must NOT drop, only relocate/compress:

- [ ] Dealer-submission protected boundary (endpoint, payload, Turnstile).
- [ ] Workbook-write safety: Excel closed, lock files, `save_workbook_safely()`,
      verify-on-disk before claiming success.
- [ ] Generated-artifact discipline: `form-output/`, `form-app/data.js` are
      never source; regenerate, don't patch.
- [ ] Spec-first requirement and its required spec contents.
- [ ] Handoff format (changed / unchanged / gates run / gates skipped+why /
      residual risk).
- [ ] Validation gate names and the surface→gate mapping (compressed to a
      table, but complete).
- [ ] ZR1/ZR1X unpromoted status and ingest-reprocess caveat (once).
- [ ] Workbook sheet inventory (may compress to family patterns, e.g.
      `<model>_{options,ovs,rule_mapping,...}` — already half-done in README).

## 6. Constraints and non-goals

- Docs-only pass. No runtime JS, CSS, Python, workbook, generated-artifact,
  or test changes. No dependencies.
- No behavior-policy changes: every rule that exists today survives; only
  duplication and boilerplate are removed.
- Non-goals: rewriting `docs/` historical specs/reviews; touching
  `.hermes/plans/` history; changing `.codex` persona definitions; altering
  ingest pass structure under `docs/ingest/pass-*`.
- Out of scope: pruning stale docs content that is wrong (flag separately if
  found; do not silently fix in this pass).

## 7. Risks

- Over-compression could drop a guardrail an agent later needs → mitigated by
  §5 checklist verified line-by-line against the pre-rewrite files at review.
- Pointer rot (owner file moves a section, pointer breaks) → mitigated by the
  standing no-redundancy rule naming files, not line numbers.
- Command-table consolidation could mistype a flag → mitigated by executing
  each consolidated command once during validation.

## 8. Validation plan (docs-only, proportional)

1. `git diff` review of all three files against §5 checklist — every preserved
   item locatable in exactly one file, zero duplicated prose blocks.
2. Byte/token count check: `wc -c AGENTS.md README.md Order-Guide_IngestPrompt.md`
   meets §4 targets.
3. Grep audit for known duplicate markers post-rewrite (e.g. `save_workbook_safely`,
   `Turnstile`, `promoted_to_runtime` each appear in one instruction owner plus
   pointers only).
4. Smoke-run consolidated command table: one representative generation +
   validation invocation per block to prove flags survived consolidation
   (`generate_form.py --model stingray`, `validate_workbook_schema.py`,
   one node test). Read-only/regeneration only; no workbook writes.
5. Companion check: `docs/ingest/README.md` pointers still resolve;
   `.codex/agents/*.toml` references to AGENTS/README sections still valid.

## 9. Companion-file impact

- `README.md`, `AGENTS.md`, `Order-Guide_IngestPrompt.md`: updated (this pass).
- `docs/ingest/README.md`: inspect; pointer fixes only if it restates moved text.
- `.codex/agents/*.toml`, tests, scripts, workbook, `form-app/`: inspected,
  no change expected.

## 10. Approval gate

Approved by user 2026-07-01 ("execute the spec"); implemented same day.

## 11. Closure (2026-07-01)

Changed surfaces: `AGENTS.md`, `README.md`, `Order-Guide_IngestPrompt.md` rewritten per the §3 content map. No code, workbook, generated-artifact, test, or `.codex` changes.

Final sizes vs targets:

| File | Before | After | Target | Result |
|---|---|---|---|---|
| AGENTS.md | 22,740 | 9,658 | ≤9,000 | −58% (slightly over target; all §5 items preserved) |
| README.md | 21,036 | 10,771 | ≤10,000 | −49% (slightly over; kept full sheet inventory + test table) |
| Order-Guide_IngestPrompt.md | 11,383 | 7,616 | ≤7,000 | −33% |
| Total | 55,159 | 28,045 | — | −49% (~6,800 tokens/worst-case session) |

Validation run:
- §5 preservation checklist verified: dealer boundary (AGENTS §6 + README endpoint line), workbook safety (AGENTS §5, README pointer), generated-artifact discipline (AGENTS §3), spec-first (§4), handoff (§11), gate mapping (README test-to-surface table + AGENTS §9), ZR1/ZR1X caveat (once in README Current State, ingest detail in prompt §guardrail 4), sheet inventory compressed to family patterns.
- Grep audit: `save_workbook_safely` 1 owner (AGENTS §5) + pointers; `Turnstile` 1x AGENTS + 1x README endpoint fact; no duplicated doctrine blocks.
- Smoke run of consolidated commands: `generate_form.py --model stingray` exit 0; `validate_workbook_schema.py` exit 0; `node --test tests/stingray-form-regression.test.mjs` 87 pass / 0 fail. Timestamp-only churn in `form-output/` reverted (docs-only pass preserved).
- Companion check: `docs/ingest/README.md` inspected — references `Order-Guide_IngestPrompt.md` by name only, no restated text to fix; `.codex/agents/*.toml` inspected-no-change.

Residual risks: AGENTS/README ~7% over byte targets — accepted rather than cutting preserved guardrails. Future agents relying on removed literal command blocks (per-model refresh sequences) must use the parameterized block + test table; behavior is identical.

Follow-up: none implied. If instruction drift recurs, the standing no-redundancy rule in AGENTS.md names the owning files.
