# Images Workspace Parity Specification

Status: authorized 2026-08-27. Scope is deliberately narrow; this is a parity
pass, not a redesign.

## 1. Why this exists

The 2026-08-21 Workbook Manager UX recovery listed six workspaces and rebuilt
five. Images got one clause — §3 item 5, "the existing asset reconciliation
capability in user-facing language" — and that clause was honoured literally:
`AssetManager.jsx` last had substantive work in PR #12, and the only
recovery-era change was five renamed strings in `91510b0`. It therefore missed
Checkpoints 3C, 3F, and 6.

Nothing is broken and nothing is unsafe: asset resolutions already become
ordinary durable draft operations and pass through the same guarded write. The
defect is that one workspace of six behaves differently from the other five.

## 2. The three gaps

1. **No editor shell (3C).** `AssetInspector` is an inline `panel`. Every other
   workspace opens `EditorShell`, which owns focus trap, Escape, dirty-close
   confirmation, body scroll lock, and focus restore to the opener.
2. **No navigation state (3F).** `AssetManager` takes `setModelKey` rather than
   `navigation` / `onNavigationChange`. An image decision cannot be deep-linked,
   does not survive reload, and is dropped when a draft starts.
3. **No lifecycle language (6).** The workspace does not consume
   `operatorLifecycle`, so it names draft state differently from the tray and
   from Review & Apply.

## 3. Required outcome

- `AssetInspector` renders inside `EditorShell` with a real `dirty` signal from
  its unsaved preview/candidate state.
- `AssetManager` accepts `navigation` and `onNavigationChange`. `asset` joins
  `ENTITY_TYPES` in `navigationState.js`; `assets` is already a workspace. A
  selected asset serialises to the URL and restores on reload.
- Draft state shown in this workspace reads from `operatorLifecycle`.
- Connected destinations resolving to an asset navigate here without losing the
  current model or draft.

## 4. Explicitly out of scope

Asset reconciliation semantics, the sync engine, fingerprint binding, matching
or classification rules, WordPress media behaviour, the resolution API
contracts, and thumbnail/preview rendering. No backend change is expected; if
one proves necessary it must be additive and named in the delivery record.

## 5. Acceptance

- A new owner test asserts each of the three gaps is closed, with a forced
  failure behind each assertion.
- The gate is registered in `tests/validation_catalog.json` and added to
  `suite.workbook_manager_serial_group` and `suite.workbook_manager_checkpoint`.
- The Manager checkpoint inventory and the frontend production build pass.
- Real-browser proof: open an image decision, reload, land in the same place;
  Escape with unsaved edits prompts; staged resolution reaches Review & Apply.

## 6. Protected boundaries

Canonical workbook and data, generated artifacts, published registry, customer
runtime, dependencies, durable mutation and Apply/Rebuild semantics, dealer
submission, media, deployment, and security behaviour are untouched.
