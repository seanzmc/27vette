"""Safe asset_map maintenance helpers and CLI implementation.

This module keeps WordPress media discovery separate from workbook-authored
runtime image metadata. Dry-run/report mode is the default; apply mode saves
through the project safe-save helper.
"""

from __future__ import annotations

import argparse
import base64
import csv
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, unquote
from urllib.request import Request, urlopen

from openpyxl import load_workbook

from corvette_form_generator.workbook import clean, rows_from_sheet, save_workbook_safely, workbook_truthy

SITE = "stingraychevroletcorvette.com"
MEDIA_ENDPOINT = f"https://{SITE}/wp-json/wp/v2/media"
PATH_FILTER = "/wp-content/uploads/pictures/27vette/"
WORDPRESS_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 Chrome/125 Safari/537.36 27vette-asset-map-sync/1.0"
)
ASSET_SHEET = "asset_map"
TARGET_TYPE_OPTION = "option"
TARGET_TYPE_MODEL = "model"
TARGET_TYPE_CONTEXT_CHOICE = "context_choice"
SUPPORTED_TARGET_TYPES = {TARGET_TYPE_OPTION, TARGET_TYPE_MODEL, TARGET_TYPE_CONTEXT_CHOICE}
NEW_ROW_FIT = "cover"
NEW_ROW_POSITION = "center"
NEW_ROW_NOTE = "auto-seeded"
MISSING_IMAGE_ACTIONS = {"flag_missing", "flag_ambiguous", "flag_dead_no_match"}

COVERAGE_EXPECTED = "expected"
COVERAGE_NOT_EXPECTED = "not_expected"
COVERAGE_INTENTS = (COVERAGE_EXPECTED, COVERAGE_NOT_EXPECTED)
ACTIONABLE_COVERAGE_INTENTS = {COVERAGE_EXPECTED, ""}
COVERAGE_RULESET_VERSION = "phase4b-v1"
COVERAGE_RULESET = (
    "target_type:model|context_choice -> expected",
    "section selection_mode=display_only -> not_expected",
    "section_presentation standard_equipment_bucket -> not_expected",
    "all other active+selectable option targets -> expected (universal policy)",
)

IMGI_RE = re.compile(r"^imgi_\d+_(.+)$")
PREFIX_RE = re.compile(r"^([cehrsg])-(.+)$")
MODEL_BODY_STYLE_RE = re.compile(r"^([cehrsg])(07|67)-([12])$")
SPLIT_RE = re.compile(r"[-_]")
RPO_RE = re.compile(r"^[0-9a-z]{3}$")

MODEL_PREFIX = {
    "c": "stingray",
    "e": "grand_sport",
    "h": "z06",
    "r": "zr1",
    "s": "zr1x",
    "g": "grand_sport_x",
}
MODEL_TARGET_STEMS = {
    "stingray": ("stingray", "stingray"),
    "grand-sport": ("grand_sport", "grandSport"),
    "grand_sport": ("grand_sport", "grandSport"),
    "grandsport": ("grand_sport", "grandSport"),
    "z06": ("z06", "z06"),
    "zr1": ("zr1", "zr1"),
    "zr1x": ("zr1x", "zr1x"),
    "grand-sport-x": ("grand_sport_x", "grandSportX"),
    "grand_sport_x": ("grand_sport_x", "grandSportX"),
    "grandsportx": ("grand_sport_x", "grandSportX"),
}
BODY_STYLE_CODE = {"07": "coupe", "67": "convertible"}
BODY_STYLE_IMAGE_FIELD = {"1": "image_url", "2": "hover_image_url"}


@dataclass(frozen=True)
class SyncResult:
    report_path: Path
    missing_path: Path
    unmatched_path: Path
    manifest_path: Path
    url_write_count: int
    insert_count: int
    action_counts: dict[str, int]
    unmatched_count: int
    unparseable_count: int
    backup_path: Path | None = None


class WordPressMediaFetchError(RuntimeError):
    """Raised when live WordPress media fetch is blocked with actionable guidance."""


@dataclass(frozen=True)
class SyncPlan:
    report: list[dict[str, str]]
    url_writes: dict[tuple[int, str], str]
    inserts: list[dict[str, Any]]
    status: dict[int, str]
    used: set[str]
    section_coverage: dict[str, Any] = field(default_factory=dict)

    def __iter__(self):
        """Preserve the older tuple-unpack test/helper contract."""

        yield self.report
        yield self.url_writes
        yield self.inserts
        yield self.status
        yield self.used


@dataclass(frozen=True)
class MediaInventory:
    option_exact: dict[tuple[str, str], list[str]]
    option_bare: dict[str, list[str]]
    model: dict[tuple[str, str], list[str]]
    bodystyle: dict[tuple[str, str, str], list[str]]
    unparseable: list[str]


def filename_stem(url: str) -> str:
    base = unquote(os.path.basename(urlparse(url).path))
    return os.path.splitext(base)[0].lower()


def parse_media(url: str) -> tuple[str | None, str, bool]:
    """Return ``(model_key_or_none, rpo, is_valid)`` parsed from a media URL."""

    stem = filename_stem(url)
    match = IMGI_RE.match(stem)
    if match:
        stem = match.group(1)
    model = None
    match = PREFIX_RE.match(stem)
    if match:
        model = MODEL_PREFIX[match.group(1)]
        stem = match.group(2)
    rpo = SPLIT_RE.split(stem)[0]
    return model, rpo, bool(RPO_RE.match(rpo))


def parse_model_media(url: str) -> tuple[str | None, str | None]:
    """Return ``(model_key, target_id)`` for model-card media filenames."""

    return MODEL_TARGET_STEMS.get(filename_stem(url), (None, None))


