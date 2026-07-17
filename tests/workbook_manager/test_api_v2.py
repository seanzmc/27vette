from __future__ import annotations

from pathlib import Path

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
