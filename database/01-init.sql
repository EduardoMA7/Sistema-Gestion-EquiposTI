CREATE TABLE unidad_organizativa (
    id_unidad          BIGSERIAL PRIMARY KEY,
    nombre             TEXT NOT NULL
);

CREATE TABLE ubicacion (
    id_ubicacion       BIGSERIAL PRIMARY KEY,
    id_unidad          BIGINT REFERENCES unidad_organizativa(id_unidad),
    descripcion        TEXT NOT NULL,
    estado             BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE equipo (
    id_equipo              BIGSERIAL PRIMARY KEY,
    codigo_inventario      VARCHAR(50) UNIQUE NOT NULL,
    numero_serie           VARCHAR(100) UNIQUE NOT NULL,
    tipo                   VARCHAR(50) NOT NULL,
    marca                  VARCHAR(50) NOT NULL,
    estado                 VARCHAR(30) NOT NULL,
    id_ubicacion_actual    BIGINT REFERENCES ubicacion(id_ubicacion),
    vida_util_meses        INTEGER,
    observaciones          TEXT
);

CREATE TABLE proveedor (
    id_proveedor       BIGSERIAL PRIMARY KEY,
    ruc                VARCHAR(11) UNIQUE NOT NULL,
    razon_social       TEXT NOT NULL,
    nombre_comercial   TEXT NOT NULL,
    direccion          TEXT NOT NULL,
    telefono           VARCHAR(9) NOT NULL,
    email              VARCHAR(255) NOT NULL,
    estado             BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE contrato (
    id_contrato        BIGSERIAL PRIMARY KEY,
    id_proveedor       BIGINT NOT NULL REFERENCES proveedor(id_proveedor),
    codigo_contrato    VARCHAR(50) UNIQUE NOT NULL,
    descripcion        TEXT NOT NULL,
    fecha_inicio       DATE NOT NULL,
    fecha_fin          DATE,
    monto_total        NUMERIC(14,2),
    tipo_contrato      VARCHAR(50),
    estado             VARCHAR(30)
);

CREATE TABLE compra (
    id_compra          BIGSERIAL PRIMARY KEY,
    id_proveedor       BIGINT NOT NULL REFERENCES proveedor(id_proveedor),
    id_contrato        BIGINT REFERENCES contrato(id_contrato),
    numero_documento   VARCHAR(50) NOT NULL,
    fecha_compra       DATE NOT NULL,
    monto_total        NUMERIC(14,2)
);

CREATE TABLE compra_detalle (
    id_compra_detalle  BIGSERIAL PRIMARY KEY,
    id_compra          BIGINT NOT NULL REFERENCES compra(id_compra) ON DELETE CASCADE,
    id_equipo          BIGINT REFERENCES equipo(id_equipo),
    cantidad           NUMERIC(10,2) NOT NULL,
    costo_unitario     NUMERIC(14,2) NOT NULL
);

CREATE TABLE equipo_movimiento (
    id_movimiento              BIGSERIAL PRIMARY KEY,
    id_equipo                  BIGINT NOT NULL REFERENCES equipo(id_equipo) ON DELETE CASCADE,
    fecha_movimiento           TIMESTAMPTZ NOT NULL,
    id_ubicacion_origen        BIGINT REFERENCES ubicacion(id_ubicacion),
    id_ubicacion_destino       BIGINT REFERENCES ubicacion(id_ubicacion),
    tipo_movimiento            VARCHAR(30) NOT NULL,
    observaciones              TEXT
);

CREATE TABLE mantenimiento (
    id_mantenimiento       BIGSERIAL PRIMARY KEY,
    id_equipo              BIGINT NOT NULL REFERENCES equipo(id_equipo),
    tipo_mantenimiento     VARCHAR(20) NOT NULL,
    estado_mantenimiento   VARCHAR(20) NOT NULL,
    prioridad              VARCHAR(20),
    fecha_solicitud        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    fecha_programada       DATE,
    fecha_inicio           TIMESTAMPTZ,
    fecha_fin              TIMESTAMPTZ,
    costo_mano_obra        NUMERIC(14,2),
    costo_repuestos        NUMERIC(14,2),
    costo_total            NUMERIC(14,2) GENERATED ALWAYS AS
                           (COALESCE(costo_mano_obra,0) + COALESCE(costo_repuestos,0)) STORED
);

CREATE TABLE mantenimiento_repuesto (
    id_repuesto            BIGSERIAL PRIMARY KEY,
    id_mantenimiento       BIGINT NOT NULL REFERENCES mantenimiento(id_mantenimiento) ON DELETE CASCADE,
    descripcion            TEXT NOT NULL,
    cantidad               NUMERIC(10,2) NOT NULL,
    costo_unitario         NUMERIC(14,2) NOT NULL,
    subtotal               NUMERIC(14,2) GENERATED ALWAYS AS (cantidad * costo_unitario) STORED
);