def parse_bodystyle_media(url: str) -> tuple[str | None, str | None, str | None]:
    """Return ``(model_key, body_style_target_id, image_field)`` for body style media."""

    match = MODEL_BODY_STYLE_RE.match(filename_stem(url))
    if not match:
        return None, None, None
    model_key = MODEL_PREFIX[match.group(1)]
    body_style = BODY_STYLE_CODE[match.group(2)]
    image_field = BODY_STYLE_IMAGE_FIELD[match.group(3)]
    return model_key, f"body_style__{body_style}", image_field


def build_media_index(media_urls: Iterable[str]) -> tuple[dict[tuple[str, str], list[str]], dict[str, list[str]], list[str]]:
    exact: dict[tuple[str, str], list[str]] = defaultdict(list)
    bare: dict[str, list[str]] = defaultdict(list)
    unparseable: list[str] = []
    for url in media_urls:
        model, rpo, ok = parse_media(url)
        if not ok:
            unparseable.append(url)
        elif model:
            exact[(model, rpo)].append(url)
        else:
            bare[rpo].append(url)
    return exact, bare, unparseable


def build_media_inventory(media_urls: Iterable[str]) -> MediaInventory:
    option_exact: dict[tuple[str, str], list[str]] = defaultdict(list)
    option_bare: dict[str, list[str]] = defaultdict(list)
    model_media: dict[tuple[str, str], list[str]] = defaultdict(list)
    bodystyle_media: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    unparseable: list[str] = []
    for url in media_urls:
        parsed_any = False
        model_key, target_id = parse_model_media(url)
        if model_key and target_id:
            model_media[(model_key, target_id)].append(url)
            parsed_any = True
        body_model, body_target, image_field = parse_bodystyle_media(url)
        if body_model and body_target and image_field:
            bodystyle_media[(body_model, body_target, image_field)].append(url)
            parsed_any = True
        option_model, rpo, ok = parse_media(url)
        if ok and not parsed_any:
            parsed_any = True
            if option_model:
                option_exact[(option_model, rpo)].append(url)
            else:
                option_bare[rpo].append(url)
        if not parsed_any:
            unparseable.append(url)
    return MediaInventory(
        option_exact=dict(option_exact),
        option_bare=dict(option_bare),
        model=dict(model_media),
        bodystyle=dict(bodystyle_media),
        unparseable=unparseable,
    )


def _auth_header_from_env() -> str | None:
    user = os.environ.get("WP_USER")
    password = os.environ.get("WP_APP_PASSWORD")
    if not user or not password:
        return None
    token = f"{user}:{password.replace(' ', '')}".encode("utf-8")
    return "Basic " + base64.b64encode(token).decode("ascii")


def _open_json(url: str, *, auth_header: str | None, timeout: float) -> tuple[list[dict[str, Any]], dict[str, str]]:
    headers = {"Accept": "application/json", "User-Agent": WORDPRESS_USER_AGENT}
    if auth_header:
        headers["Authorization"] = auth_header
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - project-controlled endpoint/CLI URL
        payload = json.loads(response.read().decode("utf-8"))
        response_headers = {key.lower(): value for key, value in response.headers.items()}
    return payload, response_headers


def _media_fetch_error(exc: HTTPError, api_url: str) -> WordPressMediaFetchError:
    return WordPressMediaFetchError(
        f"WordPress media fetch failed with HTTP {exc.code} from {api_url}. "
        "If media is private, set WP_USER/WP_APP_PASSWORD; otherwise use "
        "--media-url-list <path> for deterministic report/apply review."
    )


def fetch_media(timeout: float, modified_after: str | None = None) -> list[str]:
    """Fetch WordPress media URLs using stdlib HTTP and optional Basic auth."""

    auth_header = _auth_header_from_env()
    urls: list[str] = []
    page = 1
    while True:
        params: dict[str, Any] = {
            "per_page": 100,
            "page": page,
            "_fields": "source_url",
            "media_type": "image",
        }
        if modified_after:
            params.update({"modified_after": modified_after, "orderby": "modified", "order": "desc"})
        api_url = f"{MEDIA_ENDPOINT}?{urlencode(params)}"
        try:
            batch, headers = _open_json(api_url, auth_header=auth_header, timeout=timeout)
        except HTTPError as exc:
            if exc.code == 400 and page > 1:
                break
            if exc.code in {401, 403}:
                raise _media_fetch_error(exc, api_url) from exc
            raise
        if not batch:
            break
        for item in batch:
            url = clean(item.get("source_url"))
            if PATH_FILTER in url:
                urls.append(url)
        total_pages = int(headers.get("x-wp-totalpages", page))
        if page >= total_pages:
            break
        page += 1
    return urls


def read_media_url_list(path: Path | str) -> list[str]:
    media_path = Path(path)
    urls: list[str] = []
    for line in media_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            urls.append(stripped)
    return urls


def state_path(report_dir: Path) -> Path:
    return report_dir / ".asset_map_sync_state.json"


def read_since_auto(report_dir: Path, cushion_hours: int = 6) -> tuple[str | None, bool]:
    path = state_path(report_dir)
    if not path.exists():
        return None, False
    try:
        timestamp = json.loads(path.read_text(encoding="utf-8")).get("last_run_utc")
        if not timestamp:
            return None, True
        return (datetime.fromisoformat(timestamp) - timedelta(hours=cushion_hours)).strftime("%Y-%m-%dT%H:%M:%S"), True
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return None, True


