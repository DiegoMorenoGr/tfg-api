"""
keywords.py — Motor de clasificación por palabras clave (baseline).

Sin dependencias externas, sin coste, funciona offline.
Se usa como fallback si los motores de IA fallan.
"""

# Cada regla tiene: clave de categoría, lista de keywords y peso
# Mayor peso = esa categoría se prioriza ante empates
RULES = [
    {
        "key": "phishing",
        "weight": 3,
        "keywords": [
            # Inglés
            "verify your account", "confirm your password", "unusual activity",
            "account suspended", "click here immediately", "update your billing",
            "you have won", "claim your prize", "wire transfer", "nigerian",
            "act now", "limited time offer", "your account will be closed",
            "enter your credentials", "security alert",
            # Español
            "verifica tu cuenta", "confirma tu contraseña", "actividad inusual",
            "cuenta suspendida", "haz clic aquí urgente", "actualiza tu pago",
            "has ganado", "reclama tu premio", "transferencia bancaria urgente",
            "ingresa tus datos", "alerta de seguridad", "lotería", "herencia",
        ],
    },
    {
        "key": "facturas",
        "weight": 2,
        "keywords": [
            "invoice", "factura", "receipt", "recibo", "pago", "payment",
            "iban", "transferencia", "cuota", "suscripción", "subscription",
            "billing", "cobro", "cargo", "importe", "vencimiento", "deuda",
        ],
    },
    {
        "key": "universidad",
        "weight": 2,
        "keywords": [
            "universidad", "campus", "asignatura", "práctica", "tarea",
            "examen", "profesor", "tfg", "tfm", "matrícula", "aula",
            "calificación", "nota", "convocatoria", "secretaría", "rectorado",
            "course", "lecture", "assignment", "deadline", "grade",
        ],
    },
    {
        "key": "trabajo",
        "weight": 2,
        "keywords": [
            "meeting", "reunión", "deadline", "proyecto", "cliente",
            "deliverable", "jira", "sprint", "pull request", "deploy",
            "oferta de trabajo", "entrevista", "contrato", "nómina",
            "empresa", "equipo", "informe", "presentación", "manager",
        ],
    },
    {
        "key": "promociones",
        "weight": 1,
        "keywords": [
            "oferta", "discount", "sale", "promoción", "newsletter",
            "unsubscribe", "darse de baja", "descuento", "rebajas",
            "black friday", "cupón", "coupon", "gratis", "free",
            "hasta un", "%", "aprovecha", "solo por hoy",
        ],
    },
    {
        "key": "personal",
        "weight": 1,
        "keywords": [
            "cumple", "cumpleaños", "familia", "quedamos", "finde",
            "foto", "amigo", "cena", "fiesta", "vacaciones", "viaje",
            "birthday", "dinner", "hangout", "weekend",
        ],
    },
]


def classify(subject: str, sender: str, snippet: str, body: str) -> dict:
    """
    Clasifica un correo usando reglas de palabras clave.

    Returns:
        dict con category, confidence, phishing_score, explanation
    """
    text = f"{subject}\n{sender}\n{snippet}\n{body}".lower()

    scored = []
    for rule in RULES:
        hits = sum(1 for kw in rule["keywords"] if kw in text)
        scored.append({
            "key":   rule["key"],
            "score": hits * rule["weight"],
            "hits":  hits,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    best = scored[0]

    # Normalización: dividimos entre 8 como máximo razonable
    confidence = min(1.0, best["score"] / 8) if best["score"] > 0 else 0.0

    phishing_entry = next((s for s in scored if s["key"] == "phishing"), None)
    phishing_score = min(1.0, phishing_entry["score"] / 6) if phishing_entry else 0.0

    if best["score"] == 0:
        return {
            "category":      "revisar",
            "confidence":    0.0,
            "phishing_score": phishing_score,
            "explanation":   "Sin palabras clave reconocidas. Revisión manual recomendada.",
        }

    return {
        "category":      best["key"],
        "confidence":    round(confidence, 3),
        "phishing_score": round(phishing_score, 3),
        "explanation":   f"Motor keywords: categoría '{best['key']}' con {best['hits']} coincidencias.",
    }
