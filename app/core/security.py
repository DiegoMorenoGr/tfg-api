from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

from app.core.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Dependencia de FastAPI para proteger endpoints.

    - Si API_KEY está vacío en .env → autenticación desactivada, pasa siempre.
    - Si API_KEY tiene valor → comprueba que el header X-API-Key coincide.

    Uso en un router:
        @router.post("/classify", dependencies=[Depends(verify_api_key)])
    """
    # Sin clave configurada → acceso libre (útil mientras desarrollas)
    if not settings.API_KEY:
        return

    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key inválida o ausente.",
        )
