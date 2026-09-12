import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.ai_settings import router as ai_settings_router
from app.api.auth import router as auth_router
from app.api.graph import router as graph_router
from app.api.interactions import router as interactions_router
from app.api.jobs import router as jobs_router
from app.api.learning import router as learning_router
from app.api.sources import router as sources_router
from app.api.workspaces import router as workspaces_router
from app.core.config import settings
from app.core.errors import AppError
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(ai_settings_router)
app.include_router(graph_router)
app.include_router(interactions_router)
app.include_router(learning_router)
app.include_router(workspaces_router)
app.include_router(sources_router)
app.include_router(jobs_router)


@app.get("/health")
def health() -> dict[str, object]:
    return {"data": {"status": "ok"}, "error": None}


@app.exception_handler(AppError)
async def handle_app_error(_: Request, error: AppError) -> JSONResponse:
    return error_response(error.status_code, error.code, error.message)


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, error: RequestValidationError) -> JSONResponse:
    first_error = error.errors()[0]
    message = str(first_error.get("msg", "Request validation failed."))
    location = first_error.get("loc", ())
    field = str(location[-1]) if location else "request"
    return error_response(422, "VALIDATION_ERROR", f"{field}: {message}")


@app.exception_handler(HTTPException)
async def handle_http_error(_: Request, error: HTTPException) -> JSONResponse:
    return error_response(error.status_code, "HTTP_ERROR", str(error.detail))


@app.exception_handler(Exception)
async def handle_unexpected_error(_: Request, error: Exception) -> JSONResponse:
    logger.exception("Unhandled API error", exc_info=error)
    return error_response(500, "INTERNAL_ERROR", "An unexpected error occurred.")


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"data": None, "error": {"code": code, "message": message}},
    )
