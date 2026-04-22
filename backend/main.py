from pathlib import Path

import logging
import time

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.config import settings as runtime_settings
from backend.logging_config import setup_logging
from backend.routers import approval, auth, dashboard, export, health, organization, question, settings, task, user_admin
from backend.scripts.init_db import initialize_database
from backend.services.environment import validate_runtime_settings

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

setup_logging()
validate_runtime_settings(runtime_settings)
initialize_database(database_url=runtime_settings.database_url)

app = FastAPI(title="기밀분류시스템 API")
app.include_router(auth.router, prefix="/api")
app.include_router(organization.router, prefix="/api")
app.include_router(organization.admin_router, prefix="/api")
app.include_router(task.router, prefix="/api")
app.include_router(task.admin_router, prefix="/api")
app.include_router(question.router, prefix="/api")
app.include_router(question.admin_router, prefix="/api")
app.include_router(settings.router, prefix="/api")
app.include_router(settings.admin_router, prefix="/api")
app.include_router(approval.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")
app.include_router(user_admin.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(health.router, prefix="/api")

app.mount("/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/js", StaticFiles(directory=FRONTEND_DIR / "js"), name="js")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")

logger = logging.getLogger("backend.requests")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started_at = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        logger.exception(
            "method=%s path=%s status=500 elapsed_ms=%s",
            request.method,
            request.url.path,
            elapsed_ms,
        )
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )
    elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
    logger.info(
        "method=%s path=%s status=%s elapsed_ms=%s",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/")
def read_frontend():
    return _frontend_response()


def _frontend_response():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/inputter")
@app.get("/status")
@app.get("/group")
@app.get("/approver")
@app.get("/admin")
def read_frontend_route():
    return _frontend_response()


@app.get("/approver/approvals/{approval_id}")
def read_approval_frontend_route(approval_id: int):
    return _frontend_response()