def write_state(report_dir: Path) -> None:
    payload = {"last_run_utc": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")}
    state_path(report_dir).write_text(json.dumps(payload), encoding="utf-8")


def url_alive(url: str, timeout: float) -> bool:
    try:
        request = Request(url, method="HEAD")
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - user/workbook-provided URL liveness check
            return response.status < 400
    except HTTPError as exc:
        if exc.code != 405:
            return False
        try:
            request = Request(url, method="GET")
            with urlopen(request, timeout=timeout) as response:  # noqa: S310 - user/workbook-provided URL liveness check
                return response.status < 400
        except (HTTPError, URLError, TimeoutError):
            return False
    except (URLError, TimeoutError):
        return False


def check_existing(urls: Iterable[str], timeout: float, workers: int) -> dict[str, bool]:
    unique_urls = sorted(set(urls))
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        return dict(executor.map(lambda url: (url, url_alive(url, timeout)), unique_urls))


def discover_promoted_option_sources(wb) -> dict[str, str]:
    """Return promoted runtime model -> source option sheet mapping."""

    if "model_registry_promotion" not in wb.sheetnames:
        raise ValueError("Missing required workbook sheet 'model_registry_promotion'.")
    if "model_workbook_sources" not in wb.sheetnames:
        raise ValueError("Missing required workbook sheet 'model_workbook_sources'.")

    promoted_rows = [
        row
        for row in rows_from_sheet(wb, "model_registry_promotion")
        if workbook_truthy(row.get("active")) and workbook_truthy(row.get("promoted_to_runtime"))
    ]
    promoted_rows.sort(key=lambda row: (int(clean(row.get("display_order")) or 0), clean(row.get("model_key"))))
    promoted_models = [clean(row.get("model_key")).lower() for row in promoted_rows if clean(row.get("model_key"))]

    source_rows = [
        row
        for row in rows_from_sheet(wb, "model_workbook_sources")
        if workbook_truthy(row.get("active")) and clean(row.get("source_role")) == "source_option_sheet"
    ]
    source_by_model = {clean(row.get("model_key")).lower(): clean(row.get("sheet_name")) for row in source_rows}

    sources: dict[str, str] = {}
    for model_key in promoted_models:
        sheet_name = source_by_model.get(model_key)
        if not sheet_name:
            raise ValueError(f"Promoted model {model_key!r} is missing an active source_option_sheet row.")
        if sheet_name not in wb.sheetnames:
            raise ValueError(f"Promoted model {model_key!r} source option sheet {sheet_name!r} is missing.")
        sources[model_key] = sheet_name
    return sources


def _header_index(ws) -> dict[str, int]:
    headers = [clean(cell.value).lower() for cell in ws[1]]
    return {header: index for index, header in enumerate(headers) if header}


def read_option_sheets(wb, sources: dict[str, str]) -> dict[tuple[str, str, str], dict[str, str]]:
    desired: dict[tuple[str, str, str], dict[str, str]] = {}
    for model_key, sheet_name in sources.items():
        ws = wb[sheet_name]
        index = _header_index(ws)
        missing = {"option_id", "rpo", "selectable", "active"} - set(index)
        if missing:
            raise ValueError(f"{sheet_name} missing required columns: {', '.join(sorted(missing))}")
        for row in ws.iter_rows(min_row=2, values_only=True):
            if not any(clean(value) for value in row):
                continue
            option_id = clean(row[index["option_id"]]).lower()
            if not option_id:
                continue
            if not (workbook_truthy(row[index["active"]]) and workbook_truthy(row[index["selectable"]])):
                continue
            rpo = clean(row[index["rpo"]]).lower()
            name = clean(row[index["option_name"]]) if "option_name" in index else ""
            section_id = clean(row[index["section_id"]]).lower() if "section_id" in index else ""
            desired[(model_key, TARGET_TYPE_OPTION, option_id)] = {
                "target_type": TARGET_TYPE_OPTION,
                "rpo": rpo,
                "name": name,
                "section_id": section_id,
                "source_sheet": sheet_name,
            }
    return desired


def read_model_targets(wb) -> dict[tuple[str, str, str], dict[str, str]]:
    desired: dict[tuple[str, str, str], dict[str, str]] = {}
    if "model_registry_promotion" not in wb.sheetnames:
        return desired
    for row in rows_from_sheet(wb, "model_registry_promotion"):
        if not (workbook_truthy(row.get("active")) and workbook_truthy(row.get("promoted_to_runtime"))):
            continue
        model_key = clean(row.get("model_key")).lower()
        target_id = clean(row.get("registry_key")) or model_key
        if not model_key or not target_id:
            continue
        desired[(model_key, TARGET_TYPE_MODEL, target_id)] = {
            "target_type": TARGET_TYPE_MODEL,
            "rpo": "",
            "name": clean(row.get("model_label")) or target_id,
            "section_id": "",
            "source_sheet": "model_registry_promotion",
        }
    return desired


def read_bodystyle_targets(sources: dict[str, str]) -> dict[tuple[str, str, str], dict[str, str]]:
    desired: dict[tuple[str, str, str], dict[str, str]] = {}
    for model_key in sources:
        for body_style, display_name in (("coupe", "Coupe"), ("convertible", "Convertible")):
            target_id = f"body_style__{body_style}"
            desired[(model_key, TARGET_TYPE_CONTEXT_CHOICE, target_id)] = {
                "target_type": TARGET_TYPE_CONTEXT_CHOICE,
                "rpo": "",
                "name": display_name,
                "section_id": "sec_context_body_style",
                "source_sheet": "generated_body_style_context",
            }
    return desired


@dataclass(frozen=True)
class SectionCoverageMetadata:
    """Workbook-derived section metadata used by the coverage-intent classifier."""

    selection_mode: dict[str, str]
    standard_equipment_buckets: set[tuple[str, str]]


def read_section_coverage_metadata(wb) -> SectionCoverageMetadata:
    """Read section metadata for coverage classification; tolerates missing sheets."""

    selection_mode: dict[str, str] = {}
    buckets: set[tuple[str, str]] = set()
    if "section_master" in wb.sheetnames:
        for row in rows_from_sheet(wb, "section_master"):
            section_id = clean(row.get("section_id")).lower()
            if not section_id:
                continue
            selection_mode[section_id] = clean(row.get("selection_mode")).lower()
    if "section_presentation" in wb.sheetnames:
        for row in rows_from_sheet(wb, "section_presentation"):
            if not (workbook_truthy(row.get("active")) and workbook_truthy(row.get("standard_equipment_bucket"))):
                continue
            model_key = clean(row.get("model_key")).lower()
            section_id = clean(row.get("section_id")).lower()
            if model_key and section_id:
                buckets.add((model_key, section_id))
    return SectionCoverageMetadata(
        selection_mode=selection_mode,
        standard_equipment_buckets=buckets,
    )


def build_coverage_classifier(
    desired: dict[tuple[str, str, str], dict[str, str]],
    section_metadata: SectionCoverageMetadata,
    existing_rows: dict[tuple[str, str, str], dict[str, Any]],
) -> Callable[[str, str, str], tuple[str, str]]:
    """Return a pure ``(model_key, target_type, target_id) -> (intent, reason)`` classifier.

    Universal-expected policy (phase4b-v1): every active+selectable option card
    is expected to carry a visual element. ``not_expected`` derives only from
    structural presentation metadata (display-only sections, standard-equipment
    buckets) — never from media inventory or asset_map coverage state, so
    classifications self-correct when workbook presentation metadata changes.
    ``existing_rows`` is accepted for signature stability but unused by policy.
    """

    del existing_rows  # policy must not depend on coverage state (no circularity)

    def classify(model_key: str, target_type: str, target_id: str) -> tuple[str, str]:
        if target_type in (TARGET_TYPE_MODEL, TARGET_TYPE_CONTEXT_CHOICE):
            return COVERAGE_EXPECTED, f"target_type:{target_type}"
        info = desired.get((model_key, target_type, target_id), {})
        section_id = info.get("section_id", "")
        if section_id and section_metadata.selection_mode.get(section_id) == "display_only":
            return COVERAGE_NOT_EXPECTED, f"section-display-only:{section_id}"
        if section_id and (model_key, section_id) in section_metadata.standard_equipment_buckets:
            return COVERAGE_NOT_EXPECTED, f"standard-equipment-bucket:{section_id}"
        if not section_id or section_id not in section_metadata.selection_mode:
            return COVERAGE_EXPECTED, "unmatched-section"
        return COVERAGE_EXPECTED, "universal-expected"

    return classify


def existing_asset_rows(ws, header_index: dict[str, int]) -> dict[tuple[str, str, str], dict[str, Any]]:
    rows: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row_number, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        target_type = clean(row[header_index["target_type"]]).lower()
        if target_type not in SUPPORTED_TARGET_TYPES:
            continue
        model_key = clean(row[header_index["model_key"]]).lower()
        target_id = clean(row[header_index["target_id"]])
        target_id_key = target_id.lower() if target_type == TARGET_TYPE_OPTION else target_id
        if not model_key or not target_id_key:
            continue
        values = {
            "row": row_number,
            "target_type": target_type,
            "url": clean(row[header_index["image_url"]]),
        }
        if "hover_image_url" in header_index:
            values["hover_image_url"] = clean(row[header_index["hover_image_url"]])
        rows[(model_key, target_type, target_id_key)] = values
    return rows


def reconcile(
    desired: dict[tuple[str, str, str], dict[str, str]],
    media: MediaInventory | dict[tuple[str, str], list[str]],
    bare: dict[str, list[str]] | None = None,
    existing_rows: dict[tuple[str, str, str], dict[str, Any]] | None = None,
    alive: dict[str, bool] | None = None,
    incremental: bool = False,
    classify_coverage: Callable[[str, str, str], tuple[str, str]] | None = None,
) -> SyncPlan:
    """Pure reconciliation of desired asset targets vs current hosted media inventory."""

    if not isinstance(media, MediaInventory):
        media = MediaInventory(
            option_exact=media,
            option_bare=bare or {},
            model={},
            bodystyle={},
            unparseable=[],
        )
    existing_rows = existing_rows or {}
    alive = alive or {}

    def resolve_option(model_key: str, rpo: str) -> tuple[dict[str, str], str, str]:
        if not rpo:
            return {}, "no-rpo", "no rpo in option sheet"
        if (model_key, rpo) in media.option_exact:
            return {"image_url": media.option_exact[(model_key, rpo)][0]}, "prefixed", ""
        if rpo in media.option_bare:
            if len(media.option_bare[rpo]) == 1:
                return {"image_url": media.option_bare[rpo][0]}, "bare-shared", ""
            return {}, "bare-ambiguous", f"multiple bare files for '{rpo}'; keep one shared file or add c/e/h/r/s/g prefixes"
        return {}, "none", ""

    def resolve_fields(model_key: str, target_id: str, info: dict[str, str]) -> tuple[dict[str, str], str, str]:
        target_type = info.get("target_type", TARGET_TYPE_OPTION)
        if target_type == TARGET_TYPE_OPTION:
            return resolve_option(model_key, info.get("rpo", ""))
        if target_type == TARGET_TYPE_MODEL:
            candidates = media.model.get((model_key, target_id), [])
            if len(candidates) == 1:
                return {"image_url": candidates[0]}, "model-filename", ""
            if len(candidates) > 1:
                return {}, "model-ambiguous", f"multiple model files for '{target_id}'"
            return {}, "none", ""
        if target_type == TARGET_TYPE_CONTEXT_CHOICE:
            fields: dict[str, str] = {}
            ambiguous: list[str] = []
            for field in ("image_url", "hover_image_url"):
                candidates = media.bodystyle.get((model_key, target_id, field), [])
                if len(candidates) == 1:
                    fields[field] = candidates[0]
                elif len(candidates) > 1:
                    ambiguous.append(field)
            if ambiguous:
                return {}, "bodystyle-ambiguous", f"multiple body-style files for {', '.join(ambiguous)}"
            if fields:
                return fields, "bodystyle-filename", ""
            return {}, "none", ""
        return {}, "unsupported-target-type", f"unsupported target_type '{target_type}'"

    report: list[dict[str, str]] = []
    url_writes: dict[tuple[int, str], str] = {}
    inserts: list[dict[str, Any]] = []
    status: dict[int, str] = {}
    used: set[str] = set()

    def add_report(
        scope: str,
        model_key: str,
        source_sheet: str,
        target_type: str,
        target_id: str,
        rpo: str,
        action: str,
        source: str,
        existing_url: str,
        new_url: str,
        image_status: str,
        note: str = "",
    ) -> None:
        info = desired.get((model_key, target_type, target_id), {})
        if classify_coverage is None:
            coverage_intent, coverage_reason = "", ""
        else:
            coverage_intent, coverage_reason = classify_coverage(model_key, target_type, target_id)
        report.append(
            {
                "scope": scope,
                "model_key": model_key,
                "source_sheet": source_sheet,
                "section_id": info.get("section_id", ""),
                "target_type": target_type or info.get("target_type", ""),
                "target_id": target_id,
                "rpo": rpo,
                "option_name": info.get("name", ""),
                "action": action,
                "candidate_source": source,
                "existing_url": existing_url,
                "new_url": new_url,
                "image_status": image_status,
                "coverage_intent": coverage_intent,
                "coverage_intent_reason": coverage_reason,
                "note": note,
            }
        )

    for (model_key, target_type, target_id), info in desired.items():
        rpo = info.get("rpo", "")
        source_sheet = info.get("source_sheet", "")
        fields, source, note = resolve_fields(model_key, target_id, info)
        for url in fields.values():
            used.add(url)

        existing = existing_rows.get((model_key, target_type, target_id))
        if existing:
            row_number = int(existing["row"])
            if fields:
                changed_fields = []
                for field, candidate in fields.items():
                    existing_value = clean(existing.get("url" if field == "image_url" else field))
                    if existing_value != candidate:
                        url_writes[(row_number, field)] = candidate
                        changed_fields.append(field)
                if changed_fields:
                    status[row_number] = "ok"
                    existing_url = clean(existing.get("url"))
                    action = "fill" if not existing_url else "replace_canonical"
                    add_report(
                        "existing",
                        model_key,
                        source_sheet,
                        target_type,
                        target_id,
                        rpo,
                        action,
                        source,
                        existing_url,
                        fields.get("image_url", existing_url),
                        "ok",
                        f"canonical media inventory differs in: {', '.join(changed_fields)}",
                    )
                else:
                    status[row_number] = "ok"
                    existing_url = clean(existing.get("url"))
                    add_report("existing", model_key, source_sheet, target_type, target_id, rpo, "keep", source, existing_url, existing_url, "ok")
            elif source.endswith("ambiguous"):
                status[row_number] = "ambiguous"
                add_report("existing", model_key, source_sheet, target_type, target_id, rpo, "flag_ambiguous", source, clean(existing.get("url")), "", "ambiguous", note)
            elif incremental:
                add_report("existing", model_key, source_sheet, target_type, target_id, rpo, "skip_no_candidate_incremental", source, clean(existing.get("url")), "", "missing", note)
            elif alive.get(clean(existing.get("url")), True) is False:
                action = "dead_no_match_incremental" if incremental else "flag_dead_no_match"
                status[row_number] = "url_dead"
                add_report("existing", model_key, source_sheet, target_type, target_id, rpo, action, source, clean(existing.get("url")), "", "url_dead", note)
            else:
                status[row_number] = "missing"
                add_report("existing", model_key, source_sheet, target_type, target_id, rpo, "flag_missing", source, clean(existing.get("url")), "", "missing", note)
            continue

        if fields:
            insert = {
                "model": model_key,
                "target_type": info.get("target_type", TARGET_TYPE_OPTION),
                "tid": target_id,
                "rpo": rpo,
                "name": info.get("name", ""),
                "fields": fields,
                "url": fields.get("image_url", ""),
                "status": "ok",
            }
            if source_sheet:
                insert["source_sheet"] = source_sheet
            inserts.append(insert)
            add_report("new", model_key, source_sheet, target_type, target_id, rpo, "insert_filled", source, "", fields.get("image_url", ""), "ok", note)
        elif source.endswith("ambiguous"):
            add_report("new", model_key, source_sheet, target_type, target_id, rpo, "flag_ambiguous", source, "", "", "ambiguous", note)
        elif incremental:
            add_report("new", model_key, source_sheet, target_type, target_id, rpo, "skip_no_candidate_incremental", source, "", "", "missing", note)
        else:
            add_report("new", model_key, source_sheet, target_type, target_id, rpo, "flag_missing", source, "", "", "missing", note)

    for (model_key, target_type, target_id), existing in existing_rows.items():
        if (model_key, target_type, target_id) not in desired:
            row_number = int(existing["row"])
            status[row_number] = "stale_target"
            add_report(
                "stale",
                model_key,
                "",
                target_type,
                target_id,
                "",
                "stale_target",
                "",
                clean(existing.get("url")),
                clean(existing.get("url")),
                "stale_target",
                "asset target no longer desired by current promoted model inventory",
            )

    return SyncPlan(report=report, url_writes=url_writes, inserts=inserts, status=status, used=used)


def _ensure_asset_headers(headers: list[str]) -> dict[str, int]:
    index = {header: offset for offset, header in enumerate(headers)}
    missing = {"model_key", "target_type", "target_id", "image_url"} - set(index)
    if missing:
        raise ValueError(f"asset_map missing required columns: {', '.join(sorted(missing))}")
    return index


def _write_reports(
    report_dir: Path,
    report: list[dict[str, str]],
    unmatched: list[str],
    unparseable: list[str],
    incremental: bool,
) -> tuple[Path, Path, Path, int, int]:
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / "asset_map_sync_report.csv"
    report_fieldnames = [
        "scope",
        "model_key",
        "source_sheet",
        "section_id",
        "target_type",
        "target_id",
        "rpo",
        "option_name",
        "action",
        "candidate_source",
        "existing_url",
        "new_url",
        "image_status",
        "coverage_intent",
        "coverage_intent_reason",
        "note",
    ]
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=report_fieldnames)
        writer.writeheader()
        writer.writerows(report)

    missing_path = report_dir / "asset_map_missing_images.csv"
    missing_fieldnames = [
        "model_key",
        "source_sheet",
        "section_id",
        "target_type",
        "target_id",
        "rpo",
        "option_name",
        "action",
        "candidate_source",
        "image_status",
        "coverage_intent",
        "coverage_intent_reason",
        "note",
    ]
    broad_missing_rows = [row for row in report if row["action"] in MISSING_IMAGE_ACTIONS]
    # Actionable review queue: expected only (universal policy). Structural
    # not_expected missing rows stay visible in the broad report CSV with
    # intent columns populated. Sorted model -> section -> target for triage.
    missing_rows = sorted(
        (row for row in broad_missing_rows if row.get("coverage_intent", "") in ACTIONABLE_COVERAGE_INTENTS),
        key=lambda row: (row.get("model_key", ""), row.get("section_id", ""), row.get("target_id", "")),
    )
    with missing_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=missing_fieldnames)
        writer.writeheader()
        for row in missing_rows:
            writer.writerow({field: row.get(field, "") for field in missing_fieldnames})

    unmatched_path = report_dir / "asset_map_unmatched_media.csv"
    reason = "new media in window, no row yet" if incremental else "no desired (model, rpo) for this file"
    with unmatched_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["source_url", "parsed_model", "parsed_rpo", "reason"])
        for url in unmatched:
            model_key, rpo, _ = parse_media(url)
            writer.writerow([url, model_key or "", rpo, reason])
        for url in unparseable:
            writer.writerow([url, "", "", "filename did not yield a 3-char RPO"])
    return report_path, missing_path, unmatched_path, len(missing_rows), len(broad_missing_rows)


