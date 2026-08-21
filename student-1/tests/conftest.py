import importlib.util
from pathlib import Path

import pytest


STUDENT_1_DIR = Path(__file__).resolve().parents[1]


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def database_client(tmp_path):
    database_app = load_module(
        "student1_database_app",
        STUDENT_1_DIR / "database" / "app.py",
    )
    database_app.DB_PATH = tmp_path / "courses.db"
    database_app.init_db()
    database_app.app.config.update(TESTING=True)

    with database_app.app.test_client() as client:
        yield client


@pytest.fixture
def backend_client():
    backend_app = load_module(
        "student1_backend_app",
        STUDENT_1_DIR / "backend" / "app.py",
    )
    backend_app.app.config.update(TESTING=True)

    with backend_app.app.test_client() as client:
        yield client
