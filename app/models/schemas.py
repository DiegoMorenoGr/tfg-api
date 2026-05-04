from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class ClassifyRequest(BaseModel):
    """
    Cuerpo de la petición POST /classify.
    """
    message_id: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="ID único del mensaje en Gmail"
    )

    gmail_message_id: Optional[str] = Field(
        None,
        max_length=255,
        description="ID interno del mensaje en Gmail para generar el enlace directo"
    )

    gmail_url: Optional[str] = Field(
        None,
        description="URL directa al correo original en Gmail"
    )

    subject: Optional[str] = Field("", description="Asunto del correo")
    sender: Optional[str] = Field("", description="Dirección del remitente")
    snippet: Optional[str] = Field("", description="Fragmento corto del cuerpo")
    body: Optional[str] = Field("", description="Cuerpo completo (puede ser largo)")
    engine: Optional[Literal["keywords", "gemini"]] = Field(
        None,
        description="Motor a usar. Si no se indica, se usa DEFAULT_ENGINE del .env"
    )
    available_categories: Optional[list[str]] = Field(
        None,
        description="Lista opcional de categorías disponibles del usuario. Si se indica, Gemini debe clasificar usando una de ellas."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message_id": "18f3a2b1c4d5e6f7",
                "gmail_message_id": "18f3a2b1c4d5e6f7",
                "gmail_url": "https://mail.google.com/mail/u/0/#all/18f3a2b1c4d5e6f7",
                "subject": "Factura marzo 2026",
                "sender": "billing@empresa.com",
                "snippet": "Adjuntamos su factura correspondiente al mes de marzo...",
                "body": "Estimado cliente, le remitimos la factura número 2026-03-042...",
                "engine": "gemini",
                "available_categories": [
                    "Compras",
                    "Universidad",
                    "Trabajo",
                    "Familia",
                    "TFG/Phishing",
                    "TFG/Revisar"
                ]
            }
        }

class ClassifyResponse(BaseModel):
    message_id: str
    category: str = Field(..., description="Clave de categoría: trabajo, facturas, phishing...")
    label_name: str = Field(..., description="Nombre de etiqueta Gmail: TFG/Trabajo...")
    confidence: float = Field(..., ge=0.0, le=1.0)
    phishing_score: float = Field(..., ge=0.0, le=1.0)
    engine_used: str
    explanation: str


class CategoryStat(BaseModel):
    category: str
    label_name: str
    count: int
    percentage: float


class StatsSummary(BaseModel):
    total_classified: int
    total_phishing: int
    phishing_rate: float
    avg_confidence: float
    by_category: list[CategoryStat]
    by_engine: dict[str, int]
    first_classified: Optional[datetime]
    last_classified: Optional[datetime]