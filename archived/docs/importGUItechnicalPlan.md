# Technical Implementation Plan: Local Streamlit Import Control Plane

## 1. Architectural North Star

The GUI should be a **local-only Streamlit control and decision layer** around the existing deterministic import scripts.

It must **not** become a second import engine or a direct canonical data editor.

```text
User
  ↓
Streamlit GUI
  ↓
Typed application services
  ├─ SessionService
  ├─ MapRepository
  ├─ WorkbookPreviewService
  ├─ CommandRunner
  ├─ ArtifactReader
  ├─ ProposalDiffService
  ├─ ApprovalService
  └─ LockManager
  ↓
Plain CSV / JSON maps + import_session.json
  ↓
Existing deterministic scripts
  ↓
Staging artifacts / audit artifacts / proposal artifacts
  ↓
Explicit reviewed apply step
  ↓
Canonical data
```

### Non-negotiable invariants

| Principle                                    | Enforcement                                                                                                                      |
| -------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **GUI is not the engine**                    | GUI triggers scripts through subprocesses. It does not implement extraction or canonical mutation logic.                         |
| **Maps are the durable source of decisions** | Every user decision is written to plain CSV/JSON under `data/import_maps/[profile]/`.                                            |
| **Session state is filesystem-backed**       | Streamlit `st.session_state` is only a UI cache. The durable state is `import_session.json`.                                     |
| **No direct canonical mutation**             | GUI cannot write canonical CSVs, staging CSVs, or `data.js`. Only an apply script can modify canonical files.                    |
| **Every click has a CLI equivalent**         | GUI actions are backed by shared services and exposed through `app.cli`; mutations are also recorded in `session_history.jsonl`. |
| **Local-only, single-user execution**        | Streamlit binds to loopback, uses filesystem locks, and refuses unsafe write paths.                                              |

---

## 2. Recommended Repository Layout

```text
repo/
├── app/
│   ├── main.py
│   ├── cli.py
│   ├── pages/
│   │   ├── 00_session_launcher.py
│   │   ├── 01_dashboard.py
│   │   ├── 02_sheet_role_classifier.py
│   │   ├── 03_range_section_mapper.py
│   │   ├── 04_review_queues.py
│   │   └── 05_proposal_review.py
│   ├── components/
│   │   ├── grid_preview.py
│   │   ├── log_viewer.py
│   │   ├── diff_table.py
│   │   └── decision_queue.py
│   ├── services/
│   │   ├── session_service.py
│   │   ├── map_repository.py
│   │   ├── workbook_preview_service.py
│   │   ├── command_runner.py
│   │   ├── artifact_reader.py
│   │   ├── proposal_diff_service.py
│   │   ├── approval_service.py
│   │   ├── validation_service.py
│   │   └── lock_manager.py
│   └── models/
│       ├── session.py
│       ├── maps.py
│       ├── artifacts.py
│       ├── proposal.py
│       ├── approvals.py
│       └── commands.py
│
├── scripts/
│   ├── inspect_order_guide_export.py
│   ├── extract_order_guide.py
│   ├── audit_order_guide.py
│   ├── generate_proposal.py
│   └── apply_proposal.py
│
├── data/
│   └── import_maps/
│       └── [profile]/
│           ├── sheet_roles.csv
│           ├── sheet_sections.csv
│           ├── range_overrides.csv
│           ├── status_symbols.csv
│           ├── variant_overrides.csv
│           ├── rpo_overlap_approvals.csv
│           └── schemas/
│               ├── sheet_roles.schema.json
│               ├── sheet_sections.schema.json
│               └── ...
│
├── build/
│   └── imports/
│       └── [year]/
│           └── [model]/
│               ├── import_session.json
│               ├── session_history.jsonl
│               ├── .session.lock
│               ├── logs/
│               ├── artifacts/
│               │   ├── inspect/
│               │   ├── extract/
│               │   ├── audit/
│               │   └── proposal/
│               └── approvals/
│                   └── apply_approval.json
│
└── tests/
    ├── unit/
    ├── contracts/
    ├── fixtures/
    ├── golden/
    └── ui_smoke/
```

### Important module boundary

The Streamlit app may import script modules only for:

- Shared type definitions.
- Pure helpers.
- Constants or enums.

All script execution must go through `CommandRunner` as a subprocess. This preserves headless parity and prevents the GUI from depending on hidden in-process script behavior.

---

## 3. Session Model

Every import begins by creating or loading:

```text
build/imports/[year]/[model]/import_session.json
```

This file is the durable session index.

### Example Pydantic model

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class StageName(StrEnum):
    INSPECT = "inspect"
    EXTRACT = "extract"
    AUDIT = "audit"
    GENERATE_PROPOSAL = "generate_proposal"
    REVIEW_APPLY_PLAN = "review_apply_plan"
    APPLY = "apply"


