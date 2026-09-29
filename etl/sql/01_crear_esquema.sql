/*
 * Etapa 3 - ETL con SSIS
 * Crea la base de datos y los 4 esquemas usados por el paquete:
 *   staging  -> copia cruda del CSV, sin tipos ni validaciones (trazabilidad)
 *   ref      -> tablas de referencia/homologacion (Lookup)
 *   revision -> registros que no pasan las reglas, con el valor original y el motivo
 *   control  -> bitacora de cada ejecucion/iteracion (conteos, para comparar y evitar duplicados)
 *
 * Ejecutar una sola vez antes de abrir el proyecto de SSIS.
 */

IF DB_ID('DesaparicionPersonasETL') IS NULL
BEGIN
    CREATE DATABASE DesaparicionPersonasETL;
END
GO

USE DesaparicionPersonasETL;
GO

IF SCHEMA_ID('staging') IS NULL EXEC('CREATE SCHEMA staging');
IF SCHEMA_ID('ref')      IS NULL EXEC('CREATE SCHEMA ref');
IF SCHEMA_ID('revision') IS NULL EXEC('CREATE SCHEMA revision');
IF SCHEMA_ID('control')  IS NULL EXEC('CREATE SCHEMA control');
GO
