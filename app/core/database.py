from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timezone

from app.core.config import settings

# ─── Motor y sesión ───────────────────────────────────────────────────────────

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # reconecta si la conexión se ha cortado
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ─── Tabla principal ──────────────────────────────────────────────────────────

class Classification(Base):
    """
    Guarda el resultado de cada correo clasificado.
    Cada fila = un correo procesado.
    """
    __tablename__ = "classifications"

    id              = Column(Integer, primary_key=True, index=True)
    timestamp       = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

    # Datos del correo
    message_id      = Column(String(255), unique=True, index=True)  
    subject         = Column(Text, nullable=True)
    sender          = Column(String(255), nullable=True)

    gmail_message_id = Column(String(255), nullable=True)
    gmail_url = Column(Text, nullable=True)

    # Resultado de la clasificación
    category        = Column(String(50), index=True)               
    label_name      = Column(String(100))                             
    confidence      = Column(Float)
    phishing_score  = Column(Float, default=0.0)
    engine_used     = Column(String(20))                              
    explanation     = Column(Text, nullable=True)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_db():
    """Dependencia de FastAPI: abre y cierra la sesión por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Crea las tablas si no existen. Se llama al arrancar la app."""
    Base.metadata.create_all(bind=engine)