class StageState(StrEnum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    STALE = "stale"


class ArtifactRef(BaseModel):
    path: Path
    sha256: str | None = None
    created_at: datetime | None = None


class StageRun(BaseModel):
    state: StageState = StageState.NOT_STARTED
    command: list[str] = Field(default_factory=list)
    pid: int | None = None
    run_id: str | None = None
    log_path: Path | None = None
    manifest_path: Path | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    exit_code: int | None = None
    error_message: str | None = None


class ImportSession(BaseModel):
    schema_version: Literal[1] = 1
    session_id: UUID

    year: int
    model: str
    workbook_paths: list[Path]
    active_profile: str
    profile_map_dir: Path

    created_at: datetime
    updated_at: datetime

    active_sheet: str | None = None

    workbook_fingerprints: dict[str, str] = Field(default_factory=dict)
    map_hashes: dict[str, str] = Field(default_factory=dict)

    stages: dict[StageName, StageRun] = Field(default_factory=dict)
    artifacts: dict[str, ArtifactRef] = Field(default_factory=dict)
```

### Session rules

- `st.session_state` is never authoritative.
- All session updates are written atomically to `import_session.json`.
- Workbook fingerprints are stored to detect stale artifacts.
- If workbook path, workbook hash, year, model, profile, or map hashes change, downstream stages are marked `STALE`.
- The app refuses to run a downstream stage if its prerequisites are missing, failed, or stale.
- A sibling `session_history.jsonl` records every GUI mutation.

### `session_history.jsonl`

Each user mutation should emit an append-only event:

```json
{
  "timestamp": "2026-05-06T14:12:03Z",
  "action": "set_sheet_role",
  "cli_equivalent": [
    "python",
    "-m",
    "app.cli",
    "set-sheet-role",
    "--session",
    "build/imports/2026/model/import_session.json",
    "--sheet",
    "Exterior Colors",
    "--role",
    "ColorTrim"
  ],
  "before_sha256": "abc...",
  "after_sha256": "def...",
  "diff_summary": {
    "file": "data/import_maps/default/sheet_roles.csv",
    "rows_changed": 1
  }
}
```

This gives two layers of headless parity:

1. The same service layer powers both Streamlit and `app.cli`.
2. `replay_session.py` can replay the event log in CI and verify that the resulting proposal is byte-identical.

---

## 4. Map Repository Layer

All CSV/JSON map reads and writes should flow through a single service:

```text
MapRepository
  ├─ load_sheet_roles(profile)
  ├─ save_sheet_roles(profile, rows)
  ├─ load_sheet_sections(profile)
  ├─ save_sheet_sections(profile, rows)
  ├─ load_range_overrides(profile)
  ├─ save_range_overrides(profile, rows)
  ├─ append_status_symbol_decision(profile, row)
  ├─ append_variant_override(profile, row)
  ├─ append_rpo_overlap_approval(profile, row)
  └─ validate_all_maps(profile)
```

### Responsibilities

`MapRepository` enforces:

1. Allowed write paths.
2. Pydantic row validation.
3. Atomic writes.
4. Deterministic row ordering.
5. Schema version handling.
6. Stable CSV column order.
7. Optional `.bak` creation.
8. Map-change audit logging.
9. Protection against accidental canonical writes.
10. Hash computation for stale artifact detection.

### Allowed write roots

The GUI may write only to:

```text
data/import_maps/
build/imports/
```

The GUI must treat these as read-only:

```text
canonical data directories
staging artifacts
data.js
```

Any attempt to write outside the allowlist raises a hard error.

### Atomic write strategy

For CSV/JSON files:

1. Validate all rows with Pydantic.
2. Write to a temporary file in the same directory.
3. Flush and `fsync`.
4. Replace using `os.replace`.
5. Recompute hash.
6. Update session/map-change history.

On Windows, replacement can fail if a file is open in Excel. Handle this explicitly with:

- Clear error messages.
- Retry/backoff.
- “Close this file in Excel and retry” guidance.
- No fallback to partial writes.

Use a cross-platform lock library or equivalent lock manager rather than Unix-only `fcntl`.

---

## 5. CSV Map Contracts

CSV remains the human-reviewable durable format. Pydantic models define and validate each row type. JSON Schema files should be exported from the Pydantic models under:

```text
data/import_maps/[profile]/schemas/
```

### `sheet_roles.csv`

Purpose: durable user decisions for sheet classification.

Suggested columns:

```text
workbook_fingerprint,
sheet_name,
predicted_role,
selected_role,
confidence,
decision_source,
notes,
updated_at
```

Allowed `selected_role` values:

```text
OrderGuide,
ColorTrim,
Compatibility,
RPO,
Pricing,
Ignore,
Unknown
```

Rules:

- `selected_role` is what scripts consume.
- `predicted_role` and `confidence` are advisory.
- Existing user selections are preserved when new inspect predictions are merged.
- `Ignore` means extractor skips the sheet.
- `Unknown` blocks extraction unless explicitly allowed by profile policy.

---

### `sheet_sections.csv`

Purpose: reusable section definitions for known sheet layouts.

Suggested columns:

```text
sheet_name,
section_id,
section_type,
role,
range_a1,
row_start,
row_end,
col_start,
col_end,
priority,
notes
```

Allowed `section_type` values:

```text
Header,
Data,
Matrix,
ColorTrim,
Compatibility,
Footnote,
Ignore
```

Rules:

- Numeric coordinates are authoritative.
- `range_a1` is for human readability.
- Coordinates are 1-based Excel-style row and column indexes.
- `priority` resolves intentional overlaps.
- Section IDs must remain stable across edits.

---

### `range_overrides.csv`

Purpose: workbook-specific manual fixes.

Suggested columns:

```text
workbook_fingerprint,
sheet_name,
override_id,
section_type,
range_a1,
row_start,
row_end,
col_start,
col_end,
reason,
updated_at
```

Rules:

- Used for exceptional workbook-specific layout problems.
- Must include `workbook_fingerprint`.
- Must include a reason.
- Manual overrides are never silently overwritten by auto-detection.

Extractor precedence should be:

```text
1. range_overrides.csv
2. sheet_sections.csv
3. script heuristics
```

The extractor should emit the selected source for each sheet or section:

```text
ManualOverride | SheetSection | Heuristic
```

That value should appear in extract and audit summaries.

---

### `status_symbols.csv`

Purpose: normalize unknown status symbols such as `A/D1`.

Suggested columns:

```text
symbol,
normalized_status,
meaning,
decision_id,
supersedes_decision_id,
decision_source,
context_example,
context_hash,
notes,
updated_at
```

Example normalized statuses:

```text
Available,
Deleted,
Delayed,
Restricted,
Unknown,
Ignore
```

---

### `variant_overrides.csv`

Purpose: confirm or override detected variant IDs.

Suggested columns:

```text
source_variant_key,
detected_variant_id,
override_variant_id,
decision,
reason,
context_hash,
decision_id,
supersedes_decision_id,
updated_at
```

Allowed `decision` values:

```text
AcceptDetected,
Override,
Block,
Ignore
```

---

### `rpo_overlap_approvals.csv`

Purpose: approve, reject, or block RPO overlap cases.

Suggested columns:

```text
overlap_key,
rpo_codes,
affected_variants,
decision,
reason,
context_hash,
decision_id,
supersedes_decision_id,
updated_at
```

Allowed `decision` values:

```text
Approve,
Reject,
Block,
NeedsReview
```

### Decision history semantics

Decision maps should be append-friendly.

If a user changes a decision:

- Append a new row.
- Set `supersedes_decision_id`.
- Scripts resolve the latest active decision deterministically.

This preserves history while keeping the current effective decision reproducible.

---

## 6. Script Artifact Contract

Each deterministic script should write a typed `manifest.json`.

Example:

```json
{
  "schema_version": 1,
  "stage": "extract",
  "session_id": "e63e7a93-6843-4f8f-b86d-b7d8513d3cc6",
  "started_at": "2026-05-06T14:10:00Z",
  "completed_at": "2026-05-06T14:11:12Z",
  "exit_code": 0,
  "inputs": {
    "workbook": {
      "path": "inputs/order_guide.xlsx",
      "sha256": "..."
    },
    "sheet_roles": {
      "path": "data/import_maps/default/sheet_roles.csv",
      "sha256": "..."
    },
    "sheet_sections": {
      "path": "data/import_maps/default/sheet_sections.csv",
      "sha256": "..."
    },
    "range_overrides": {
      "path": "data/import_maps/default/range_overrides.csv",
      "sha256": "..."
    }
  },
  "outputs": {
    "staging_rows": "build/imports/2026/model/artifacts/extract/staging_rows.csv",
    "summary": "build/imports/2026/model/artifacts/extract/staging_summary.json"
  },
  "metrics": {
    "rows_extracted": 1240,
    "sheets_extracted": 8,
    "manual_ranges_used": 3,
    "heuristic_ranges_used": 5
  }
}
```

The GUI should read structured artifacts and manifests, not scrape logs.

Optional future enhancement: scripts can support `--json-events` for live progress events, but the stable contract should be the manifest and artifact files.

---

## 7. Command Runner and Long-Running Process Handling

All stage execution goes through `CommandRunner`.

```python
class CommandRunner:
    def run_stage(
        self,
        *,
        session_path: Path,
        stage: StageName,
        command: list[str],

```
