/*
 * Bitacora de ejecuciones. El Control Flow del paquete SSIS debe:
 *   1) INSERT en esta tabla al iniciar (obtiene id_carga con SCOPE_IDENTITY()).
 *   2) Guardar id_carga en una variable de paquete y usarla en todo el Data Flow.
 *   3) UPDATE con los conteos finales al terminar.
 *
 * Esto es lo que te permite, en el informe, mostrar y comparar las 3
 * iteraciones (un registro por cada una) y demostrar que un mismo lote
 * reprocesado no duplica datos (ver 05_final_y_revision.sql).
 */
USE DesaparicionPersonasETL;
GO

IF OBJECT_ID('control.control_cargas') IS NOT NULL
    DROP TABLE control.control_cargas;
GO

CREATE TABLE control.control_cargas (
    id_carga                INT IDENTITY(1,1) PRIMARY KEY,
    iteracion               INT NOT NULL,
    fecha_ejecucion         DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
    archivo_origen          NVARCHAR(300) NULL,
    registros_recibidos     INT NULL,
    registros_aceptados     INT NULL,
    registros_duplicados    INT NULL,
    registros_revision      INT NULL,
    completitud_pct_antes   DECIMAL(5,2) NULL,
    completitud_pct_despues DECIMAL(5,2) NULL,
    notas                   NVARCHAR(MAX) NULL
);
GO
