import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db, Classification
from app.models.schemas import ClassifyRequest, ClassifyResponse
from app.services.classifier import classify_email

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="",
    tags=["Classification"],
)


@router.post(
    "/classify",
    response_model=ClassifyResponse,
    summary="Clasificar un email",
    description="Clasifica un correo electrónico y guarda el resultado en la base de datos.",
)
async def classify_endpoint(email: ClassifyRequest, db: Session = Depends(get_db)):
    try:
        result = await classify_email(
        message_id=email.message_id,
        subject=email.subject,
        sender=email.sender,
        snippet=email.snippet,
        body=email.body,
        engine=email.engine,
        available_categories=email.available_categories,
    )

        existing = (
            db.query(Classification)
            .filter(Classification.message_id == email.message_id)
            .first()
        )

        if existing:
            existing.subject = email.subject
            existing.sender = email.sender
            existing.category = result["category"]
            existing.label_name = result["label_name"]
            existing.confidence = result["confidence"]
            existing.phishing_score = result["phishing_score"]
            existing.engine_used = result["engine_used"]
            existing.explanation = result["explanation"]
        else:
            record = Classification(
                message_id=email.message_id,
                subject=email.subject,
                sender=email.sender,
                category=result["category"],
                label_name=result["label_name"],
                confidence=result["confidence"],
                phishing_score=result["phishing_score"],
                engine_used=result["engine_used"],
                explanation=result["explanation"],
            )
            db.add(record)

        db.commit()

        return ClassifyResponse(
            message_id=result["message_id"],
            category=result["category"],
            label_name=result["label_name"],
            confidence=result["confidence"],
            phishing_score=result["phishing_score"],
            engine_used=result["engine_used"],
            explanation=result["explanation"],
        )

    except SQLAlchemyError as e:
        db.rollback()
        logger.exception("Error de base de datos guardando la clasificación")
        raise HTTPException(
            status_code=500,
            detail=f"Error de base de datos guardando la clasificación: {str(e)}"
        )

    except Exception as e:
        db.rollback()
        logger.exception("Error interno en /classify")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno procesando la clasificación: {str(e)}"
        )