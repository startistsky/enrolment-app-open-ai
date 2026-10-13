import importlib.util
import sys
from pathlib import Path

import pytest


STUDENT_2_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = STUDENT_2_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def database_client(tmp_path):
    database_app = load_module(
        "student2_database_app",
        STUDENT_2_DIR / "database" / "app.py",
    )
    init_db = load_module(
        "student2_init_db",
        STUDENT_2_DIR / "database" / "init_db.py",
    )
    path = tmp_path / "assignments.db"
    database_app.DB_PATH = path
    init_db.DB_PATH = path
    init_db.initialise_database()
    database_app.app.config.update(TESTING=True)
    with database_app.app.test_client() as client:
        yield client


@pytest.fixture
def backend_app():
    module = load_module(
        "student2_backend_app",
        STUDENT_2_DIR / "backend" / "app.py",
    )
    module.app.config.update(TESTING=True)
    return module


@pytest.fixture
def backend_client(backend_app):
    with backend_app.app.test_client() as client:
        yield client