def build_section_coverage_stats(
    desired: dict[tuple[str, str, str], dict[str, str]],
    existing_rows: dict[tuple[str, str, str], dict[str, Any]],
) -> dict[str, Any]:
    """Per-model/per-section coverage stats over ALL desired option targets.

    A target counts as covered when an existing asset_map row carries an
    image_url. Computed over the full desired set (not the missing subset) so
    percentages converge to 100 as images land.
    """

    per_model: dict[str, dict[str, dict[str, int]]] = {}
    for (model_key, target_type, target_id), info in desired.items():
        if target_type != TARGET_TYPE_OPTION:
            continue
        section_id = info.get("section_id", "") or "(none)"
        bucket = per_model.setdefault(model_key, {}).setdefault(
            section_id, {"total_targets": 0, "covered": 0, "missing": 0}
        )
        bucket["total_targets"] += 1
        existing = existing_rows.get((model_key, target_type, target_id))
        if existing and clean(existing.get("url")):
            bucket["covered"] += 1
        else:
            bucket["missing"] += 1

    stats: dict[str, Any] = {}
    for model_key in sorted(per_model):
        sections: dict[str, Any] = {}
        model_total = model_covered = 0
        for section_id in sorted(per_model[model_key]):
            bucket = per_model[model_key][section_id]
            model_total += bucket["total_targets"]
            model_covered += bucket["covered"]
            sections[section_id] = {
                **bucket,
                "coverage_pct": round(100.0 * bucket["covered"] / bucket["total_targets"], 1),
            }
        stats[model_key] = {
            "sections": sections,
            "total_targets": model_total,
            "covered": model_covered,
            "missing": model_total - model_covered,
            "coverage_pct": round(100.0 * model_covered / model_total, 1) if model_total else 0.0,
        }
    return stats


