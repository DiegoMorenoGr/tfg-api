import asyncio
import json
import logging
import google.generativeai as genai

from app.core.config import settings, CATEGORIES

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """Eres un sistema experto en clasificación automática de correos electrónicos y detección de fraude.

Tu tarea es analizar el contenido de un correo y devolver ÚNICAMENTE un objeto JSON válido.
NO incluyas texto adicional, explicaciones fuera del JSON ni bloques de código.

=====================
SEÑALES DE PHISHING
=====================

Aumenta el "phishing_score" si detectas:

- Urgencia artificial: "actúa ahora", "últimas 24 horas", "tu cuenta será bloqueada"
- Solicitud de credenciales: contraseña, DNI, tarjeta, datos bancarios
- Enlaces sospechosos o dominios que imitan a empresas conocidas
- Remitente extraño o dominio mal escrito
- Premios falsos: "has ganado", "reclama tu premio", "herencia"
- Amenazas: suspensión de cuenta, sanciones, deudas urgentes
- Errores gramaticales graves o texto mal traducido
- Solicitud de transferencia de dinero urgente

=====================
REGLAS IMPORTANTES
=====================

- NO inventes información que no esté en el correo
- Basa tu decisión en subject, sender, snippet y body
- El "confidence" debe reflejar qué tan segura es la clasificación
- El "phishing_score" debe reflejar el nivel de riesgo de fraude
- Devuelve SOLO JSON válido, sin explicaciones fuera del JSON

=====================
FORMATO DE RESPUESTA
=====================

Devuelve SOLO este JSON válido:

{
  "category": "<una de las categorías disponibles>",
  "confidence": <número entre 0.0 y 1.0>,
  "phishing_score": <número entre 0.0 y 1.0>,
  "explanation": "<una sola frase breve en español explicando la decisión>"
}
"""


USER_PROMPT = """Analiza este correo:

De: {sender}
Asunto: {subject}
Fragmento: {snippet}
Cuerpo: {body}"""


def get_model():
    genai.configure(api_key=settings.GEMINI_API_KEY)
    return genai.GenerativeModel(settings.GEMINI_MODEL)


def _safe_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clean_raw_response(raw: str) -> str:
    raw = (raw or "{}").strip()

    if raw.startswith("```"):
        parts = raw.split("```")
        if len(parts) > 1:
            raw = parts[1]
        if raw.startswith("json"):
            raw = raw[4:]

    return raw.strip()


def _build_categories_block(available_categories: list[str] | None) -> tuple[str, set[str]]:
    """
    Construye el bloque de categorías para Gemini y devuelve también
    el conjunto de categorías válidas para validar la respuesta.
    """

    if available_categories:
        categories = available_categories
    else:
        categories = list(CATEGORIES.keys())

    categories_text = "\n".join(f"- {category}" for category in categories)

    categories_block = f"""
=====================
CATEGORÍAS DISPONIBLES
=====================

Debes clasificar el correo usando ÚNICAMENTE una de estas categorías:

{categories_text}

Reglas sobre categorías:
- La categoría devuelta debe coincidir EXACTAMENTE con una de la lista anterior.
- No inventes categorías nuevas.
- Si detectas fraude o phishing, usa "TFG/Phishing" si está disponible.
- Si detectas fraude o phishing y "TFG/Phishing" no está disponible, usa "phishing" si está disponible.
- Si no tienes suficiente información, usa "TFG/Revisar" si está disponible.
- Si no tienes suficiente información y "TFG/Revisar" no está disponible, usa "revisar" si está disponible.
"""

    return categories_block, set(categories)


async def classify(
    subject: str,
    sender: str,
    snippet: str,
    body: str,
    available_categories: list[str] | None = None,
) -> dict:
    model = get_model()

    body_truncated = (body or "")[:2000]

    prompt = USER_PROMPT.format(
        sender=sender or "Desconocido",
        subject=subject or "(sin asunto)",
        snippet=snippet or "",
        body=body_truncated,
    )

    categories_block, valid_categories = _build_categories_block(available_categories)

    try:
        response = await asyncio.wait_for(
            model.generate_content_async(
                f"{SYSTEM_PROMPT}\n\n{categories_block}\n\n{prompt}",
                generation_config=genai.GenerationConfig(
                    temperature=0,
                    max_output_tokens=300,
                ),
            ),
            timeout=20,
        )
    except asyncio.TimeoutError:
        logger.warning("Timeout llamando a Gemini")
        raise RuntimeError("Timeout llamando a Gemini")

    raw = _clean_raw_response(getattr(response, "text", "{}"))

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Gemini devolvió JSON inválido: %s", raw[:300])
        raise RuntimeError("Gemini devolvió JSON inválido")

    category = parsed.get("category")

    if category not in valid_categories:
        if "TFG/Revisar" in valid_categories:
            category = "TFG/Revisar"
        elif "revisar" in valid_categories:
            category = "revisar"
        else:
            category = next(iter(valid_categories))

    confidence = round(
        max(0.0, min(1.0, _safe_float(parsed.get("confidence", 0.0)))),
        3
    )

    phishing_score = round(
        max(0.0, min(1.0, _safe_float(parsed.get("phishing_score", 0.0)))),
        3
    )

    explanation = parsed.get("explanation") or "Sin explicación."

    return {
        "category": category,
        "confidence": confidence,
        "phishing_score": phishing_score,
        "explanation": explanation,
    }