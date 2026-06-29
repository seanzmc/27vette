#!/usr/bin/env python3
"""Focused tests for the asset_map sync maintenance command."""

from __future__ import annotations

import subprocess
import sys
import json
import csv
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError

import pytest
from openpyxl import Workbook, load_workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator import asset_map_sync  # noqa: E402


def add_sheet(wb: Workbook, name: str, headers: list[str], rows: list[dict[str, object]]) -> None:
    ws = wb.create_sheet(name)
    ws.append(headers)
    for row in rows:
        ws.append([row.get(header, "") for header in headers])


def make_discovery_workbook() -> Workbook:
    wb = Workbook()
    del wb[wb.sheetnames[0]]
    add_sheet(
        wb,
        "model_registry_promotion",
        ["model_key", "promoted_to_runtime", "active", "display_order"],
        [
            {"model_key": "stingray", "promoted_to_runtime": True, "active": True, "display_order": 1},
            {"model_key": "grand_sport", "promoted_to_runtime": True, "active": True, "display_order": 2},
            {"model_key": "zr1", "promoted_to_runtime": False, "active": False, "display_order": 3},
        ],
    )
    add_sheet(
        wb,
        "model_workbook_sources",
        ["model_key", "source_role", "sheet_name", "active"],
        [
            {"model_key": "stingray", "source_role": "source_option_sheet", "sheet_name": "stingray_options", "active": True},
            {"model_key": "grand_sport", "source_role": "source_option_sheet", "sheet_name": "grandSport_options", "active": True},
            {"model_key": "zr1", "source_role": "source_option_sheet", "sheet_name": "zr1_options", "active": True},
        ],
    )
    option_headers = ["option_id", "rpo", "option_name", "active", "selectable"]
    add_sheet(
        wb,
        "stingray_options",
        option_headers,
        [
            {"option_id": "opt_gba_001", "rpo": "GBA", "option_name": "Black", "active": True, "selectable": True},
            {"option_id": "opt_hidden_001", "rpo": "ZZZ", "option_name": "Hidden", "active": False, "selectable": True},
        ],
    )
    add_sheet(
        wb,
        "grandSport_options",
        option_headers,
        [
            {"option_id": "opt_qe6_001", "rpo": "QE6", "option_name": "Wheel", "active": True, "selectable": True},
        ],
    )
    add_sheet(
        wb,
        "zr1_options",
        option_headers,
        [
            {"option_id": "opt_future_001", "rpo": "FUT", "option_name": "Future", "active": True, "selectable": True},
        ],
    )
    return wb


def make_apply_workbook(path: Path) -> None:
    wb = Workbook()
    del wb[wb.sheetnames[0]]
    add_sheet(
        wb,
        "model_registry_promotion",
        ["model_key", "promoted_to_runtime", "active", "display_order"],
        [{"model_key": "stingray", "promoted_to_runtime": True, "active": True, "display_order": 1}],
    )
    add_sheet(
        wb,
        "model_workbook_sources",
        ["model_key", "source_role", "sheet_name", "active"],
        [{"model_key": "stingray", "source_role": "source_option_sheet", "sheet_name": "stingray_options", "active": True}],
    )
    add_sheet(
        wb,
        "stingray_options",
        ["option_id", "rpo", "option_name", "active", "selectable"],
        [{"option_id": "opt_gba_001", "rpo": "GBA", "option_name": "Black", "active": True, "selectable": True}],
    )
    add_sheet(
        wb,
        "asset_map",
        ["model_key", "target_type", "target_id", "image_url", "image_alt", "image_fit", "image_position", "active", "notes"],
        [],
    )
    wb.save(path)
    wb.close()


