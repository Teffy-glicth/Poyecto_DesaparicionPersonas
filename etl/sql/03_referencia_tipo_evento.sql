/*
 * Tabla de referencia para el componente LOOKUP que homologa 'tipo_evento'.
 * Contiene las 11 variantes reales encontradas en el dataset consolidado
 * (data/processed/dataset_consolidado.parquet) y su etiqueta canonica.
 *
 * Solo 'Desplazamiento ' (con un espacio NBSP invisible al final, \xa0)
 * necesita normalizarse de verdad; el resto ya mapea a si misma. Se listan
 * las 11 igual para que el Lookup nunca falle por "no match" con datos ya
 * conocidos (todo lo que no este en esta tabla cae al flujo de revision).
 *
 * IMPORTANTE: este archivo tiene acentos (UTF-8). Si lo ejecutas con
 * sqlcmd, usa el flag -f 65001. Si lo abres y ejecutas desde el Explorador
 * de objetos de SQL Server en Visual Studio, no necesitas nada especial.
 */
USE DesaparicionPersonasETL;
GO

IF OBJECT_ID('ref.tipo_evento_homologado') IS NOT NULL
    DROP TABLE ref.tipo_evento_homologado;
GO

CREATE TABLE ref.tipo_evento_homologado (
    valor_origen    NVARCHAR(200) NOT NULL PRIMARY KEY,
    valor_canonico  NVARCHAR(200) NOT NULL
);
GO

INSERT INTO ref.tipo_evento_homologado (valor_origen, valor_canonico) VALUES
    (N'Abduccion/desaparicion forzada (conflicto armado)', N'Abduccion/desaparicion forzada (conflicto armado)'),
    (N'Accidente',                                          N'Accidente'),
    (N'Desaparicion forzada (conflicto armado)',             N'Desaparicion forzada (conflicto armado)'),
    (N'Desaparicion forzada (presunta)',                     N'Desaparicion forzada (presunta)'),
    (N'Desaparicion/muerte de persona migrante',             N'Desaparicion/muerte de persona migrante'),
    (N'Desaparición forzada',                                N'Desaparición forzada'),
    (N'Desconocida',                                         N'Desconocida'),
    (N'Desplazamiento' + NCHAR(160),                         N'Desplazamiento'),   -- NCHAR(160) = NBSP (\xa0), el caracter invisible real detectado
    (N'Otro',                                                N'Otro'),
    (N'Reclutamiento',                                       N'Reclutamiento'),
    (N'Sin informacion',                                     N'Sin informacion');
GO
