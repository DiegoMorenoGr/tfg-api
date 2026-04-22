from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
import pandas as pd
import io
from datetime import datetime, timezone

from app.core.database import get_db, Classification
from app.core.security import verify_api_key
from app.core.config import CATEGORIES
from app.models.schemas import StatsSummary, CategoryStat

router = APIRouter(prefix="/stats", tags=["Estadísticas"])


@router.get(
    "",
    response_model=StatsSummary,
    dependencies=[Depends(verify_api_key)],
    summary="Estadísticas generales",
)
def get_stats(db: Session = Depends(get_db)):
    total = db.query(func.count(Classification.id)).scalar() or 0

    if total == 0:
        return StatsSummary(
            total_classified=0, total_phishing=0, phishing_rate=0.0,
            avg_confidence=0.0, by_category=[], by_engine={},
            first_classified=None, last_classified=None,
        )

    # Phishing
    total_phishing = db.query(func.count(Classification.id)).filter(
        Classification.category == "phishing"
    ).scalar() or 0

    # Confianza media
    avg_conf = db.query(func.avg(Classification.confidence)).scalar() or 0.0

    # Por categoría
    cat_counts = db.query(
        Classification.category,
        func.count(Classification.id).label("count")
    ).group_by(Classification.category).all()

    by_category = [
        CategoryStat(
            category=row.category,
            label_name=CATEGORIES.get(row.category, "TFG/Revisar"),
            count=row.count,
            percentage=round(row.count / total * 100, 1),
        )
        for row in sorted(cat_counts, key=lambda r: r.count, reverse=True)
    ]

    # Por motor
    engine_counts = db.query(
        Classification.engine_used,
        func.count(Classification.id).label("count")
    ).group_by(Classification.engine_used).all()

    by_engine = {row.engine_used: row.count for row in engine_counts}

    # Fechas
    first = db.query(func.min(Classification.timestamp)).scalar()
    last  = db.query(func.max(Classification.timestamp)).scalar()

    return StatsSummary(
        total_classified=total,
        total_phishing=total_phishing,
        phishing_rate=round(total_phishing / total * 100, 2),
        avg_confidence=round(float(avg_conf), 3),
        by_category=by_category,
        by_engine=by_engine,
        first_classified=first,
        last_classified=last,
    )


@router.get(
    "/export",
    dependencies=[Depends(verify_api_key)],
    summary="Exportar historial completo a Excel",
    description="Descarga un archivo .xlsx con tres hojas: historial, resumen por categoría y resumen por motor.",
)
def export_excel(db: Session = Depends(get_db)):
    records = db.query(Classification).order_by(Classification.timestamp.desc()).all()

    columns = [
        "id", "timestamp", "message_id", "subject", "sender",
        "category", "label_name", "confidence", "phishing_score",
        "engine_used", "explanation"
    ]

    if not records:
        df = pd.DataFrame(columns=columns)
        summary_cat = pd.DataFrame(columns=["category", "total", "avg_confidence", "avg_phishing"])
        summary_engine = pd.DataFrame(columns=["engine_used", "total", "avg_confidence"])
    else:
        df = pd.DataFrame([{
            "id": r.id,
            "timestamp": r.timestamp,
            "message_id": r.message_id,
            "subject": r.subject,
            "sender": r.sender,
            "category": r.category,
            "label_name": r.label_name,
            "confidence": r.confidence,
            "phishing_score": r.phishing_score,
            "engine_used": r.engine_used,
            "explanation": r.explanation,
        } for r in records])

        summary_cat = df.groupby("category").agg(
            total=("id", "count"),
            avg_confidence=("confidence", "mean"),
            avg_phishing=("phishing_score", "mean"),
        ).reset_index()

        summary_engine = df.groupby("engine_used").agg(
            total=("id", "count"),
            avg_confidence=("confidence", "mean"),
        ).reset_index()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Historial", index=False)
        summary_cat.to_excel(writer, sheet_name="Por_categoria", index=False)
        summary_engine.to_excel(writer, sheet_name="Por_motor", index=False)

    output.seek(0)

    filename = f"tfg_emails_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xlsx"

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )