import json

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import distinct

from app.core.database import get_db, Classification

router = APIRouter(prefix="/emails", tags=["Emails"])


def parse_breakdown(value):
    if not value:
        return {}

    try:
        return json.loads(value)
    except Exception:
        return {}


@router.get("/")
def get_processed_emails(
    category: str | None = Query(None),
    sender: str | None = Query(None),
    subject: str | None = Query(None),
    min_phishing: float | None = Query(None, ge=0, le=1),
    max_phishing: float | None = Query(None, ge=0, le=1),
    sort_by: str | None = Query(
        None,
        description="Orden por fecha: email_desc, email_asc, processed_desc, processed_asc"
    ),
    db: Session = Depends(get_db),
):
    query = db.query(Classification)

    if category:
        query = query.filter(Classification.category == category)

    if sender:
        query = query.filter(Classification.sender.ilike(f"%{sender}%"))

    if subject:
        query = query.filter(Classification.subject.ilike(f"%{subject}%"))

    if min_phishing is not None:
        query = query.filter(Classification.phishing_score >= min_phishing)

    if max_phishing is not None:
        query = query.filter(Classification.phishing_score <= max_phishing)

    # Ordenación
    if sort_by == "email_asc":
        query = query.order_by(Classification.email_timestamp.asc().nullslast())
    elif sort_by == "email_desc":
        query = query.order_by(Classification.email_timestamp.desc().nullslast())
    elif sort_by == "processed_asc":
        query = query.order_by(Classification.timestamp.asc())
    else:
        # Por defecto: como lo tenías antes, fecha de procesado más reciente primero
        query = query.order_by(Classification.timestamp.desc())

    emails = query.all()

    return [
        {
            "id": email.id,
            "subject": email.subject,
            "sender": email.sender,

            # La web puede seguir usando "timestamp".
            # Si existe email_timestamp, muestra la fecha real del correo.
            # Si no existe, usa la fecha de procesado.
            "timestamp": email.email_timestamp or email.timestamp,

            # Fechas separadas por si quieres usarlas más adelante
            "email_timestamp": email.email_timestamp,
            "processed_timestamp": email.timestamp,

            "category": email.category,
            "phishing_score": email.phishing_score,
            "phishing_breakdown": parse_breakdown(email.phishing_breakdown),
            "explanation": email.explanation,
            "gmail_url": getattr(email, "gmail_url", None),
        }
        for email in emails
    ]


@router.get("/categories")
def get_categories(db: Session = Depends(get_db)):
    categories = (
        db.query(distinct(Classification.category))
        .filter(Classification.category.isnot(None))
        .order_by(Classification.category.asc())
        .all()
    )

    return [category[0] for category in categories]