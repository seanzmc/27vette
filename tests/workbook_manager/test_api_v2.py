from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import main


def test_create_app_supports_an_isolated_database(imported_db_path: Path):
    create_app = getattr(main, "create_app", None)
    assert callable(create_app)
    with TestClient(create_app(imported_db_path)) as client:
        response = client.get("/api/models")
    assert response.status_code == 200
    assert {model["model_key"] for model in response.json()["models"]} >= {
        "stingray",
        "grand_sport",
        "z06",
    }


def test_status_exposes_the_backend_owned_workbook_path(client: TestClient):
    response = client.get("/api/status")
    assert response.status_code == 200
    workbook = response.json()["workbook"]
    assert Path(workbook["workbook_path"]).name == "stingray_master.xlsx"


@pytest.fixture
def client(imported_db_path: Path):
    with TestClient(main.create_app(imported_db_path)) as test_client:
        yield test_client


def test_model_tables_expose_physical_name_and_lineage(client: TestClient):
    response = client.get("/api/models/grand_sport/tables")
    assert response.status_code == 200
    options = next(
        table for table in response.json()["tables"]
        if table["role"] == "options"
    )
    assert options["sql_table"] == "grand_sport_options"
    assert options["source_sheets"] == ["grandSport_options"]
    assert options["mapping_type"] == "exact"
    assert options["count"] == 241


def test_arbitrary_model_or_role_is_rejected(client: TestClient):
    assert client.get("/api/models/bad/tables").status_code == 404
    assert (
        client.get("/api/models/stingray/tables/sqlite_master").status_code
        == 404
    )