class FakeJsonResponse:
    def __init__(self, payload: bytes = b"[]", headers: dict[str, str] | None = None) -> None:
        self.payload = payload
        self.headers = headers or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def make_missing_report_workbook(path: Path) -> None:
    wb = Workbook()
    del wb[wb.sheetnames[0]]
    add_sheet(
        wb,
        "model_registry_promotion",
        ["model_key", "promoted_to_runtime", "active", "display_order"],
        [
            {"model_key": "stingray", "promoted_to_runtime": True, "active": True, "display_order": 1},
            {"model_key": "grand_sport", "promoted_to_runtime": True, "active": True, "display_order": 2},
        ],
    )
    add_sheet(
        wb,
        "model_workbook_sources",
        ["model_key", "source_role", "sheet_name", "active"],
        [
            {"model_key": "stingray", "source_role": "source_option_sheet", "sheet_name": "stingray_options", "active": True},
            {"model_key": "grand_sport", "source_role": "source_option_sheet", "sheet_name": "grandSport_options", "active": True},
        ],
    )
    option_headers = ["option_id", "rpo", "option_name", "section_id", "active", "selectable"]
    add_sheet(
        wb,
        "stingray_options",
        option_headers,
        [
            {"option_id": "opt_gba_001", "rpo": "GBA", "option_name": "Black", "section_id": "sec_paint_001", "active": True, "selectable": True},
            {"option_id": "opt_noimg_001", "rpo": "NIX", "option_name": "No Image", "section_id": "sec_test_001", "active": True, "selectable": True},
            {"option_id": "opt_stx_001", "rpo": "STX", "option_name": "Stripe", "section_id": "sec_stripe_001", "active": True, "selectable": True},
        ],
    )
    add_sheet(
        wb,
        "grandSport_options",
        option_headers,
        [
            {"option_id": "opt_gba_002", "rpo": "GBA", "option_name": "Black GS", "section_id": "sec_paint_001", "active": True, "selectable": True},
        ],
    )
    add_sheet(
        wb,
        "asset_map",
        ["model_key", "target_type", "target_id", "image_url", "image_alt", "image_fit", "image_position", "active", "notes"],
        [
            {
                "model_key": "stingray",
                "target_type": "option",
                "target_id": "opt_gba_001",
                "image_url": "https://example.test/current-gba.png",
                "image_alt": "Black",
                "image_fit": "cover",
                "image_position": "center",
                "active": True,
                "notes": "existing",
            },
        ],
    )
    wb.save(path)
    wb.close()


def test_open_json_sends_browser_like_user_agent(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str | None] = {}

    def fake_urlopen(request, timeout):
        captured["accept"] = request.get_header("Accept")
        captured["user_agent"] = request.get_header("User-agent")
        return FakeJsonResponse(b"[]", {"X-WP-TotalPages": "1"})

    monkeypatch.setattr(asset_map_sync, "urlopen", fake_urlopen)

    payload, headers = asset_map_sync._open_json("https://example.test/wp-json/wp/v2/media", auth_header=None, timeout=1)

    assert payload == []
    assert headers == {"x-wp-totalpages": "1"}
    assert captured["accept"] == "application/json"
    assert captured["user_agent"]
    assert "Mozilla/5.0" in captured["user_agent"]


def test_open_json_preserves_optional_basic_auth_header(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, str | None] = {}
    monkeypatch.setenv("WP_USER", "media-user")
    monkeypatch.setenv("WP_APP_PASSWORD", "app pass")

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        captured["user_agent"] = request.get_header("User-agent")
        return FakeJsonResponse()

    monkeypatch.setattr(asset_map_sync, "urlopen", fake_urlopen)

    asset_map_sync._open_json(
        "https://example.test/wp-json/wp/v2/media",
        auth_header=asset_map_sync._auth_header_from_env(),
        timeout=1,
    )

    assert captured["authorization"]
    assert captured["authorization"].startswith("Basic ")
    assert captured["user_agent"]


def test_fetch_media_403_mentions_media_url_list_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def blocked(url, *, auth_header, timeout):
        raise HTTPError(url, 403, "Forbidden", Message(), None)

    monkeypatch.setattr(asset_map_sync, "_open_json", blocked)

    with pytest.raises(Exception) as excinfo:
        asset_map_sync.fetch_media(timeout=1)

    message = str(excinfo.value)
    assert "HTTP 403" in message
    assert "--media-url-list" in message


def test_parse_media_requires_hyphen_for_model_prefix() -> None:
    assert asset_map_sync.parse_media("https://example.test/imgi_47_379.png") == (None, "379", True)
    assert asset_map_sync.parse_media("https://example.test/h-stx.png") == ("z06", "stx", True)
    assert asset_map_sync.parse_media("https://example.test/hzp.png") == (None, "hzp", True)
    assert asset_map_sync.parse_media("https://example.test/c-qe6_v1.png") == ("stingray", "qe6", True)
    assert asset_map_sync.parse_media("https://example.test/27vette/paint/gba.png") == (None, "gba", True)
    assert asset_map_sync.parse_media("https://example.test/27vette/paint/c-gba.png") == ("stingray", "gba", True)


