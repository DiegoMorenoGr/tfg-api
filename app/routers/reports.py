from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

from app.core.database import get_db
from app.services.reports_service import generate_monthly_excel

router = APIRouter(
    prefix="/reports",
    tags=["Reports"]
)


@router.get("/monthly/excel")
def get_monthly_report(db: Session = Depends(get_db)):
    file_stream = generate_monthly_excel(db)

    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=report.xlsx"}
    )