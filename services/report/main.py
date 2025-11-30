from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import pandas as pd
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

app = FastAPI(title="Report Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASS'),
        cursor_factory=RealDictCursor
    )
    return conn

class EquipmentStatusReport(BaseModel):
    status: str
    count: int
    percentage: float

class MaintenanceCostReport(BaseModel):
    month: str
    total_cost: float
    maintenance_count: int

class EquipmentByLocationReport(BaseModel):
    ubicacion: str
    count: int

class MaintenanceByTypeReport(BaseModel):
    tipo_mantenimiento: str
    count: int
    total_cost: float

@app.get("/reports/equipment-status")
def get_equipment_status_report():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT COUNT(*) as total FROM equipo")
        total = cur.fetchone()['total']
        
        if total == 0:
            return []
            
        cur.execute("""
            SELECT 
                estado as status, 
                COUNT(*) as count,
                ROUND(COUNT(*) * 100.0 / %s, 2) as percentage
            FROM equipo
            GROUP BY estado
            ORDER BY count DESC
        """, (total,))
        
        return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/reports/maintenance-costs")
def get_maintenance_cost_report(months: int = 12):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                TO_CHAR(fecha_fin, 'YYYY-MM') as month,
                COUNT(*) as maintenance_count,
                COALESCE(SUM(costo_total), 0) as total_cost
            FROM mantenimiento
            WHERE fecha_fin >= NOW() - INTERVAL '%s months'
              AND fecha_fin <= NOW()
            GROUP BY TO_CHAR(fecha_fin, 'YYYY-MM')
            ORDER BY month
        """, (months,))
        
        return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/reports/equipment-by-location")
def get_equipment_by_location():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                u.descripcion as ubicacion,
                COUNT(e.id_equipo) as count
            FROM equipo e
            LEFT JOIN ubicacion u ON e.id_ubicacion_actual = u.id_ubicacion
            GROUP BY u.descripcion
            ORDER BY count DESC
        """)
        return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/reports/maintenance-by-type")
def get_maintenance_by_type():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                tipo_mantenimiento,
                COUNT(*) as count,
                COALESCE(SUM(costo_total), 0) as total_cost
            FROM mantenimiento
            GROUP BY tipo_mantenimiento
            ORDER BY count DESC
        """)
        return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/reports/equipment-aging")
def get_equipment_aging_report():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                c.fecha_compra as purchase_date,
                e.tipo as equipment_type,
                e.marca as brand,
                e.codigo_inventario as inventory_code,
                EXTRACT(YEAR FROM AGE(NOW(), c.fecha_compra)) as years_old
            FROM equipo e
            JOIN compra_detalle cd ON e.id_equipo = cd.id_equipo
            JOIN compra c ON cd.id_compra = c.id_compra
            ORDER BY years_old DESC
        """)
        
        df = pd.DataFrame(cur.fetchall())
        
        bins = [0, 1, 3, 5, 10, float('inf')]
        labels = ['<1 year', '1-3 years', '3-5 years', '5-10 years', '10+ years']
        
        if not df.empty:
            df['age_group'] = pd.cut(df['years_old'], bins=bins, labels=labels, right=False)
            result = df.groupby('age_group').size().reset_index(name='count')
            return result.to_dict('records')
        return []
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)

def _append_report_section(elements: List[Any], title: str, dataset: List[Dict[str, Any]], styles):
    """Add a titled section with an optional table for a report dataset."""
    elements.append(Paragraph(title, styles['Heading2']))
    if not dataset:
        elements.append(Paragraph("No data available.", styles['Normal']))
        elements.append(Spacer(1, 12))
        return

    columns = list(dataset[0].keys())
    table_data = [columns]
    for row in dataset:
        table_data.append([_normalize_value(row.get(column)) for column in columns])

    table = Table(table_data, repeatRows=1)
    table_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4F81BD")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
    ])
    table.setStyle(table_style)
    elements.append(table)
    elements.append(Spacer(1, 18))

