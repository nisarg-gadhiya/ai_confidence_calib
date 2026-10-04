import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.api.routes.health import router as health_router
from app.api.routes.gateway import router as gateway_router
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title="AI Confidence Calibration",
    description="A system for estimating and evaluating AI reasoning confidence.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    health_router,
    prefix="/api"
)

app.include_router(
    gateway_router,
    prefix="/api"
)

@app.get("/")
def root():
    return {
        "name": "AI Confidence Calibration",
        "status": "running",
        "version": "0.1.0",
    }