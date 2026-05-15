"""
classifier.py — Orquestador de motores de clasificación.

Motor principal: Gemini
Fallback automático: keywords
"""

import logging

from app.core.config import settings, CATEGORIES
from app.services import keywords, gemini_engine

logger = logging.getLogger(__name__)


PHISHING_BREAKDOWN_KEYS = {
    "urgency": 0.0,
    "sensitive_data_request": 0.0,
    "suspicious_links_or_actions": 0.0,
    "suspicious_sender": 0.0,
    "alarmist_language": 0.0,
    "impersonation": 0.0,
}


def _safe_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_breakdown(value) -> dict:
    """
    Normaliza el desglose de phishing para asegurar que siempre existen
    las mismas claves y que todos los valores están entre 0.0 y 1.0.
    """
    if not isinstance(value, dict):
        value = {}

    normalized = {}

    for key, default_value in PHISHING_BREAKDOWN_KEYS.items():
        normalized[key] = round(
            max(0.0, min(1.0, _safe_float(value.get(key, default_value)))),
            3,
        )

    return normalized


def _normalize_result(result: dict, available_categories: list[str] | None = None) -> dict:
    """
    Normaliza el resultado del motor (Gemini o keywords)
    y valida la categoría contra las disponibles.
    """

    if available_categories:
        valid_categories = set(available_categories)
    else:
        valid_categories = set(CATEGORIES.keys())

    category = result.get("category", "revisar")

    if category not in valid_categories:
        if "Revisar" in valid_categories:
            category = "Revisar"
        elif "TFG/Revisar" in valid_categories:
            category = "TFG/Revisar"
        elif "revisar" in valid_categories:
            category = "revisar"
        else:
            category = next(iter(valid_categories))

    confidence = round(
        max(0.0, min(1.0, _safe_float(result.get("confidence", 0.0)))),
        3
    )

    phishing_score = round(
        max(0.0, min(1.0, _safe_float(result.get("phishing_score", 0.0)))),
        3
    )

    phishing_breakdown = _normalize_breakdown(
        result.get("phishing_breakdown")
    )

    explanation = result.get("explanation") or "Sin explicación."

    return {
        "category": category,
        "confidence": confidence,
        "phishing_score": phishing_score,
        "phishing_breakdown": phishing_breakdown,
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
    logger.info("Categorías recibidas: %s", available_categories)
    logger.info("VERSION NUEVA API - PHISHING BREAKDOWN OK")

    selected_engine = engine or settings.DEFAULT_ENGINE

    # ---------------------
    # MOTOR KEYWORDS
    # ---------------------
    if selected_engine == "keywords":
        raw_result = keywords.classify(subject, sender, snippet, body)
        normalized = _normalize_result(raw_result, available_categories)
        final_engine = "keywords"

    # ---------------------
    # MOTOR GEMINI
    # ---------------------
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

            normalized = _normalize_result(raw_result, available_categories)
            final_engine = "gemini"

        except Exception:
            logger.exception(
                "Gemini falló para message_id=%s. Usando fallback keywords.",
                message_id,
            )

            raw_result = keywords.classify(subject, sender, snippet, body)
            normalized = _normalize_result(raw_result, available_categories)
            final_engine = "keywords"

    category = normalized["category"]

    # ---------------------
    # AJUSTES DE SEGURIDAD
    # ---------------------
    if normalized["phishing_score"] >= 0.75:
        if available_categories and "Phishing" in available_categories:
            category = "Phishing"
        elif available_categories and "TFG/Phishing" in available_categories:
            category = "TFG/Phishing"
        else:
            category = "phishing"

    elif normalized["confidence"] < settings.CONFIDENCE_THRESHOLD:
        if available_categories and "Revisar" in available_categories:
            category = "Revisar"
        elif available_categories and "TFG/Revisar" in available_categories:
            category = "TFG/Revisar"
        else:
            category = "revisar"

    # ---------------------
    # MAPEO A LABEL FINAL
    # ---------------------
    if category in CATEGORIES:
        label_name = CATEGORIES[category]
    else:
        label_name = category

    return {
        "message_id": message_id,
        "category": category,
        "label_name": label_name,
        "confidence": normalized["confidence"],
        "phishing_score": normalized["phishing_score"],
        "phishing_breakdown": normalized["phishing_breakdown"],
        "engine_used": final_engine,
        "explanation": normalized["explanation"],
    }