def build_coverage_summary(report: list[dict[str, str]]) -> dict[str, Any]:
    """Coverage-intent metrics over broad missing rows for the manifest."""

    broad_missing = [row for row in report if row["action"] in MISSING_IMAGE_ACTIONS]
    intent_counts = Counter(row.get("coverage_intent", "") or "unclassified" for row in broad_missing)
    section_counts: dict[str, dict[str, dict[str, int]]] = {}
    for row in broad_missing:
        model_key = row.get("model_key", "")
        section_id = row.get("section_id", "") or "(none)"
        intent = row.get("coverage_intent", "") or "unclassified"
        section_counts.setdefault(model_key, {}).setdefault(section_id, {}).setdefault(intent, 0)
        section_counts[model_key][section_id][intent] += 1
    return {
        "ruleset_version": COVERAGE_RULESET_VERSION,
        "ruleset": list(COVERAGE_RULESET),
        "broad_missing_count": len(broad_missing),
        "intent_counts": dict(intent_counts),
        "actionable_missing_count": sum(
            count for intent, count in intent_counts.items() if intent != COVERAGE_NOT_EXPECTED
        ),
        "missing_by_model_section_intent": section_counts,
    }


def _write_manifest(
    *,
    report_dir: Path,
    workbook_path: Path,
    asset_sheet: str,
    apply: bool,
    media_source: str,
    since_argument: str | None,
    resolved_modified_after: str | None,
    incremental: bool,
    state_read: bool,
    state_written: bool,
    media_url_count: int,
    verify_existing: bool,
    included_sources: dict[str, str],
    action_counts: dict[str, int],
    url_write_count: int,
    insert_count: int,
    unmatched_count: int,
    unparseable_count: int,
    report_path: Path,
    missing_path: Path,
    missing_count: int,
    broad_missing_count: int,
    coverage_summary: dict[str, Any],
    unmatched_path: Path,
) -> Path:
    manifest_path = report_dir / "asset_map_sync_manifest.json"
    payload = {
        "version": 1,
        "generated_at_utc": datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds") + "Z",
        "workbook_path": str(workbook_path),
        "asset_sheet": asset_sheet,
        "apply": apply,
        "media_source": media_source,
        "since_argument": since_argument,
        "resolved_modified_after": resolved_modified_after,
        "incremental": incremental,
        "state_path": str(state_path(report_dir)),
        "state_read": state_read,
        "state_written": state_written,
        "media_url_count": media_url_count,
        "verify_existing": verify_existing,
        "included_sources": [
            {"model_key": model_key, "option_sheet": option_sheet}
            for model_key, option_sheet in included_sources.items()
        ],
        "action_counts": action_counts,
        "url_write_count": url_write_count,
        "insert_count": insert_count,
        "unmatched_count": unmatched_count,
        "unparseable_count": unparseable_count,
        "report_path": str(report_path),
        "missing_images_path": str(missing_path),
        "missing_images_count": missing_count,
        "broad_missing_images_count": broad_missing_count,
        "coverage": coverage_summary,
        "unmatched_path": str(unmatched_path),
    }
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest_path


