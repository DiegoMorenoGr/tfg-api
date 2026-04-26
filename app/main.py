import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.database import create_tables
from app.routers import classify, stats, reports

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