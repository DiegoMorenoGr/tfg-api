from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

from app.core.database import get_db
from app.services.reports_service import generate_monthly_excel, generate_monthly_csv

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/monthly/excel")
def get_monthly_excel_report(
    year: int | None = Query(None),
    month: int | None = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
):
    file_stream = generate_monthly_excel(db, year, month)

    filename = "monthly_report.xlsx"

    return StreamingResponse(
        file_stream,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )


@router.get("/monthly/csv")
def get_monthly_csv_report(
    year: int | None = Query(None),
    month: int | None = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
):
    file_stream = generate_monthly_csv(db, year, month)

    filename = "monthly_report.csv"

    return StreamingResponse(
        file_stream,
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        },
    )