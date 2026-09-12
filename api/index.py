import sys
from pathlib import Path

from fastapi import FastAPI

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

import app.models  # noqa: E402,F401
from app.core.database import Base, engine  # noqa: E402
from app.main import app as backend_app  # noqa: E402

# A fresh production deployment receives an empty managed PostgreSQL database. This is
# idempotent, so cold starts can safely ensure that the current schema exists.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PathGraph")
app.mount("/api", backend_app)
