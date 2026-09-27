from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.health import router as health_router
from app.api.routes.questions import router as questions_router
from app.api.routes.inference import router as inference_router

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
    questions_router,
    prefix="/api"
)
app.include_router(
    inference_router,
    prefix="/api"
)

@app.get("/")
def root():
    return {
        "name": "AI Confidence Calibration",
        "status": "running",
        "version": "0.1.0",
    }