/*
 * Zona de staging: espejo 1:1 del CSV consolidado, TODO como NVARCHAR.
 * No se valida ni se convierte nada aqui -- es la copia "cruda" que garantiza
 * trazabilidad (siempre puedes volver a este dato tal como llego del CSV).
 *
 * id_carga: identifica cada ejecucion/iteracion del paquete (lo genera el
 * Control Flow con una variable de tipo GUID o un entero desde control.control_cargas).
 */
USE DesaparicionPersonasETL;
GO

IF OBJECT_ID('staging.desaparecidos_raw') IS NOT NULL
    DROP TABLE staging.desaparecidos_raw;
GO

CREATE TABLE staging.desaparecidos_raw (
    fila_staging_id           INT IDENTITY(1,1) PRIMARY KEY,
    id_carga                  INT NOT NULL,
    fecha_carga               DATETIME2 NOT NULL DEFAULT SYSDATETIME(),

    id_registro                NVARCHAR(100),
    id_original                NVARCHAR(100),
    fuente                     NVARCHAR(100),
    nivel_fuente               NVARCHAR(50),
    unidad_de_analisis         NVARCHAR(50),
    num_personas               NVARCHAR(50),
    tipo_evento                NVARCHAR(200),
    estado_victima             NVARCHAR(100),
    sexo                       NVARCHAR(50),
    edad                       NVARCHAR(50),
    anio                       NVARCHAR(50),
    mes                        NVARCHAR(50),
    fecha                      NVARCHAR(50),
    pais                       NVARCHAR(100),
    region                     NVARCHAR(100),
    departamento               NVARCHAR(150),
    municipio                  NVARCHAR(150),
    codigo_dane_departamento   NVARCHAR(50),
    codigo_dane_municipio      NVARCHAR(50),
    latitud                    NVARCHAR(50),
    longitud                   NVARCHAR(50),
    detalle                    NVARCHAR(300),
    narrativa                  NVARCHAR(MAX)
);
GO

-- Util para depurar una carga puntual sin perder el historial de otras cargas
CREATE INDEX ix_staging_id_carga ON staging.desaparecidos_raw(id_carga);
GO
