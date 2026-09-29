/*
 * Tabla FINAL (limpia, tipada) y tabla de REVISION (cuarentena).
 *
 * Clave para la idempotencia: id_registro es UNIQUE en la tabla final.
 * En el Data Flow, el segundo LOOKUP (contra esta misma tabla, por
 * id_registro) redirige a "no insertar" cualquier fila que ya exista --
 * asi, volver a correr el mismo CSV no genera duplicados (punto 6 de la guia).
 */
USE DesaparicionPersonasETL;
GO

IF OBJECT_ID('dbo.desaparecidos_final') IS NOT NULL
    DROP TABLE dbo.desaparecidos_final;
GO

CREATE TABLE dbo.desaparecidos_final (
    id_registro                NVARCHAR(100)   NOT NULL,
    id_original                NVARCHAR(100)   NULL,
    fuente                     NVARCHAR(100)   NOT NULL,
    nivel_fuente                NVARCHAR(50)    NOT NULL,
    unidad_de_analisis          NVARCHAR(50)    NULL,
    num_personas                INT             NULL,
    tipo_evento                 NVARCHAR(200)   NULL,
    estado_victima              NVARCHAR(100)   NULL,
    sexo                        NVARCHAR(50)    NULL,
    edad                        SMALLINT        NULL,
    anio                        SMALLINT        NULL,
    mes                         TINYINT         NULL,
    fecha                       DATE            NULL,
    pais                        NVARCHAR(100)   NULL,
    region                      NVARCHAR(100)   NULL,
    departamento                NVARCHAR(150)   NULL,
    municipio                   NVARCHAR(150)   NULL,
    codigo_dane_departamento    INT             NULL,
    codigo_dane_municipio       INT             NULL,
    latitud                     DECIMAL(9,6)    NULL,
    longitud                    DECIMAL(9,6)    NULL,
    detalle                     NVARCHAR(300)   NULL,
    narrativa                   NVARCHAR(MAX)   NULL,
    num_personas_atipico        BIT             NOT NULL DEFAULT 0,
    anio_atipico                 BIT             NOT NULL DEFAULT 0,
    id_carga                     INT             NOT NULL,
    fecha_proceso                DATETIME2       NOT NULL DEFAULT SYSDATETIME(),
    CONSTRAINT uq_desaparecidos_final_id_registro UNIQUE (id_registro)
);
GO

IF OBJECT_ID('revision.desaparecidos_pendientes') IS NOT NULL
    DROP TABLE revision.desaparecidos_pendientes;
GO

CREATE TABLE revision.desaparecidos_pendientes (
    revision_id                 INT IDENTITY(1,1) PRIMARY KEY,
    id_registro                  NVARCHAR(100)   NULL,
    id_original                  NVARCHAR(100)   NULL,
    fuente                       NVARCHAR(100)   NULL,
    campo_conflictivo            NVARCHAR(100)   NOT NULL,   -- ej: 'anio', 'tipo_evento', 'duplicado'
    valor_original               NVARCHAR(MAX)   NULL,       -- el valor tal cual llego, SIN modificar
    motivo_revision              NVARCHAR(300)   NOT NULL,   -- ej: 'anio fuera de [1974,2046] segun IQR'
    fila_completa_json           NVARCHAR(MAX)   NULL,       -- fila entera serializada, para no perder contexto
    id_carga                     INT             NOT NULL,
    fecha_proceso                DATETIME2       NOT NULL DEFAULT SYSDATETIME()
);
GO