def test_parse_model_and_bodystyle_media_names() -> None:
    assert asset_map_sync.parse_model_media("https://example.test/27vette/grandsport.png") == ("grand_sport", "grandSport")
    assert asset_map_sync.parse_bodystyle_media("https://example.test/27vette/c07-1.png") == (
        "stingray",
        "body_style__coupe",
        "image_url",
    )
    assert asset_map_sync.parse_bodystyle_media("https://example.test/27vette/h67-2.png") == (
        "z06",
        "body_style__convertible",
        "hover_image_url",
    )


def test_discovery_uses_promoted_runtime_models_not_inactive_future_sheets() -> None:
    wb = make_discovery_workbook()

    sources = asset_map_sync.discover_promoted_option_sources(wb)
    desired = asset_map_sync.read_option_sheets(wb, sources)

    assert sources == {"stingray": "stingray_options", "grand_sport": "grandSport_options"}
    assert sorted(desired) == [("grand_sport", "opt_qe6_001"), ("stingray", "opt_gba_001")]
    assert ("zr1", "opt_future_001") not in desired


def test_reconcile_uses_bare_media_as_shared_fallback_after_model_prefixed_media() -> None:
    desired = {
        ("stingray", "opt_gba_001"): {"rpo": "gba", "name": "Black"},
        ("grand_sport", "opt_gba_001"): {"rpo": "gba", "name": "Black"},
        ("z06", "opt_stx_001"): {"rpo": "stx", "name": "Stripe"},
        ("stingray", "opt_noimg_001"): {"rpo": "nix", "name": "No Image"},
    }
    exact, bare, _ = asset_map_sync.build_media_index(
        [
            "https://example.test/27vette/paint/gba.png",
            "https://example.test/27vette/stripes/stx.png",
            "https://example.test/27vette/z06/h-stx.png",
        ]
    )

    report, url_writes, inserts, status, _used = asset_map_sync.reconcile(
        desired,
        exact,
        bare,
        existing_rows={},
        alive={},
        incremental=False,
    )

    actions = {(row["model_key"], row["target_id"]): row["action"] for row in report}
    sources = {(row["model_key"], row["target_id"]): row["candidate_source"] for row in report}
    urls = {(row["model_key"], row["target_id"]): row["new_url"] for row in report}
    assert actions[("stingray", "opt_gba_001")] == "insert_filled"
    assert actions[("grand_sport", "opt_gba_001")] == "insert_filled"
    assert actions[("z06", "opt_stx_001")] == "insert_filled"
    assert actions[("stingray", "opt_noimg_001")] == "flag_missing"
    assert sources[("stingray", "opt_gba_001")] == "bare-shared"
    assert sources[("grand_sport", "opt_gba_001")] == "bare-shared"
    assert sources[("z06", "opt_stx_001")] == "prefixed"
    assert urls[("stingray", "opt_gba_001")] == "https://example.test/27vette/paint/gba.png"
    assert urls[("grand_sport", "opt_gba_001")] == "https://example.test/27vette/paint/gba.png"
    assert urls[("z06", "opt_stx_001")] == "https://example.test/27vette/z06/h-stx.png"
    assert [(row["model"], row["tid"], row["url"], row["target_type"]) for row in inserts] == [
        ("stingray", "opt_gba_001", "https://example.test/27vette/paint/gba.png", "option"),
        ("grand_sport", "opt_gba_001", "https://example.test/27vette/paint/gba.png", "option"),
        ("z06", "opt_stx_001", "https://example.test/27vette/z06/h-stx.png", "option"),
    ]
    assert url_writes == {}
    assert status == {}


