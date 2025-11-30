from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
import os
from datetime import date

app = FastAPI(title="Provider Service")

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

class ProviderBase(BaseModel):
    ruc: str
    razon_social: str
    nombre_comercial: str
    direccion: str
    telefono: str
    email: str
    estado: bool = True

class ProviderCreate(ProviderBase):
    pass

class Provider(ProviderBase):
    id_proveedor: int

    class Config:
        orm_mode = True

class Purchase(BaseModel):
    id_compra: int
    numero_documento: str
    fecha_compra: date
    monto_total: Optional[float]
    codigo_contrato: Optional[str]
    descripcion: Optional[str]

    class Config:
        orm_mode = True

class PurchaseDetail(BaseModel):
    id_compra_detalle: int
    id_compra: int
    id_equipo: Optional[int] = None
    codigo_inventario: Optional[str] = None
    numero_serie: Optional[str] = None
    tipo: Optional[str] = None
    marca: Optional[str] = None
    cantidad: float
    costo_unitario: float
    subtotal: float

    class Config:
        orm_mode = True

class ContractBase(BaseModel):
    id_proveedor: int
    codigo_contrato: str
    descripcion: str
    fecha_inicio: date
    fecha_fin: Optional[date] = None
    monto_total: Optional[float] = None
    tipo_contrato: Optional[str] = None
    estado: Optional[str] = None

class ContractCreate(ContractBase):
    pass

class Contract(ContractBase):
    id_contrato: int

    class Config:
        orm_mode = True

@app.post("/providers/", response_model=Provider)
def create_provider(provider: ProviderCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO proveedor (
                ruc, razon_social, nombre_comercial, direccion, 
                telefono, email, estado
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            provider.ruc, provider.razon_social, provider.nombre_comercial,
            provider.direccion, provider.telefono, provider.email, provider.estado
        ))
        new_provider = cur.fetchone()
        conn.commit()
        return new_provider
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/providers/", response_model=List[Provider])
def list_providers():
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT * FROM proveedor")
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

@app.post("/contracts/", response_model=Contract)
def create_contract(contract: ContractCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO contrato (
                id_proveedor, codigo_contrato, descripcion, fecha_inicio,
                fecha_fin, monto_total, tipo_contrato, estado
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            contract.id_proveedor, contract.codigo_contrato, contract.descripcion,
            contract.fecha_inicio, contract.fecha_fin, contract.monto_total,
            contract.tipo_contrato, contract.estado
        ))
        new_contract = cur.fetchone()
        conn.commit()
        return new_contract
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()

@app.get("/providers/{provider_id}/contracts", response_model=List[Contract])
def list_provider_contracts(provider_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT * FROM contrato 
            WHERE id_proveedor = %s
        """, (provider_id,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

@app.get("/providers/{provider_id}/purchases", response_model=List[Purchase])
def list_provider_purchases(provider_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT 
                c.id_compra,
                c.numero_documento,
                c.fecha_compra,
                c.monto_total,
                ct.codigo_contrato,
                ct.descripcion
            FROM compra c
            LEFT JOIN contrato ct ON c.id_contrato = ct.id_contrato
            WHERE c.id_proveedor = %s
            ORDER BY c.fecha_compra DESC
        """, (provider_id,))
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

@app.get(
    "/providers/{provider_id}/purchases/{purchase_id}/details",
    response_model=List[PurchaseDetail],
)
def list_purchase_details(provider_id: int, purchase_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT
                cd.id_compra_detalle,
                cd.id_compra,
                cd.id_equipo,
                e.codigo_inventario,
                e.numero_serie,
                e.tipo,
                e.marca,
                cd.cantidad,
                cd.costo_unitario,
                (cd.cantidad * cd.costo_unitario) AS subtotal
            FROM compra_detalle cd
            LEFT JOIN equipo e ON cd.id_equipo = e.id_equipo
            WHERE cd.id_compra = %s
            ORDER BY cd.id_compra_detalle
            """,
            (purchase_id,),
        )
        return cur.fetchall()
    finally:
        cur.close()
        conn.close()

@app.put("/providers/{provider_id}", response_model=Provider)
def update_provider(provider_id: int, provider: ProviderCreate):
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE proveedor
            SET 
                ruc = %s,
                razon_social = %s,
                nombre_comercial = %s,
                direccion = %s,
                telefono = %s,
                email = %s,
                estado = %s
            WHERE id_proveedor = %s
            RETURNING *
        """, (
            provider.ruc,
            provider.razon_social,
            provider.nombre_comercial,
            provider.direccion,
            provider.telefono,
            provider.email,
            provider.estado,
            provider_id
        ))
        updated = cur.fetchone()
        if not updated:
            raise HTTPException(status_code=404, detail="Proveedor no encontrado")
        conn.commit()
        return updated
    except HTTPException:
        conn.rollback()
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)