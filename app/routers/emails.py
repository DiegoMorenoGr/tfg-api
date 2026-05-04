from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import distinct

from app.core.database import get_db, Classification

router = APIRouter(prefix="/emails", tags=["Emails"])


@router.get("/")
def get_processed_emails(
    category: str | None = Query(None),
    sender: str | None = Query(None),
    subject: str | None = Query(None),
    min_phishing: float | None = Query(None, ge=0, le=1),
    max_phishing: float | None = Query(None, ge=0, le=1),
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

    emails = query.order_by(Classification.timestamp.desc()).all()

    return [
        {
            "id": email.id,
            "subject": email.subject,
            "sender": email.sender,
            "timestamp": email.timestamp,
            "category": email.category,
            "phishing_score": email.phishing_score,
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