def test_reconcile_flags_duplicate_bare_media_for_same_rpo_as_ambiguous() -> None:
    desired = {
        ("stingray", "opt_gba_001"): {"rpo": "gba", "name": "Black"},
        ("grand_sport", "opt_gba_001"): {"rpo": "gba", "name": "Black"},
    }
    exact, bare, _ = asset_map_sync.build_media_index(
        [
            "https://example.test/27vette/paint/gba.png",
            "https://example.test/27vette/exterior/gba.png",
        ]
    )

    report, url_writes, inserts, status, _used = asset_map_sync.reconcile(
        desired,
        exact,
        bare,
        existing_rows={},
        alive={},
        incremental=False,
    )

    assert {row["action"] for row in report} == {"flag_ambiguous"}
    assert {row["candidate_source"] for row in report} == {"bare-ambiguous"}
    assert all("multiple bare files" in row["note"] for row in report)
    assert url_writes == {}
    assert inserts == []
    assert status == {}


def test_reconcile_replaces_existing_url_when_canonical_media_inventory_differs() -> None:
    desired = {
        ("stingray", "opt_gba_001"): {"target_type": "option", "rpo": "gba", "name": "Black"},
    }
    media = asset_map_sync.build_media_inventory(["https://example.test/27vette/paint/c-gba-new.png"])

    report, url_writes, inserts, status, _used = asset_map_sync.reconcile(
        desired,
        media,
        existing_rows={
            ("stingray", "opt_gba_001"): {
                "row": 12,
                "target_type": "option",
                "url": "https://example.test/27vette/paint/c-gba-old.png",
            }
        },
        alive={"https://example.test/27vette/paint/c-gba-old.png": True},
        incremental=False,
    )

    assert report[0]["action"] == "replace_canonical"
    assert report[0]["new_url"] == "https://example.test/27vette/paint/c-gba-new.png"
    assert url_writes == {(12, "image_url"): "https://example.test/27vette/paint/c-gba-new.png"}
    assert inserts == []
    assert status == {12: "ok"}


def test_reconcile_inserts_context_choice_base_and_hover_media_from_naming_pair() -> None:
    desired = {
        ("stingray", "body_style__coupe"): {
            "target_type": "context_choice",
            "rpo": "",
            "name": "Coupe",
            "source_sheet": "generated_body_style_context",
        }
    }
    media = asset_map_sync.build_media_inventory(
        [
            "https://example.test/27vette/body/c07-1.png",
            "https://example.test/27vette/body/c07-2.png",
        ]
    )

    report, url_writes, inserts, status, _used = asset_map_sync.reconcile(
        desired,
        media,
        existing_rows={},
        alive={},
        incremental=False,
    )

    assert report[0]["action"] == "insert_filled"
    assert report[0]["target_type"] == "context_choice"
    assert inserts == [
        {
            "model": "stingray",
            "target_type": "context_choice",
            "tid": "body_style__coupe",
            "rpo": "",
            "name": "Coupe",
            "fields": {
                "image_url": "https://example.test/27vette/body/c07-1.png",
                "hover_image_url": "https://example.test/27vette/body/c07-2.png",
            },
            "url": "https://example.test/27vette/body/c07-1.png",
            "status": "ok",
            "source_sheet": "generated_body_style_context",
        }
    ]
    assert url_writes == {}
    assert status == {}


def test_apply_uses_injected_safe_save_and_inserts_confident_candidate(tmp_path: Path) -> None:
    workbook_path = tmp_path / "sync.xlsx"
    make_apply_workbook(workbook_path)
    report_dir = tmp_path / "reports"
    fixture = ROOT / "tests" / "fixtures" / "asset-map-sync-media-urls.txt"
    calls: list[tuple[Path, int | None]] = []

    def fake_safe_save(wb, path, *, loaded_mtime_ns=None):
        calls.append((Path(path), loaded_mtime_ns))
        wb.save(path)
        return tmp_path / "backup.xlsx"

    result = asset_map_sync.run_sync(
        workbook_path=workbook_path,
        report_dir=report_dir,
        media_urls=asset_map_sync.read_media_url_list(fixture),
        apply=True,
        verify_existing=False,
        save_fn=fake_safe_save,
    )

    assert result.url_write_count == 0
    assert result.insert_count == 1
    assert calls and calls[0][0] == workbook_path and calls[0][1] is not None
    wb = load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        rows = list(wb["asset_map"].iter_rows(min_row=2, values_only=True))
    finally:
        wb.close()
    assert rows[0][:9] == (
        "stingray",
        "option",
        "opt_gba_001",
        "https://example.test/c-gba.png",
        "Black",
        "cover",
        "center",
        True,
        "auto-seeded",
    )
    assert (report_dir / "asset_map_sync_report.csv").exists()
    assert (report_dir / "asset_map_unmatched_media.csv").exists()


