PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS fact_desaparicion;
DROP TABLE IF EXISTS dim_tiempo;
DROP TABLE IF EXISTS dim_geografia;
DROP TABLE IF EXISTS dim_zona;
DROP TABLE IF EXISTS dim_victima;
DROP TABLE IF EXISTS dim_estado;
DROP TABLE IF EXISTS dim_fuente;

CREATE TABLE dim_tiempo (
    id_tiempo       INTEGER PRIMARY KEY,
    anio            INTEGER,
    semestre        INTEGER,
    trimestre       INTEGER,
    mes             INTEGER,
    nombre_mes      TEXT,
    periodo_acuerdo TEXT NOT NULL
);

CREATE TABLE dim_geografia (
    id_geografia             INTEGER PRIMARY KEY,
    macro_region             TEXT NOT NULL,
    codigo_dane_departamento TEXT,
    departamento             TEXT NOT NULL,
    codigo_dane_municipio    TEXT,
    municipio                TEXT NOT NULL,
    UNIQUE (departamento, municipio)
);

CREATE TABLE dim_zona (
    id_zona    INTEGER PRIMARY KEY,
    zona_hecho TEXT NOT NULL UNIQUE
);

CREATE TABLE dim_victima (
    id_victima      INTEGER PRIMARY KEY,
    sexo            TEXT NOT NULL,
    calidad_victima TEXT NOT NULL,
    UNIQUE (sexo, calidad_victima)
);

CREATE TABLE dim_estado (
    id_estado       INTEGER PRIMARY KEY,
    grupo_desenlace TEXT NOT NULL,
    estado_victima  TEXT NOT NULL UNIQUE
);

CREATE TABLE dim_fuente (
    id_fuente    INTEGER PRIMARY KEY,
    fuente       TEXT NOT NULL,
    tipo_evento  TEXT NOT NULL,
    nivel_fuente TEXT NOT NULL,
    UNIQUE (fuente, tipo_evento)
);

CREATE TABLE fact_desaparicion (
    id_hecho                 INTEGER PRIMARY KEY AUTOINCREMENT,
    id_registro              TEXT NOT NULL UNIQUE,
    id_tiempo                INTEGER NOT NULL,
    id_geografia              INTEGER NOT NULL,
    id_zona                  INTEGER NOT NULL,
    id_victima                INTEGER NOT NULL,
    id_estado                INTEGER NOT NULL,
    id_fuente                INTEGER NOT NULL,
    num_personas              INTEGER NOT NULL DEFAULT 1,
    flag_sigue_desaparecida   INTEGER NOT NULL CHECK (flag_sigue_desaparecida IN (0, 1)),
    flag_aparecio_viva        INTEGER NOT NULL CHECK (flag_aparecio_viva IN (0, 1)),
    flag_aparecio_sin_vida    INTEGER NOT NULL CHECK (flag_aparecio_sin_vida IN (0, 1)),
    FOREIGN KEY (id_tiempo)    REFERENCES dim_tiempo (id_tiempo),
    FOREIGN KEY (id_geografia) REFERENCES dim_geografia (id_geografia),
    FOREIGN KEY (id_zona)      REFERENCES dim_zona (id_zona),
    FOREIGN KEY (id_victima)   REFERENCES dim_victima (id_victima),
    FOREIGN KEY (id_estado)    REFERENCES dim_estado (id_estado),
    FOREIGN KEY (id_fuente)    REFERENCES dim_fuente (id_fuente)
);