def build_sync_plan(
    wb,
    *,
    asset_sheet: str,
    media_urls: list[str],
    verify_existing: bool,
    timeout: float,
    workers: int,
    incremental: bool,
) -> tuple[SyncPlan, dict[str, str], list[str], list[str]]:
    if asset_sheet not in wb.sheetnames:
        raise ValueError(f"Sheet {asset_sheet!r} not found.")
    ws = wb[asset_sheet]
    headers = [clean(cell.value) for cell in ws[1]]
    header_index = _ensure_asset_headers(headers)

    sources = discover_promoted_option_sources(wb)
    desired = read_option_sheets(wb, sources)
    desired.update(read_model_targets(wb))
    desired.update(read_bodystyle_targets(sources))
    existing_rows = existing_asset_rows(ws, header_index)
    media = build_media_inventory(media_urls)
    classify_coverage = build_coverage_classifier(desired, read_section_coverage_metadata(wb), existing_rows)

    if verify_existing:
        alive = check_existing([row["url"] for row in existing_rows.values() if row.get("url")], timeout, workers)
    else:
        alive = {}

    plan = reconcile(
        desired,
        media,
        existing_rows=existing_rows,
        alive=alive,
        incremental=incremental,
        classify_coverage=classify_coverage,
    )
    plan = replace(plan, section_coverage=build_section_coverage_stats(desired, existing_rows))
    unmatched = sorted(set(media_urls) - plan.used - set(media.unparseable))
    return plan, sources, unmatched, media.unparseable