def test_report_manifest_records_source_inventory_and_counts(tmp_path: Path) -> None:
    workbook_path = tmp_path / "sync.xlsx"
    make_apply_workbook(workbook_path)
    report_dir = tmp_path / "reports"
    fixture = ROOT / "tests" / "fixtures" / "asset-map-sync-media-urls.txt"

    result = asset_map_sync.run_sync(
        workbook_path=workbook_path,
        report_dir=report_dir,
        media_urls=asset_map_sync.read_media_url_list(fixture),
        apply=False,
        verify_existing=False,
        media_source="media-url-list",
        since_argument=None,
        resolved_modified_after=None,
        state_read=False,
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    required = {
        "version",
        "generated_at_utc",
        "workbook_path",
        "asset_sheet",
        "apply",
        "media_source",
        "since_argument",
        "resolved_modified_after",
        "incremental",
        "state_path",
        "state_read",
        "state_written",
        "media_url_count",
        "verify_existing",
        "included_sources",
        "action_counts",
        "url_write_count",
        "insert_count",
        "unmatched_count",
        "unparseable_count",
        "report_path",
        "unmatched_path",
    }
    assert required <= set(manifest)
    assert manifest["apply"] is False
    assert manifest["media_source"] == "media-url-list"
    assert manifest["verify_existing"] is False
    assert manifest["included_sources"] == [{"model_key": "stingray", "option_sheet": "stingray_options"}]
    assert manifest["action_counts"] == {"flag_missing": 3, "insert_filled": 1}
    assert manifest["url_write_count"] == 0
    assert manifest["insert_count"] == 1
    assert manifest["media_url_count"] == len(asset_map_sync.read_media_url_list(fixture))
    assert Path(manifest["report_path"]).name == "asset_map_sync_report.csv"
    assert Path(manifest["unmatched_path"]).name == "asset_map_unmatched_media.csv"
    assert result.manifest_path == report_dir / "asset_map_sync_manifest.json"


def test_missing_images_artifact_written_and_manifested(tmp_path: Path) -> None:
    workbook_path = tmp_path / "missing-report.xlsx"
    make_missing_report_workbook(workbook_path)
    report_dir = tmp_path / "reports"

    result = asset_map_sync.run_sync(
        workbook_path=workbook_path,
        report_dir=report_dir,
        media_urls=[
            "https://example.test/gba.png",
            "https://example.test/c-stx.png",
            "https://example.test/abc.png",
        ],
        apply=False,
        verify_existing=False,
        media_source="media-url-list",
    )

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    missing_path = report_dir / "asset_map_missing_images.csv"
    assert result.missing_path == missing_path
    assert Path(manifest["missing_images_path"]) == missing_path

    rows = list(csv.DictReader(missing_path.open(encoding="utf-8")))
    assert manifest["missing_images_count"] == len(rows) == 7
    assert ("opt_noimg_001", "flag_missing") in {(row["target_id"], row["action"]) for row in rows}
    no_image = next(row for row in rows if row["target_id"] == "opt_noimg_001")
    assert no_image["section_id"] == "sec_test_001"
    assert no_image["option_name"] == "No Image"


def test_missing_images_artifact_excludes_keep_insert_and_unmatched(tmp_path: Path) -> None:
    workbook_path = tmp_path / "missing-filter.xlsx"
    make_missing_report_workbook(workbook_path)
    report_dir = tmp_path / "reports"

    result = asset_map_sync.run_sync(
        workbook_path=workbook_path,
        report_dir=report_dir,
        media_urls=[
            "https://example.test/gba.png",
            "https://example.test/c-stx.png",
            "https://example.test/abc.png",
        ],
        apply=False,
        verify_existing=False,
        media_source="media-url-list",
    )

    rows = list(csv.DictReader(result.missing_path.open(encoding="utf-8")))
    assert {row["action"] for row in rows} <= {"flag_missing", "flag_ambiguous", "flag_dead_no_match"}
    assert "opt_gba_001" not in {row["target_id"] for row in rows}
    assert "opt_stx_001" not in {row["target_id"] for row in rows}
    unmatched_rows = list(csv.DictReader(result.unmatched_path.open(encoding="utf-8")))
    assert {row["parsed_rpo"] for row in unmatched_rows} == {"abc"}
    assert "abc" not in {row["rpo"] for row in rows}


def test_dry_run_reports_without_saving_workbook_rows_or_state(tmp_path: Path) -> None:
    workbook_path = tmp_path / "sync.xlsx"
    make_apply_workbook(workbook_path)
    report_dir = tmp_path / "reports"
    fixture = ROOT / "tests" / "fixtures" / "asset-map-sync-media-urls.txt"

    result = asset_map_sync.run_sync(
        workbook_path=workbook_path,
        report_dir=report_dir,
        media_urls=asset_map_sync.read_media_url_list(fixture),
        apply=False,
        verify_existing=False,
        media_source="media-url-list",
        since_argument="auto",
        resolved_modified_after=None,
        state_read=False,
    )

    wb = load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        rows = list(wb["asset_map"].iter_rows(min_row=2, values_only=True))
    finally:
        wb.close()
    assert rows == []
    assert result.insert_count == 1
    assert not asset_map_sync.state_path(report_dir).exists()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["state_read"] is False
    assert manifest["state_written"] is False


def test_apply_state_written_only_after_safe_save_success(tmp_path: Path) -> None:
    fixture = ROOT / "tests" / "fixtures" / "asset-map-sync-media-urls.txt"

    success_workbook = tmp_path / "success.xlsx"
    make_apply_workbook(success_workbook)
    success_dir = tmp_path / "success-report"

    def fake_safe_save(wb, path, *, loaded_mtime_ns=None):
        wb.save(path)
        return tmp_path / "backup.xlsx"

    result = asset_map_sync.run_sync(
        workbook_path=success_workbook,
        report_dir=success_dir,
        media_urls=asset_map_sync.read_media_url_list(fixture),
        apply=True,
        verify_existing=False,
        save_fn=fake_safe_save,
        since_argument="auto",
        resolved_modified_after="2026-06-26T00:00:00",
        state_read=True,
        media_source="media-url-list",
    )

    assert asset_map_sync.state_path(success_dir).exists()
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    assert manifest["state_read"] is True
    assert manifest["state_written"] is True

    failed_workbook = tmp_path / "failed.xlsx"
    make_apply_workbook(failed_workbook)
    failed_dir = tmp_path / "failed-report"

    def failing_safe_save(wb, path, *, loaded_mtime_ns=None):
        raise RuntimeError("save failed")

    with pytest.raises(RuntimeError, match="save failed"):
        asset_map_sync.run_sync(
            workbook_path=failed_workbook,
            report_dir=failed_dir,
            media_urls=asset_map_sync.read_media_url_list(fixture),
            apply=True,
            verify_existing=False,
            save_fn=failing_safe_save,
            since_argument="auto",
            resolved_modified_after="2026-06-26T00:00:00",
            state_read=True,
            media_source="media-url-list",
        )

    assert not asset_map_sync.state_path(failed_dir).exists()


def test_cli_help_works_without_requests_dependency() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "sync_asset_map.py"), "--help"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout
    assert "--media-url-list" in completed.stdout
    assert "--apply" in completed.stdout
    assert "--status-col" not in completed.stdout
    assert "--deactivate-stale" not in completed.stdout
    assert "--seed-blank-missing" not in completed.stdout


def test_cli_rejects_unsupported_schema_and_lifecycle_flags(tmp_path: Path) -> None:
    for flag in ["--status-col", "--deactivate-stale", "--seed-blank-missing"]:
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "sync_asset_map.py"),
                "--workbook",
                str(tmp_path / "missing.xlsx"),
                "--report-dir",
                str(tmp_path / "reports"),
                "--media-url-list",
                str(ROOT / "tests" / "fixtures" / "asset-map-sync-media-urls.txt"),
                flag,
            ],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )

        assert completed.returncode != 0
        assert flag in completed.stdout


def test_legacy_entrypoint_no_longer_contains_direct_workbook_save() -> None:
    legacy = (ROOT / "asset_map-Sync" / "asset_map_sync.py").read_text(encoding="utf-8")

    assert "wb.save(args.workbook)" not in legacy
    assert "scripts/sync_asset_map.py" in legacy or "asset_map_sync" not in legacy
