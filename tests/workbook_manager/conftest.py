from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "workbook-manager" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import db  # noqa: E402


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def real_workbook(repo_root: Path) -> Path:
    return repo_root / "stingray_master.xlsx"


@pytest.fixture
def connection(tmp_path):
    conn = db.connect(tmp_path / "test.sqlite3")
    try:
        yield conn
    finally:
        conn.close()
