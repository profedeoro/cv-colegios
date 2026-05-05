-- Tabla principal: un colegio por fila
CREATE TABLE IF NOT EXISTS colegios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    nombre_normalizado TEXT NOT NULL,
    ciudad TEXT NOT NULL,
    departamento TEXT NOT NULL,
    nit TEXT,
    web TEXT,
    correo TEXT,
    correo_destinatario TEXT,
    fuente TEXT NOT NULL,
    perfil_pedagogico TEXT,        -- JSON
    palabras_clave TEXT,           -- JSON list
    estado TEXT NOT NULL DEFAULT 'descubierto',
    intentos_enriquecer INTEGER NOT NULL DEFAULT 0,
    intentos_generar INTEGER NOT NULL DEFAULT 0,
    fecha_descubierto DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_enriquecido DATETIME,
    fecha_envio DATETIME,
    fecha_respuesta DATETIME,
    gmail_draft_id TEXT,
    gmail_thread_id TEXT,
    notas TEXT,
    CHECK (estado IN (
        'descubierto', 'enriquecido', 'sin_correo', 'borrador_creado',
        'enviado', 'respondió', 'rebotó', 'seguimiento_pendiente',
        'sin_respuesta', 'descartado', 'error', 'revisar_manualmente'
    ))
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_colegios_dedup
    ON colegios(nombre_normalizado, ciudad);

CREATE UNIQUE INDEX IF NOT EXISTS ix_colegios_nit
    ON colegios(nit) WHERE nit IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_colegios_estado ON colegios(estado);
CREATE INDEX IF NOT EXISTS ix_colegios_thread ON colegios(gmail_thread_id);

-- Tabla de borradores generados (un colegio puede tener varios: inicial + seguimiento)
CREATE TABLE IF NOT EXISTS borradores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    colegio_id INTEGER NOT NULL REFERENCES colegios(id) ON DELETE RESTRICT,
    tipo TEXT NOT NULL CHECK (tipo IN ('inicial', 'seguimiento')),
    asunto TEXT NOT NULL,
    cuerpo_carta TEXT NOT NULL,
    ruta_pdf_hv TEXT,
    estado TEXT NOT NULL DEFAULT 'listo_para_subir'
        CHECK (estado IN ('listo_para_subir', 'subido', 'fallo')),
    gmail_draft_id TEXT,
    fecha_creado DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_subido DATETIME,
    error_mensaje TEXT
);

CREATE INDEX IF NOT EXISTS ix_borradores_estado ON borradores(estado);
CREATE INDEX IF NOT EXISTS ix_borradores_colegio ON borradores(colegio_id);

-- Tabla de auditoría de ejecuciones
CREATE TABLE IF NOT EXISTS registro_ejecuciones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    modulo TEXT NOT NULL,
    fecha DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    duracion_segundos REAL,
    estado TEXT NOT NULL CHECK (estado IN ('ok', 'error')),
    colegios_procesados INTEGER NOT NULL DEFAULT 0,
    mensaje TEXT,
    costo_api_usd REAL NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS ix_registro_modulo_fecha
    ON registro_ejecuciones(modulo, fecha);

-- Tabla de metadatos clave-valor (para hash del CV, versión, etc.)
CREATE TABLE IF NOT EXISTS metadatos (
    clave TEXT PRIMARY KEY,
    valor TEXT NOT NULL,
    fecha_actualizacion DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
