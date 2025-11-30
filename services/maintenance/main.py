from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime, date
from enum import Enum

app = FastAPI(title="Maintenance Service")

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

class MaintenanceType(str, Enum):
    PREVENTIVO = "preventivo"
    CORRECTIVO = "correctivo"

class MaintenanceStatus(str, Enum):
    SOLICITADO = "solicitado"
    EN_PROGRESO = "en progreso"
    COMPLETADO = "completado"
    CANCELADO = "cancelado"

class MaintenanceBase(BaseModel):
    id_equipo: int
    tipo_mantenimiento: MaintenanceType
    estado_mantenimiento: MaintenanceStatus
    prioridad: Optional[str] = None
    fecha_solicitud: Optional[datetime] = None
    fecha_programada: Optional[date] = None
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    costo_mano_obra: Optional[float] = None
    costo_repuestos: Optional[float] = None

class MaintenanceCreate(MaintenanceBase):
    pass

class Maintenance(MaintenanceBase):
    id_mantenimiento: int
    costo_total: float
    equipo_nombre: Optional[str] = None

    class Config:
        orm_mode = True

class SparePartBase(BaseModel):
    id_mantenimiento: int
    descripcion: str
    cantidad: float
    costo_unitario: float

class SparePartCreate(SparePartBase):
    pass

class SparePart(SparePartBase):
    id_repuesto: int
    subtotal: float

    class Config:
        orm_mode = True

@app.get("/maintenance/", response_model=List[Maintenance])
def list_all_maintenance():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                m.*,
                (e.tipo || ' ' || e.marca) AS equipo_nombre
            FROM mantenimiento m
            LEFT JOIN equipo e ON m.id_equipo = e.id_equipo
            ORDER BY m.fecha_solicitud DESC
        """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

@app.post("/maintenance/", response_model=Maintenance)
def create_maintenance(maintenance: MaintenanceCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO mantenimiento (
                id_equipo, tipo_mantenimiento, estado_mantenimiento, prioridad,
                fecha_solicitud, fecha_programada, fecha_inicio, fecha_fin, 
                costo_mano_obra, costo_repuestos
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            maintenance.id_equipo, maintenance.tipo_mantenimiento, 
            maintenance.estado_mantenimiento, maintenance.prioridad,
            maintenance.fecha_solicitud or datetime.now(), maintenance.fecha_programada,
            maintenance.fecha_inicio, maintenance.fecha_fin, 
            maintenance.costo_mano_obra, maintenance.costo_repuestos
        ))
        new_maintenance = cur.fetchone()
        conn.commit()
        return new_maintenance
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/maintenance/equipment/{equipment_id}", response_model=List[Maintenance])
def list_equipment_maintenance(equipment_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                m.*,
                (e.tipo || ' ' || e.marca) AS equipo_nombre
            FROM mantenimiento m
            LEFT JOIN equipo e ON m.id_equipo = e.id_equipo
            WHERE m.id_equipo = %s
            ORDER BY m.fecha_solicitud DESC
        """, (equipment_id,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

@app.post("/maintenance/{maintenance_id}/spare-parts/", response_model=SparePart)
def add_spare_part(maintenance_id: int, spare_part: SparePartCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO mantenimiento_repuesto (
                id_mantenimiento, descripcion, cantidad, costo_unitario
            ) VALUES (%s, %s, %s, %s)
            RETURNING *
        """, (
            maintenance_id, spare_part.descripcion, 
            spare_part.cantidad, spare_part.costo_unitario
        ))
        new_spare_part = cur.fetchone()
        
        cur.execute("""
            UPDATE mantenimiento 
            SET costo_repuestos = COALESCE(costo_repuestos, 0) + %s
            WHERE id_mantenimiento = %s
        """, (new_spare_part['subtotal'], maintenance_id))
        
        conn.commit()
        return new_spare_part
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/maintenance/{maintenance_id}/spare-parts/", response_model=List[SparePart])
def list_maintenance_spare_parts(maintenance_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT * FROM mantenimiento_repuesto 
            WHERE id_mantenimiento = %s
        """, (maintenance_id,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)