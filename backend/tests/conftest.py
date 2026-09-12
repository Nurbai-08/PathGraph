import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["JWT_SECRET"] = "test-secret-that-is-long-enough-for-tests"
os.environ["SOURCE_STORAGE_DIR"] = str(Path(__file__).parent.parent / ".test-source-storage")
os.environ["CREDENTIAL_ENCRYPTION_KEY"] = "test-credential-key-not-for-production"
os.environ["LOCAL_AUTH_ENABLED"] = "true"
os.environ["DEMO_GRAPH_ENABLED"] = "false"

from app import models  # noqa: E402, F401
from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def reset_database() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    storage = Path(os.environ["SOURCE_STORAGE_DIR"])
    storage.mkdir(exist_ok=True)
    for item in storage.iterdir():
        if item.is_file():
            item.unlink()


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
