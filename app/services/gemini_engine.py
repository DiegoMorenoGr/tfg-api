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
CATEGORÍAS DISPONIBLES
=====================

- trabajo: emails laborales, reuniones, proyectos, contratos, nóminas, ofertas de empleo
- universidad: correos académicos, asignaturas, exámenes, profesores, TFG, matrículas
- facturas: facturas, recibos, pagos, suscripciones, cobros, confirmaciones de compra
- promociones: newsletters, ofertas comerciales, descuentos, publicidad, cupones
- personal: amigos, familia, planes personales, eventos sociales
- phishing: intentos de fraude o engaño (ver señales abajo)
- revisar: no hay información suficiente para clasificar con certeza

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

- SI detectas múltiples señales claras de fraude → category = "phishing"
- SI hay dudas razonables → category = "revisar"
- NO inventes información que no esté en el correo
- Basa tu decisión en subject, sender, snippet y body
- El "confidence" debe reflejar qué tan segura es la clasificación
- El "phishing_score" debe reflejar el nivel de riesgo de fraude

=====================
FORMATO DE RESPUESTA
=====================

Devuelve SOLO este JSON válido:

{
  "category": "<trabajo | universidad | facturas | promociones | personal | phishing | revisar>",
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


async def classify(subject: str, sender: str, snippet: str, body: str) -> dict:
    model = get_model()

    body_truncated = (body or "")[:2000]

    prompt = USER_PROMPT.format(
        sender=sender or "Desconocido",
        subject=subject or "(sin asunto)",
        snippet=snippet or "",
        body=body_truncated,
    )

    try:
        response = await asyncio.wait_for(
            model.generate_content_async(
                f"{SYSTEM_PROMPT}\n\n{prompt}",
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

    valid_categories = set(CATEGORIES.keys())

    category = parsed.get("category", "revisar")
    if category not in valid_categories:
        category = "revisar"

    confidence = round(max(0.0, min(1.0, _safe_float(parsed.get("confidence", 0.0)))), 3)
    phishing_score = round(max(0.0, min(1.0, _safe_float(parsed.get("phishing_score", 0.0)))), 3)
    explanation = parsed.get("explanation") or "Sin explicación."

    return {
        "category": category,
        "confidence": confidence,
        "phishing_score": phishing_score,
        "explanation": explanation,
    }