def apply_sync_plan(wb, *, asset_sheet: str, plan: SyncPlan) -> None:
    if asset_sheet not in wb.sheetnames:
        raise ValueError(f"Sheet {asset_sheet!r} not found.")
    ws = wb[asset_sheet]
    headers = [clean(cell.value) for cell in ws[1]]
    header_index = _ensure_asset_headers(headers)

    for (row_number, field), url in plan.url_writes.items():
        if field in header_index:
            ws.cell(row_number, header_index[field] + 1).value = url

    for insert in plan.inserts:
        row_values: list[Any] = [""] * len(headers)
        row_values[header_index["model_key"]] = insert["model"]
        row_values[header_index["target_type"]] = insert.get("target_type", TARGET_TYPE_OPTION)
        row_values[header_index["target_id"]] = insert["tid"]
        for field, value in insert.get("fields", {"image_url": insert.get("url", "")}).items():
            if field in header_index:
                row_values[header_index[field]] = value
        if "image_alt" in header_index:
            row_values[header_index["image_alt"]] = insert["name"]
        if "hover_image_alt" in header_index and insert.get("fields", {}).get("hover_image_url"):
            row_values[header_index["hover_image_alt"]] = insert["name"]
        if "image_fit" in header_index:
            row_values[header_index["image_fit"]] = NEW_ROW_FIT
        if "image_position" in header_index:
            row_values[header_index["image_position"]] = NEW_ROW_POSITION
        if "hover_image_position" in header_index and insert.get("fields", {}).get("hover_image_url"):
            row_values[header_index["hover_image_position"]] = NEW_ROW_POSITION
        if "active" in header_index:
            row_values[header_index["active"]] = True
        if "notes" in header_index:
            row_values[header_index["notes"]] = NEW_ROW_NOTE
        ws.append(row_values)


