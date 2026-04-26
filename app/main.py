import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.database import create_tables
from app.routers import classify, stats, reports
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    safe_db_url = settings.DATABASE_URL
    if "@" in safe_db_url and "://" in safe_db_url:
        prefix, rest = safe_db_url.split("://", 1)
        if ":" in rest and "@" in rest:
            userinfo, hostpart = rest.split("@", 1)
            if ":" in userinfo:
                user, _ = userinfo.split(":", 1)
                safe_db_url = f"{prefix}://{user}:****@{hostpart}"

    print("TFG-API-V2 ARRANCANDO")
    print("DATABASE_URL usada por la app:", safe_db_url)

    create_tables()
    yield
    
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