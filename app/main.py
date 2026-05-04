import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.database import create_tables
from app.routers import classify, stats, reports

from fastapi.staticfiles import StaticFiles
from app.routers import emails
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield

app = FastAPI(
    title="TFG Email Classifier API",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(classify.router)
app.include_router(stats.router)
app.include_router(reports.router)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

app.mount("/web", StaticFiles(directory=str(STATIC_DIR), html=True), name="web")
app.include_router(emails.router)