def test_model_table_records_retain_registry_lineage(client: TestClient):
    response = client.get(
        "/api/models/grand_sport/tables/options?limit=1"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sql_table"] == "grand_sport_options"
    assert body["source_sheets"] == ["grandSport_options"]
    assert body["key"] == ["option_id"]
    assert len(body["records"]) == 1


def test_import_run_findings_and_mappings_are_typed(client: TestClient):
    run = client.get("/api/imports/1")
    assert run.status_code == 200
    assert run.json()["status"] == "validated"
    assert isinstance(run.json()["row_counts"], dict)

    findings = client.get("/api/imports/1/findings")
    assert findings.status_code == 200
    finding = findings.json()["findings"][0]
    assert {"source_sheet", "source_row", "source_column", "code"} <= set(finding)

    mappings = client.get("/api/schema/mappings")
    assert mappings.status_code == 200
    mapping = mappings.json()["mappings"][0]
    assert {
        "source_sheet",
        "source_column",
        "model_key",
        "sql_table",
        "sql_column",
        "transform_type",
        "contract_status",
    } <= set(mapping)


def test_variants_and_runtime_are_model_scoped(client: TestClient):
    variants = client.get("/api/models/z06/variants")
    assert variants.status_code == 200
    assert variants.json()["model_key"] == "z06"
    assert variants.json()["variants"]
    assert all(
        variant["model_key"] == "z06"
        for variant in variants.json()["variants"]
    )

    runtime = client.get("/api/models/z06/runtime")
    assert runtime.status_code == 200
    body = runtime.json()
    assert body["model_key"] == "z06"
    assert body["steps"]
    assert body["section_presentation"]
    assert body["context_sections"]
    assert body["context_choices"]
    assert body["summary_sections"]
    assert body["step_summary_map"]


def test_decision_finding_has_actionable_source_detail(
    client: TestClient, broken_fk_workbook: Path
):
    response = client.post(
        "/api/imports", json={"workbook_path": str(broken_fk_workbook)}
    )
    assert response.status_code == 409
    finding = response.json()["detail"]["findings"][0]
    assert {"source_sheet", "source_row", "source_column", "code"} <= set(finding)


def test_typed_stage_and_domain_error_shapes(client: TestClient):
    row = client.get(
        "/api/models/stingray/tables/options?search=Z51&limit=1"
    ).json()["records"][0]
    staged = client.post("/api/changes", json={
        "model_key": "stingray",
        "table_role": "options",
        "op": "update",
        "key": {"option_id": row["option_id"]},
        "record": {"price": row["price"] + 1},
    })
    assert staged.status_code == 200
    assert staged.json()["model_key"] == "stingray"
    assert staged.json()["table_role"] == "options"
    assert client.post("/api/changes/validate").json()["ok"]
    client.delete(f"/api/changes/{staged.json()['id']}")

    invalid = client.post("/api/changes", json={
        "model_key": "stingray",
        "table_role": "options",
        "op": "add",
        "key": {"option_id": "opt_api_bad"},
        "record": {"option_id": "opt_api_bad", "price": "bad"},
    })
    assert invalid.status_code == 422
    assert invalid.json()["detail"]["errors"][0]["model_key"] == "stingray"
    assert invalid.json()["detail"]["errors"][0]["table_role"] == "options"

    invalid_update = client.post("/api/changes", json={
        "model_key": "stingray",
        "table_role": "options",
        "op": "update",
        "key": {"option_id": row["option_id"]},
        "record": {"price": "bad"},
    })
    assert invalid_update.status_code == 422
    error = invalid_update.json()["detail"]["errors"][0]
    assert error["source_sheet"] == "stingray_options"
    assert isinstance(error["source_row"], int)
    assert error["source_column"] == "price"


def test_sync_decision_blocker_is_http_409(client: TestClient, monkeypatch):
    monkeypatch.setattr(
        main.syncmod,
        "sync_workbook",
        lambda *args, **kwargs: {
            "ok": False,
            "status": "stale_source",
            "errors": ["workbook changed"],
        },
    )
    response = client.post("/api/sync", json={})
    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "stale_source"


def test_sync_dry_run_preserves_typed_review_fields(
    client: TestClient, monkeypatch
):
    monkeypatch.setattr(
        main.syncmod,
        "sync_workbook",
        lambda *args, **kwargs: {
            "ok": True,
            "status": "validated",
            "errors": [],
            "warnings": [],
            "skipped": [],
            "workbookMtimeNs": "1784215687760284347",
            "workbookSha256": "abc123",
            "opCount": 2,
            "sheets": ["stingray_options"],
            "gateReminders": ["run focused gates"],
        },
    )
    response = client.post("/api/sync", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["workbookMtimeNs"] == "1784215687760284347"
    assert body["workbookSha256"] == "abc123"
    assert body["opCount"] == 2
    assert body["sheets"] == ["stingray_options"]


def test_primary_routes_publish_named_response_contracts(client: TestClient):
    schema = client.get("/openapi.json").json()
    components = schema["components"]["schemas"]
    assert {
        "ImportReportOut",
        "FindingOut",
        "SchemaMappingOut",
        "ModelTableOut",
        "ModelRuntimeOut",
    } <= set(components)
    for path in (
        "/api/imports",
        "/api/imports/{import_run_id}",
        "/api/imports/{import_run_id}/findings",
        "/api/schema/mappings",
        "/api/models/{model_key}/tables",
        "/api/models/{model_key}/variants",
        "/api/models/{model_key}/runtime",
        "/api/changes",
        "/api/changes/validate",
        "/api/changes/commit",
        "/api/history",
        "/api/sync",
        "/api/export",
        "/api/backup",
    ):
        assert path in schema["paths"]


def test_removed_transitional_routes_are_absent_and_return_404(
    client: TestClient,
):
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/api/import" not in paths
    assert "/api/models/{model_key}/collections" not in paths
    assert "/api/records/{table_role}" not in paths
    assert "/api/records/{table_role}/schema" not in paths
    assert "/api/records/{table_role}/dependencies" not in paths

    assert client.post("/api/import").status_code == 404
    assert client.get("/api/models/stingray/collections").status_code == 404
    assert client.get("/api/records/options?model=stingray").status_code == 404
    assert (
        client.get("/api/records/options/schema?model=stingray").status_code
        == 404
    )
    assert (
        client.post(
            "/api/records/options/dependencies",
            json={"model_id": "stingray", "key": {"option_id": "Z51"}},
        ).status_code
        == 404
    )

    registered_paths = {
        route.path for route in client.app.routes if hasattr(route, "path")
    }
    assert "/api/import" not in registered_paths
    assert "/api/models/{model_key}/collections" not in registered_paths
    assert not any(path.startswith("/api/records/") for path in registered_paths)


def test_openapi_contracts_are_exact_and_document_domain_errors(
    client: TestClient,
):
    schema = client.get("/openapi.json").json()
    components = schema["components"]["schemas"]

    issue = components["ValidationIssue"]
    assert {
        "model_key",
        "table_role",
        "sql_table",
        "field",
        "entity_key",
        "message",
        "source_sheet",
        "source_row",
        "source_column",
    } <= set(issue["required"])
    assert {"code", "severity", "status"} <= set(issue["properties"])

    assert components["ModelVariantsOut"]["properties"]["variants"]["items"][
        "$ref"
    ].endswith("/VariantOut")
    runtime = components["ModelRuntimeOut"]["properties"]
    assert runtime["steps"]["items"]["$ref"].endswith("/RuntimeStepOut")
    assert runtime["context_choices"]["items"]["$ref"].endswith(
        "/RuntimeContextChoiceOut"
    )
    assert components["ValidationOut"]["properties"]["results"]["items"][
        "$ref"
    ].endswith("/ValidationResultOut")
    assert {
        "workbookMtimeNs",
        "workbookSha256",
        "opCount",
        "warnings",
        "skipped",
    } <= set(components["SyncOut"]["properties"])
    assert components["HistoryOut"]["properties"]["history"]["items"][
        "$ref"
    ].endswith("/HistoryEntryOut")

    paths = schema["paths"]
    assert paths["/api/models"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]["$ref"].endswith("/ModelsOut")
    schema_route = paths[
        "/api/models/{model_key}/tables/{table_role}/schema"
    ]["get"]
    assert schema_route["responses"]["200"]["content"]["application/json"][
        "schema"
    ]["$ref"].endswith("/TableSchemaOut")
    for path, contract in (
        ("/api/sync", "SyncOut"),
        ("/api/export", "ExportOut"),
        ("/api/backup", "BackupOut"),
    ):
        assert paths[path]["post"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]["$ref"].endswith(f"/{contract}")
    for path, method, statuses in (
        ("/api/imports", "post", {404, 409, 422}),
        ("/api/changes", "post", {404, 422}),
        ("/api/changes/{change_id}", "delete", {404, 422}),
        ("/api/changes/commit", "post", {409, 422}),
        ("/api/history", "get", {404, 422}),
        ("/api/sync", "post", {409, 422}),
    ):
        responses = paths[path][method]["responses"]
        for status in statuses:
            response_schema = responses[str(status)]["content"][
                "application/json"
            ]["schema"]
            assert "$ref" in response_schema
            assert not response_schema["$ref"].endswith(
                "/HTTPValidationError"
            )


def test_unknown_resources_and_missing_change_return_404(client: TestClient):
    payload = {
        "model_key": "stingray",
        "table_role": "sqlite_master",
        "op": "add",
        "key": {"id": "bad"},
        "record": {"id": "bad"},
    }
    assert client.post("/api/changes", json=payload).status_code == 404
    payload["model_key"] = "bad"
    payload["table_role"] = "options"
    assert client.post("/api/changes", json=payload).status_code == 404
    assert client.get(
        "/api/history?model_key=stingray&table_role=sqlite_master"
    ).status_code == 404
    assert client.get("/api/history?model_key=bad").status_code == 404
    assert client.delete("/api/changes/999999999").status_code == 404


def test_commit_invalid_batch_is_422_and_constraint_conflict_is_409(
    client: TestClient, imported_db_path: Path, monkeypatch
):
    row = client.get(
        "/api/models/stingray/tables/options?search=Z51&limit=1"
    ).json()["records"][0]
    staged = client.post("/api/changes", json={
        "model_key": "stingray",
        "table_role": "options",
        "op": "update",
        "key": {"option_id": row["option_id"]},
        "record": {"price": row["price"] + 1},
    }).json()
    corrupted = dict(staged["new"])
    corrupted["option_name"] = ""
    raw = sqlite3.connect(imported_db_path)
    raw.execute(
        "UPDATE pending_changes SET new_json=? WHERE id=?",
        (json.dumps(corrupted), staged["id"]),
    )
    raw.commit()
    raw.close()

    invalid = client.post("/api/changes/commit", json={"actor": "api-test"})
    assert invalid.status_code == 422
    error = invalid.json()["detail"]["errors"][0]
    assert error["model_key"] == "stingray"
    assert error["table_role"] == "options"
    assert error["source_sheet"] == "stingray_options"
    assert error["source_column"] == "option_name"
    client.delete(f"/api/changes/{staged['id']}")

    monkeypatch.setattr(
        main.staging,
        "commit_staged",
        lambda *args, **kwargs: {
            "ok": False,
            "status": "constraint_failed",
            "committed": 0,
            "validation": {"ok": True, "results": []},
            "errors": ["database constraint rejected the batch"],
        },
    )
    conflict = client.post("/api/changes/commit", json={})
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["status"] == "constraint_failed"


def test_commit_and_history_use_exact_typed_payloads(client: TestClient):
    row = client.get(
        "/api/models/stingray/tables/options?search=Z51&limit=1"
    ).json()["records"][0]
    staged = client.post("/api/changes", json={
        "model_key": "stingray",
        "table_role": "options",
        "op": "update",
        "key": {"option_id": row["option_id"]},
        "record": {"price": row["price"] + 1},
    })
    assert staged.status_code == 200
    committed = client.post(
        "/api/changes/commit", json={"actor": "typed-api-test"}
    )
    assert committed.status_code == 200
    assert committed.json()["status"] == "committed"
    assert committed.json()["validation"]["ok"]

    history = client.get(
        "/api/history?model_key=stingray&table_role=options"
    )
    assert history.status_code == 200
    item = history.json()["history"][0]
    assert item["actor"] == "typed-api-test"
    assert item["model_key"] == "stingray"
    assert item["table_role"] == "options"
    assert item["old"]["option_id"] == row["option_id"]
    assert item["new"]["price"] == row["price"] + 1
