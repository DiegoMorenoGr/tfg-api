"""
classifier.py — Orquestador de motores de clasificación.

Motor principal: Gemini
Fallback automático: keywords
"""

import logging
from app.core.config import settings, CATEGORIES
from app.services import keywords, gemini_engine

logger = logging.getLogger(__name__)


def _safe_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_result(result: dict) -> dict:
    valid_categories = set(CATEGORIES.keys())

    category = result.get("category", "revisar")
    if category not in valid_categories:
        category = "revisar"

    confidence = round(max(0.0, min(1.0, _safe_float(result.get("confidence", 0.0)))), 3)
    phishing_score = round(max(0.0, min(1.0, _safe_float(result.get("phishing_score", 0.0)))), 3)

    explanation = result.get("explanation") or "Sin explicación."

    return {
        "category": category,
        "confidence": confidence,
        "phishing_score": phishing_score,
        "explanation": explanation,
    }


async def classify_email(
    message_id: str,
    subject: str,
    sender: str,
    snippet: str,
    body: str,
    engine: str | None = None,
    available_categories: list[str] | None = None,
) -> dict:
    selected_engine = engine or settings.DEFAULT_ENGINE

    if selected_engine == "keywords":
        raw_result = keywords.classify(subject, sender, snippet, body)
        normalized = _normalize_result(raw_result)
        final_engine = "keywords"
    else:
        try:
            logger.info("Clasificando mensaje %s con Gemini", message_id)
            raw_result = await gemini_engine.classify(
                subject,
                sender,
                snippet,
                body,
                available_categories=available_categories,
            )
            normalized = _normalize_result(raw_result)
            final_engine = "gemini"
        except Exception:
            logger.exception(
                "Gemini falló para message_id=%s. Usando fallback keywords.",
                message_id,
            )
            raw_result = keywords.classify(subject, sender, snippet, body)
            normalized = _normalize_result(raw_result)
            final_engine = "keywords"

    category = normalized["category"]

    if normalized["phishing_score"] >= 0.75:
        category = "phishing"

    elif normalized["confidence"] < settings.CONFIDENCE_THRESHOLD:
        category = "revisar"

    label_name = CATEGORIES.get(category, "TFG/Revisar")

    return {
        "message_id": message_id,
        "category": category,
        "label_name": label_name,
        "confidence": normalized["confidence"],
        "phishing_score": normalized["phishing_score"],
        "engine_used": final_engine,
        "explanation": normalized["explanation"],
    }