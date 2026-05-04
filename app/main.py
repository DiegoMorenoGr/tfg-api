import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.database import create_tables
from app.routers import classify, stats, reports

from fastapi.staticfiles import StaticFiles
from app.routers import emails
from pathlib import Path

from pathlib import Path
from fastapi.responses import FileResponse


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
app.include_router(emails.router)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

@app.get("/debug/static")
def debug_static():
    return {
        "base_dir": str(BASE_DIR),
        "static_dir": str(STATIC_DIR),
        "static_exists": STATIC_DIR.exists(),
        "index_exists": (STATIC_DIR / "index.html").exists(),
        "files": [p.name for p in STATIC_DIR.iterdir()] if STATIC_DIR.exists() else []
    }

@app.get("/web-test")
def web_test():
    return FileResponse(STATIC_DIR / "index.html")

app.mount("/web", StaticFiles(directory=str(STATIC_DIR), html=True), name="web")
