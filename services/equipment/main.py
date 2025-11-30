from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import datetime, date

app = FastAPI(title="Equipment Service")

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

def _get_equipment_with_location(cur, equipment_id: int):
    cur.execute(
        """
        SELECT
            e.*,
            u.descripcion AS ubicacion_descripcion
        FROM equipo e
        LEFT JOIN ubicacion u ON e.id_ubicacion_actual = u.id_ubicacion
        WHERE e.id_equipo = %s
        """,
        (equipment_id,),
    )
    return cur.fetchone()

class EquipmentBase(BaseModel):
    codigo_inventario: str
    numero_serie: str
    tipo: str
    marca: str
    estado: str
    id_ubicacion_actual: Optional[int] = None
    vida_util_meses: Optional[int] = None
    observaciones: Optional[str] = None

class EquipmentCreate(EquipmentBase):
    pass

class Equipment(EquipmentBase):
    id_equipo: int
    ubicacion_descripcion: Optional[str] = None

    class Config:
        orm_mode = True

class EquipmentPurchase(BaseModel):
    id_compra: int
    numero_documento: str
    fecha_compra: date
    monto_total: Optional[float] = None
    proveedor: Optional[str] = None
    codigo_contrato: Optional[str] = None
    descripcion_contrato: Optional[str] = None
    cantidad: Optional[float] = None
    costo_unitario: Optional[float] = None

    class Config:
        orm_mode = True

class EquipmentMovement(BaseModel):
    id_movimiento: int
    id_equipo: int
    fecha_movimiento: datetime
    id_ubicacion_origen: Optional[int] = None
    id_ubicacion_destino: Optional[int] = None
    ubicacion_origen_descripcion: Optional[str] = None
    ubicacion_destino_descripcion: Optional[str] = None
    tipo_movimiento: str
    observaciones: Optional[str] = None

    class Config:
        orm_mode = True

class Location(BaseModel):
    id_ubicacion: int
    descripcion: str

    class Config:
        orm_mode = True

@app.post("/equipment/", response_model=Equipment)
def create_equipment(equipment: EquipmentCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO equipo (
                codigo_inventario, numero_serie, tipo, marca, estado, 
                id_ubicacion_actual, vida_util_meses, observaciones
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id_equipo
        """, (
            equipment.codigo_inventario, equipment.numero_serie, equipment.tipo,
            equipment.marca, equipment.estado, equipment.id_ubicacion_actual,
            equipment.vida_util_meses, equipment.observaciones
        ))
        new_equipment = cur.fetchone()
        conn.commit()
        if not new_equipment:
            raise HTTPException(status_code=400, detail="Equipment could not be created")
        return _get_equipment_with_location(cur, new_equipment["id_equipo"])
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/equipment/", response_model=List[Equipment])
def list_equipment():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT
                e.*,
                u.descripcion AS ubicacion_descripcion
            FROM equipo e
            LEFT JOIN ubicacion u ON e.id_ubicacion_actual = u.id_ubicacion
        """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

@app.get("/equipment/locations/", response_model=List[Location])
def list_locations():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT
                id_ubicacion,
                descripcion
            FROM ubicacion
            ORDER BY descripcion
        """)
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

@app.get("/equipment/{equipment_id}", response_model=Equipment)
def get_equipment(equipment_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        equipment = _get_equipment_with_location(cur, equipment_id)
        if equipment is None:
            raise HTTPException(status_code=404, detail="Equipment not found")
        return equipment
    finally:
        cur.close()
        conn.close()

@app.put("/equipment/{equipment_id}", response_model=Equipment)
def update_equipment(equipment_id: int, equipment: EquipmentCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE equipo SET
                codigo_inventario = %s,
                numero_serie = %s,
                tipo = %s,
                marca = %s,
                estado = %s,
                id_ubicacion_actual = %s,
                vida_util_meses = %s,
                observaciones = %s
            WHERE id_equipo = %s
            RETURNING id_equipo
        """, (
            equipment.codigo_inventario, equipment.numero_serie, equipment.tipo,
            equipment.marca, equipment.estado, equipment.id_ubicacion_actual,
            equipment.vida_util_meses, equipment.observaciones, equipment_id
        ))
        updated_equipment = cur.fetchone()
        if updated_equipment is None:
            raise HTTPException(status_code=404, detail="Equipment not found")
        conn.commit()
        return _get_equipment_with_location(cur, updated_equipment["id_equipo"])
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.delete("/equipment/{equipment_id}")
def delete_equipment(equipment_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("DELETE FROM equipo WHERE id_equipo = %s RETURNING id_equipo", (equipment_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="Equipment not found")
        conn.commit()
        return {"message": "Equipment deleted successfully"}
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get(
    "/equipment/{equipment_id}/purchases/",
    response_model=List[EquipmentPurchase],
)
def list_equipment_purchases(equipment_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                c.id_compra,
                c.numero_documento,
                c.fecha_compra,
                c.monto_total,
                p.razon_social AS proveedor,
                ct.codigo_contrato,
                ct.descripcion AS descripcion_contrato,
                cd.cantidad,
                cd.costo_unitario
            FROM compra_detalle cd
            JOIN compra c ON cd.id_compra = c.id_compra
            LEFT JOIN proveedor p ON c.id_proveedor = p.id_proveedor
            LEFT JOIN contrato ct ON c.id_contrato = ct.id_contrato
            WHERE cd.id_equipo = %s
            ORDER BY c.fecha_compra DESC
            """,
            (equipment_id,),
        )
        return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get(
    "/equipment/{equipment_id}/movements/",
    response_model=List[EquipmentMovement],
)
def list_equipment_movements(equipment_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                em.id_movimiento,
                em.id_equipo,
                em.fecha_movimiento,
                em.id_ubicacion_origen,
                em.id_ubicacion_destino,
                uo.descripcion AS ubicacion_origen_descripcion,
                ud.descripcion AS ubicacion_destino_descripcion,
                em.tipo_movimiento,
                em.observaciones
            FROM equipo_movimiento em
            LEFT JOIN ubicacion uo ON em.id_ubicacion_origen = uo.id_ubicacion
            LEFT JOIN ubicacion ud ON em.id_ubicacion_destino = ud.id_ubicacion
            WHERE em.id_equipo = %s
            ORDER BY em.fecha_movimiento DESC
            """,
            (equipment_id,),
        )
        return cur.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)