from __future__ import annotations

import json
from pathlib import Path
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app import main


def _rewrite_as_prior_canonical_database(database_path: Path) -> None:
    conn = sqlite3.connect(database_path)
    try:
        conn.execute("DROP INDEX schema_mapping_null_safe_unique")
        conn.execute("ALTER TABLE schema_mapping RENAME TO old_schema_mapping")
        conn.execute(
            "CREATE TABLE schema_mapping ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "source_sheet TEXT NOT NULL,"
            "source_column TEXT NOT NULL,"
            "model_key TEXT REFERENCES models(model_key),"
            "source_role TEXT NOT NULL DEFAULT '',"
            "sql_table TEXT NOT NULL,"
            "sql_column TEXT NOT NULL,"
            "transform_type TEXT NOT NULL,"
            "transform_parameters_json TEXT NOT NULL DEFAULT '{}',"
            "contract_status TEXT NOT NULL,"
            "notes TEXT NOT NULL DEFAULT '',"
            "UNIQUE(source_sheet, source_column, model_key, sql_table, sql_column)"
            ")"
        )
        conn.execute(
            "INSERT INTO schema_mapping("
            "id, source_sheet, source_column, model_key, source_role, sql_table, "
            "sql_column, transform_type, transform_parameters_json, "
            "contract_status, notes) "
            "SELECT id, source_sheet, source_column, model_key, '', sql_table, "
            "sql_column, transform_type, transform_parameters_json, 'mapped', '' "
            "FROM old_schema_mapping"
        )
        conn.execute("DROP TABLE old_schema_mapping")
        conn.execute(
            "CREATE UNIQUE INDEX schema_mapping_null_safe_unique ON "
            "schema_mapping(source_sheet, source_column, "
            "COALESCE(model_key, '__27vette_global_schema_mapping__'), "
            "sql_table, sql_column)"
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture
def prior_canonical_db_path(imported_db_path: Path) -> Path:
    _rewrite_as_prior_canonical_database(imported_db_path)
    return imported_db_path


@pytest.fixture
def prior_client(prior_canonical_db_path: Path):
    with TestClient(main.create_app(prior_canonical_db_path)) as test_client:
        yield test_client


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
    assert "/api/structure/{model_key}" not in paths

    assert client.post("/api/import").status_code == 404
    assert client.get("/api/models/stingray/collections").status_code == 404
    assert client.get("/api/structure/stingray").status_code == 404
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
    assert "/api/structure/{model_key}" not in registered_paths


def test_dependencies_route_has_explicit_request_and_response_contracts(
    client: TestClient,
):
    operation = client.get("/openapi.json").json()["paths"][
        "/api/models/{model_key}/tables/{table_role}/dependencies"
    ]["post"]
    request_schema = operation["requestBody"]["content"][
        "application/json"
    ]["schema"]
    response_schema = operation["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert request_schema["$ref"].endswith("/DependenciesRequest")
    assert response_schema["$ref"].endswith("/DependenciesOut")


def test_stale_commit_is_typed_http_409(
    client: TestClient, imported_db_path: Path
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
    })
    assert staged.status_code == 200
    external = sqlite3.connect(imported_db_path)
    external.execute(
        "UPDATE stingray_options SET price=99 WHERE option_id=?",
        (row["option_id"],),
    )
    external.commit()
    external.close()

    response = client.post("/api/changes/commit", json={"actor": "race-api"})

    assert response.status_code == 409
    assert response.json()["detail"]["status"] == "stale_conflict"
    assert response.json()["detail"]["committed"] == 0


def test_malformed_workbook_import_is_typed_409_and_reopens_database(
    client: TestClient, imported_db_path: Path, tmp_path
):
    malformed = tmp_path / "malformed-api.xlsx"
    malformed.write_text("not a workbook", encoding="utf-8")
    before = imported_db_path.read_bytes()

    response = client.post(
        "/api/imports", json={"workbook_path": str(malformed)}
    )

    assert response.status_code == 409
    finding = response.json()["detail"]["findings"][0]
    assert finding["code"] == "workbook_source_invalid"
    assert finding["value"] == str(malformed)
    assert imported_db_path.read_bytes() == before
    assert client.get("/api/models").status_code == 200


@pytest.mark.parametrize(
    "fixture_name",
    ("corrupt_content_types_workbook", "corrupt_workbook_xml_workbook"),
)
def test_corrupt_xml_workbook_import_is_typed_409_and_reopens_database(
    client: TestClient, imported_db_path: Path, request, fixture_name
):
    workbook = request.getfixturevalue(fixture_name)
    before = imported_db_path.read_bytes()

    response = client.post(
        "/api/imports", json={"workbook_path": str(workbook)}
    )

    assert response.status_code == 409
    finding = response.json()["detail"]["findings"][0]
    assert finding["code"] == "workbook_source_invalid"
    assert finding["value"] == str(workbook)
    assert imported_db_path.read_bytes() == before
    assert client.get("/api/models").status_code == 200


def _assert_reimport_required(response):
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["code"] == "database_reimport_required"
    assert detail["compatible"] is False
    assert detail["action"] == "POST /api/imports"
    assert "validated re-import" in detail["message"]


def test_prior_canonical_database_exposes_status_but_gates_canonical_routes(
    prior_client: TestClient,
    prior_canonical_db_path: Path,
):
    status = prior_client.get("/api/status")
    assert status.status_code == 200
    body = status.json()
    assert body["database"]["compatible"] is False
    assert body["database"]["code"] == "database_reimport_required"
    assert body["database"]["action"] == "POST /api/imports"
    assert body["last_import"] is None
    raw = sqlite3.connect(prior_canonical_db_path)
    try:
        statuses = {
            row[0]
            for row in raw.execute(
                "SELECT DISTINCT contract_status FROM schema_mapping"
            )
        }
        ddl = raw.execute(
            "SELECT sql FROM sqlite_master "
            "WHERE type='table' AND name='schema_mapping'"
        ).fetchone()[0]
    finally:
        raw.close()
    assert statuses == {"mapped"}
    assert "CHECK" not in ddl.upper()

    requests = (
        ("get", "/api/schema/mappings", None),
        ("get", "/api/models", None),
        ("get", "/api/models/stingray/tables", None),
        ("get", "/api/models/stingray/runtime", None),
        ("get", "/api/changes", None),
        ("get", "/api/history", None),
        ("post", "/api/changes/validate", {}),
        ("post", "/api/sync", {}),
        ("post", "/api/export", {}),
        ("post", "/api/backup", {}),
    )
    for method, path, payload in requests:
        kwargs = {"json": payload} if payload is not None else {}
        response = getattr(prior_client, method)(path, **kwargs)
        _assert_reimport_required(response)


def test_prior_database_import_replaces_gate_and_reconnects(
    prior_client: TestClient,
    real_workbook: Path,
):
    blocked = prior_client.get("/api/schema/mappings")
    _assert_reimport_required(blocked)

    imported = prior_client.post(
        "/api/imports", json={"workbook_path": str(real_workbook)}
    )

    assert imported.status_code == 200
    assert imported.json()["status"] == "validated"
    mappings = prior_client.get("/api/schema/mappings")
    assert mappings.status_code == 200
    statuses = {
        mapping["contract_status"]
        for mapping in mappings.json()["mappings"]
    }
    assert "mapped" not in statuses
    assert "exact" in statuses
    assert prior_client.get("/api/models").status_code == 200


def test_failed_prior_database_import_preserves_bytes_and_gate(
    prior_client: TestClient,
    prior_canonical_db_path: Path,
    corrupt_workbook_xml_workbook: Path,
):
    assert prior_client.get("/api/status").json()["database"][
        "compatible"
    ] is False
    before = prior_canonical_db_path.read_bytes()

    failed = prior_client.post(
        "/api/imports",
        json={"workbook_path": str(corrupt_workbook_xml_workbook)},
    )

    assert failed.status_code == 409
    assert failed.json()["detail"]["findings"][0]["code"] == (
        "workbook_source_invalid"
    )
    assert prior_canonical_db_path.read_bytes() == before
    _assert_reimport_required(prior_client.get("/api/models"))


def test_reimport_gate_is_documented_for_canonical_endpoints(
    prior_client: TestClient,
):
    schema = prior_client.get("/openapi.json").json()
    for path, operations in schema["paths"].items():
        if not path.startswith("/api/"):
            continue
        for method, operation in operations.items():
            if (method, path) in {
                ("get", "/api/status"),
                ("post", "/api/imports"),
            }:
                continue
            response = operation["responses"]["409"]
            assert response["content"]["application/json"]["schema"][
                "$ref"
            ].endswith("/DatabaseCompatibilityResponse")


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
    assert item["sql_table"] == "stingray_options"
    assert item["entity_id"] == row["option_id"]
    assert item["old"]["option_id"] == row["option_id"]
    assert item["new"]["price"] == row["price"] + 1