def run_sync(
    *,
    workbook_path: Path | str,
    report_dir: Path | str,
    media_urls: Iterable[str],
    apply: bool = False,
    asset_sheet: str = ASSET_SHEET,
    verify_existing: bool = False,
    timeout: float = 10.0,
    workers: int = 16,
    incremental: bool = False,
    media_source: str = "live",
    since_argument: str | None = None,
    resolved_modified_after: str | None = None,
    state_read: bool = False,
    save_fn: Callable[..., Path] = save_workbook_safely,
) -> SyncResult:
    workbook_path = Path(workbook_path)
    report_dir = Path(report_dir)
    media_url_list = list(media_urls)
    loaded_mtime_ns = workbook_path.stat().st_mtime_ns if workbook_path.exists() else None
    backup_path: Path | None = None
    state_written = False

    plan_wb = load_workbook(workbook_path, read_only=not apply, data_only=not apply)
    try:
        plan, sources, unmatched, unparseable = build_sync_plan(
            plan_wb,
            asset_sheet=asset_sheet,
            media_urls=media_url_list,
            verify_existing=verify_existing,
            timeout=timeout,
            workers=workers,
            incremental=incremental,
        )
    finally:
        plan_wb.close()

    report_path, missing_path, unmatched_path, missing_count, broad_missing_count = _write_reports(
        report_dir,
        plan.report,
        unmatched,
        unparseable,
        incremental,
    )
    action_counts = dict(Counter(row["action"] for row in plan.report))
    coverage_summary = build_coverage_summary(plan.report)
    coverage_summary["section_coverage"] = plan.section_coverage

    if apply:
        apply_wb = load_workbook(workbook_path)
        try:
            apply_sync_plan(apply_wb, asset_sheet=asset_sheet, plan=plan)
            backup_path = save_fn(apply_wb, workbook_path, loaded_mtime_ns=loaded_mtime_ns)
        finally:
            apply_wb.close()
        check_wb = load_workbook(workbook_path, read_only=True, data_only=True)
        check_wb.close()
        if since_argument == "auto":
            write_state(report_dir)
            state_written = True

    manifest_path = _write_manifest(
        report_dir=report_dir,
        workbook_path=workbook_path,
        asset_sheet=asset_sheet,
        apply=apply,
        media_source=media_source,
        since_argument=since_argument,
        resolved_modified_after=resolved_modified_after,
        incremental=incremental,
        state_read=state_read,
        state_written=state_written,
        media_url_count=len(media_url_list),
        verify_existing=verify_existing,
        included_sources=sources,
        action_counts=action_counts,
        url_write_count=len(plan.url_writes),
        insert_count=len(plan.inserts),
        unmatched_count=len(unmatched),
        unparseable_count=len(unparseable),
        report_path=report_path,
        missing_path=missing_path,
        missing_count=missing_count,
        broad_missing_count=broad_missing_count,
        coverage_summary=coverage_summary,
        unmatched_path=unmatched_path,
    )

    return SyncResult(
        report_path=report_path,
        missing_path=missing_path,
        unmatched_path=unmatched_path,
        manifest_path=manifest_path,
        url_write_count=len(plan.url_writes),
        insert_count=len(plan.inserts),
        action_counts=action_counts,
        unmatched_count=len(unmatched),
        unparseable_count=len(unparseable),
        backup_path=backup_path,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Report or safely apply asset_map image URL sync from current hosted media inventory.")
    parser.add_argument("--workbook", required=True, type=Path)
    parser.add_argument("--asset-sheet", default=ASSET_SHEET)
    parser.add_argument("--report-dir", required=True, type=Path)
    parser.add_argument("--media-url-list", type=Path, help="Deterministic newline-delimited media URL fixture/list")
    parser.add_argument("--apply", action="store_true", help="Write workbook changes through save_workbook_safely()")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--verify-existing-network", dest="verify_existing", action="store_true", help="Optionally probe existing workbook URLs for dead-link reporting")
    parser.add_argument("--no-verify-existing", dest="verify_existing", action="store_false", help="Deprecated no-op; network verification is off by default")
    parser.add_argument("--since", default=None, metavar="DATE", help="Media modified-after date, or 'auto' for saved cursor")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    state_read = False
    if args.since == "auto":
        modified_after, state_read = read_since_auto(args.report_dir)
    else:
        modified_after = args.since
    if args.media_url_list:
        media_urls = read_media_url_list(args.media_url_list)
        media_source = "media-url-list"
        print(f"Loaded {len(media_urls)} media URLs from {args.media_url_list}")
    else:
        media_source = "live"
        label = f"incremental after {modified_after}" if modified_after else "full"
        print(f"Pulling media [{label}] ...")
        try:
            media_urls = fetch_media(args.timeout, modified_after)
        except WordPressMediaFetchError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"  {len(media_urls)} images under {PATH_FILTER}")

    result = run_sync(
        workbook_path=args.workbook,
        report_dir=args.report_dir,
        media_urls=media_urls,
        apply=args.apply,
        asset_sheet=args.asset_sheet,
        verify_existing=args.verify_existing,
        timeout=args.timeout,
        workers=args.workers,
        incremental=modified_after is not None,
        media_source=media_source,
        since_argument=args.since,
        resolved_modified_after=modified_after,
        state_read=state_read,
    )

    print("\n=== Summary ===")
    for action, count in sorted(result.action_counts.items()):
        print(f"  {action:<30} {count}")
    print(f"  {'unmatched media':<30} {result.unmatched_count}")
    print(f"  {'unparseable files':<30} {result.unparseable_count}")
    print(
        f"\nReports: {result.report_path}\n"
        f"         {result.missing_path}\n"
        f"         {result.unmatched_path}\n"
        f"Manifest: {result.manifest_path}"
    )

    if args.apply:
        print(f"\nAPPLIED: {result.url_write_count} url change(s), {result.insert_count} row insert(s).")
        if result.backup_path:
            print(f"Backup -> {result.backup_path}")
    else:
        print(f"\nDRY RUN -- would write {result.url_write_count} url change(s) and {result.insert_count} new row(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