def _rename_dataset_for_pdf(title: str, dataset: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not dataset:
        return dataset

    mappings_by_title: Dict[str, Dict[str, str]] = {
        "Estado del equipo": {
            "status": "Estado",
            "count": "Cantidad",
            "percentage": "Porcentaje (%)",
        },
        "Costos de mantenimiento (12 meses)": {
            "month": "Mes",
            "total_cost": "Costo total",
            "maintenance_count": "N° mantenimientos",
        },
        "Equipos por ubicación": {
            "ubicacion": "Ubicación",
            "count": "Cantidad de equipos",
        },
        "Mantenimientos por tipo": {
            "tipo_mantenimiento": "Tipo de mantenimiento",
            "count": "Cantidad",
            "total_cost": "Costo total",
        },
        "Antigüedad del equipo": {
            "age_group": "Rango de antigüedad",
            "count": "Cantidad de equipos",
        },
    }

    mapping = mappings_by_title.get(title, {})

    translated: List[Dict[str, Any]] = []
    for row in dataset:
        new_row: Dict[str, Any] = {}
        for key, value in row.items():
            new_key = mapping.get(key, key)
            new_row[new_key] = value
        translated.append(new_row)

    return translated

@app.get("/reports/export/excel")
def export_reports_to_excel():
    try:
        output = BytesIO()

        with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
            status_df = pd.DataFrame(get_equipment_status_report())
            if not status_df.empty:
                status_df = status_df.rename(
                    columns={
                        "status": "Estado",
                        "count": "Cantidad",
                        "percentage": "Porcentaje (%)",
                    }
                )
                status_df.to_excel(writer, sheet_name="Estado equipos", index=False)

            costs_df = pd.DataFrame(get_maintenance_cost_report(12))
            if not costs_df.empty:
                costs_df = costs_df.rename(
                    columns={
                        "month": "Mes",
                        "total_cost": "Costo total",
                        "maintenance_count": "N° mantenimientos",
                    }
                )
                costs_df.to_excel(writer, sheet_name="Costos mantto", index=False)

            location_df = pd.DataFrame(get_equipment_by_location())
            if not location_df.empty:
                location_df = location_df.rename(
                    columns={
                        "ubicacion": "Ubicación",
                        "count": "Cantidad de equipos",
                    }
                )
                location_df.to_excel(writer, sheet_name="Equipos x ubicación", index=False)

            type_df = pd.DataFrame(get_maintenance_by_type())
            if not type_df.empty:
                type_df = type_df.rename(
                    columns={
                        "tipo_mantenimiento": "Tipo de mantenimiento",
                        "count": "Cantidad",
                        "total_cost": "Costo total",
                    }
                )
                type_df.to_excel(writer, sheet_name="Mantto x tipo", index=False)

            aging_df = pd.DataFrame(get_equipment_aging_report())
            if not aging_df.empty:
                aging_df = aging_df.rename(
                    columns={
                        "age_group": "Rango de antigüedad",
                        "count": "Cantidad de equipos",
                    }
                )
                aging_df.to_excel(writer, sheet_name="Antigüedad equipos", index=False)

        output.seek(0)

        headers = {
            "Content-Disposition": "attachment; filename=equipment_reports.xlsx"
        }

        return StreamingResponse(
            output,
            media_type=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
            headers=headers,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reports/export/pdf")
def export_reports_to_pdf():
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=18,
        )

        styles = getSampleStyleSheet()
        elements = []

        reports = [
            ("Estado del equipo", get_equipment_status_report()),
            ("Costos de mantenimiento (12 meses)", get_maintenance_cost_report(12)),
            ("Equipos por ubicación", get_equipment_by_location()),
            ("Mantenimientos por tipo", get_maintenance_by_type()),
            ("Antigüedad del equipo", get_equipment_aging_report()),
        ]

        for title, dataset in reports:
            dataset_es = _rename_dataset_for_pdf(title, dataset)
            _append_report_section(elements, title, dataset_es, styles)

        doc.build(elements)
        buffer.seek(0)

        headers = {
            "Content-Disposition": "attachment; filename=equipment_reports.pdf"
        }

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers=headers,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)