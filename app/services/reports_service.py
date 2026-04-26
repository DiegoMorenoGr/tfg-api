from io import BytesIO
from datetime import date
from calendar import monthrange

from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference
from sqlalchemy.orm import Session

from app.core.database import Classification


def _week_of_month(day: int) -> int:
    if day <= 7:
        return 1
    elif day <= 14:
        return 2
    elif day <= 21:
        return 3
    else:
        return 4


def generate_monthly_excel(db: Session) -> BytesIO:
    today = date.today()
    year = today.year
    month = today.month

    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    records = (
        db.query(Classification)
        .filter(Classification.created_at >= start_date)
        .filter(Classification.created_at <= end_date)
        .all()
    )

    wb = Workbook()

    # -----------------------
    # Hoja 1: Datos
    # -----------------------
    ws_data = wb.active
    ws_data.title = "Datos"

    headers = [
        "message_id",
        "subject",
        "sender",
        "category",
        "label_name",
        "confidence",
        "phishing_score",
        "engine_used",
        "created_at",
        "week_of_month",
    ]
    ws_data.append(headers)

    weekly_counts = {}

    for r in records:
        created_at = r.created_at
        week = _week_of_month(created_at.day)

        category = r.category or "Sin categoría"

        if category not in weekly_counts:
            weekly_counts[category] = {1: 0, 2: 0, 3: 0, 4: 0}

        weekly_counts[category][week] += 1

        ws_data.append([
            r.message_id,
            r.subject,
            r.sender,
            r.category,
            r.label_name,
            r.confidence,
            r.phishing_score,
            r.engine_used,
            r.explanation,
            r.created_at,
            week,
        ])

    # -----------------------
    # Hoja 2: Resumen semanal
    # -----------------------
    ws_summary = wb.create_sheet("Resumen semanal")

    ws_summary.append(["Categoría", "Semana 1", "Semana 2", "Semana 3", "Semana 4"])

    for category, weeks in weekly_counts.items():
        ws_summary.append([
            category,
            weeks.get(1, 0),
            weeks.get(2, 0),
            weeks.get(3, 0),
            weeks.get(4, 0),
        ])

    # -----------------------
    # Hoja 3: Gráfica
    # -----------------------
    ws_chart = wb.create_sheet("Gráfica")

    ws_chart.append(["Semana"] + list(weekly_counts.keys()))

    for week in [1, 2, 3, 4]:
        row = [f"Semana {week}"]
        for category in weekly_counts.keys():
            row.append(weekly_counts[category].get(week, 0))
        ws_chart.append(row)

    if weekly_counts:
        chart = LineChart()
        chart.title = "Correos por categoría y semana"
        chart.y_axis.title = "Número de correos"
        chart.x_axis.title = "Semana del mes"

        data = Reference(
            ws_chart,
            min_col=2,
            max_col=1 + len(weekly_counts),
            min_row=1,
            max_row=5,
        )

        categories = Reference(
            ws_chart,
            min_col=1,
            min_row=2,
            max_row=5,
        )

        chart.add_data(data, titles_from_data=True)
        chart.set_categories(categories)

        ws_chart.add_chart(chart, "A8")

    # Ajustar ancho columnas
    for sheet in [ws_data, ws_summary, ws_chart]:
        for column_cells in sheet.columns:
            max_length = 0
            column_letter = column_cells[0].column_letter

            for cell in column_cells:
                if cell.value:
                    max_length = max(max_length, len(str(cell.value)))

            sheet.column_dimensions[column_letter].width = min(max_length + 2, 50)

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return output