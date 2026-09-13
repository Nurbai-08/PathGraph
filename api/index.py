import sys
from pathlib import Path

from fastapi import FastAPI, Request

BACKEND_ROOT = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

import app.models
from app.core.database import Base, engine
from app.main import app as backend_app

# A fresh production deployment receives an empty managed PostgreSQL database. This is
# idempotent, so cold starts can safely ensure that the current schema exists.
Base.metadata.create_all(bind=engine)

app = FastAPI(title="PathGraph")
app.mount("/api", backend_app)


@app.middleware("http")
async def restore_vercel_api_path(request: Request, call_next):
    """Restore the path forwarded through the Vite project's Python route."""
    forwarded_path = request.query_params.get("__path")
    if forwarded_path:
        path = f"/api/{forwarded_path.lstrip('/')}"
        request.scope["path"] = path
        request.scope["raw_path"] = path.encode()
    return await call_next(request)
