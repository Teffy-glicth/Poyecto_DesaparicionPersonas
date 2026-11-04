-- Vista 2 · Territorio
-- ¿Qué departamentos y municipios concentran a las personas que siguen desaparecidas
-- y cómo cambia el porcentaje al bajar de macrorregión a municipio?
-- Todas las consultas usan Medicina Legal (SIRDEC) salvo la 9, que compara con SIEVCAC.
-- Los % siempre se recalculan con SUM(flag)/SUM(num_personas) del grupo mostrado; nunca
-- se promedian los % de los hijos (ver la caja de comprobación de la vista).

-- 1. Nivel macrorregión (Sur vs. Resto del país): punto de partida de la vista.
SELECT
    g.macro_region,
    SUM(h.num_personas)                                        AS personas,
    SUM(h.flag_sigue_desaparecida)                             AS siguen_desaparecidas,
    SUM(h.flag_sigue_desaparecida) * 100.0 / SUM(h.num_personas) AS pct_siguen_desaparecidas
FROM fact_desaparicion h
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
WHERE f.fuente = 'Medicina Legal (SIRDEC)'
GROUP BY g.macro_region
ORDER BY g.macro_region;

-- 2. Drill-down: de macrorregión a departamento, dentro del Sur.
SELECT
    g.departamento,
    SUM(h.num_personas)                                        AS personas,
    SUM(h.flag_sigue_desaparecida)                             AS siguen_desaparecidas,
    SUM(h.flag_sigue_desaparecida) * 100.0 / SUM(h.num_personas) AS pct_siguen_desaparecidas
FROM fact_desaparicion h
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
WHERE f.fuente = 'Medicina Legal (SIRDEC)'
  AND g.macro_region = 'Sur'
GROUP BY g.departamento
ORDER BY siguen_desaparecidas DESC;

-- 3. Drill-down: de departamento a municipio, dentro de Huila.
SELECT
    g.municipio,
    SUM(h.num_personas)                                        AS personas,
    SUM(h.flag_sigue_desaparecida)                             AS siguen_desaparecidas,
    SUM(h.flag_sigue_desaparecida) * 100.0 / SUM(h.num_personas) AS pct_siguen_desaparecidas
FROM fact_desaparicion h
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
WHERE f.fuente = 'Medicina Legal (SIRDEC)'
  AND g.macro_region = 'Sur'
  AND g.departamento = 'Huila'
GROUP BY g.municipio
ORDER BY siguen_desaparecidas DESC;

-- 4. Huila sin Neiva: aísla el peso de la capital sobre el % del departamento.
SELECT
    SUM(h.num_personas)                                        AS personas,
    SUM(h.flag_sigue_desaparecida)                             AS siguen_desaparecidas,
    SUM(h.flag_sigue_desaparecida) * 100.0 / SUM(h.num_personas) AS pct_siguen_desaparecidas
FROM fact_desaparicion h
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
WHERE f.fuente = 'Medicina Legal (SIRDEC)'
  AND g.departamento = 'Huila'
  AND g.municipio <> 'Neiva';

-- 5. Roll-up: de municipio de vuelta a los departamentos del Sur. El % de cada
--    departamento sale de sus propias personas, no del promedio de sus municipios.
SELECT
    g.departamento,
    SUM(h.num_personas)                                        AS personas,
    SUM(h.flag_sigue_desaparecida)                             AS siguen_desaparecidas,
    SUM(h.flag_sigue_desaparecida) * 100.0 / SUM(h.num_personas) AS pct_siguen_desaparecidas
FROM fact_desaparicion h
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
WHERE f.fuente = 'Medicina Legal (SIRDEC)'
  AND g.macro_region = 'Sur'
GROUP BY g.departamento
ORDER BY g.departamento;

-- 6. Totales de la selección activa (indicadores 1 y 2, y denominador de la comprobación).
SELECT
    SUM(h.num_personas)                                        AS personas,
    SUM(h.flag_sigue_desaparecida)                             AS siguen_desaparecidas,
    SUM(h.flag_sigue_desaparecida) * 100.0 / SUM(h.num_personas) AS pct_siguen_desaparecidas
FROM fact_desaparicion h
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
WHERE f.fuente = 'Medicina Legal (SIRDEC)'
  AND g.macro_region = 'Sur';

-- 7. Municipios afectados (indicador 3: conteo distinto, no aditivo). En la app se
--    descartan como municipio real las categorías "Sin informacion" y
--    "Desaparecidos En El Extranjero" antes de contar las filas.
SELECT
    g.departamento,
    g.municipio,
    SUM(h.num_personas) AS personas
FROM fact_desaparicion h
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
WHERE f.fuente = 'Medicina Legal (SIRDEC)'
  AND g.macro_region = 'Sur'
GROUP BY g.departamento, g.municipio;

-- 8. Ranking de los municipios del Sur por personas que siguen desaparecidas: alimenta
--    el top 10 de las gráficas 1 (volumen) y 2 (%) de la vista.
SELECT
    g.municipio,
    SUM(h.num_personas)                                        AS personas,
    SUM(h.flag_sigue_desaparecida)                             AS siguen_desaparecidas,
    SUM(h.flag_sigue_desaparecida) * 100.0 / SUM(h.num_personas) AS pct_siguen_desaparecidas
FROM fact_desaparicion h
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
WHERE f.fuente = 'Medicina Legal (SIRDEC)'
  AND g.macro_region = 'Sur'
GROUP BY g.municipio
ORDER BY siguen_desaparecidas DESC
LIMIT 10;

-- 9. Comparación con SIEVCAC: los mismos municipios de Huila, con la fuente del
--    conflicto armado, para ver si la excepción de Huila se mantiene o desaparece.
SELECT
    g.municipio,
    SUM(h.num_personas)                                        AS personas,
    SUM(h.flag_sigue_desaparecida)                             AS siguen_desaparecidas,
    SUM(h.flag_sigue_desaparecida) * 100.0 / SUM(h.num_personas) AS pct_siguen_desaparecidas
FROM fact_desaparicion h
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
WHERE f.fuente = 'SIEVCAC (CNMH)'
  AND g.departamento = 'Huila'
GROUP BY g.municipio
ORDER BY siguen_desaparecidas DESC;

-- 10. Matriz de la vista: nivel geográfico actual × grupo de desenlace (personas;
--     el % por fila, usado para el mapa de calor, lo calcula static/js/olap.js
--     sobre esta misma consulta, nunca promediando porcentajes ya calculados).
SELECT
    g.departamento,
    e.grupo_desenlace,
    SUM(h.num_personas) AS personas
FROM fact_desaparicion h
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_estado e    ON h.id_estado = e.id_estado
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
WHERE f.fuente = 'Medicina Legal (SIRDEC)'
  AND g.macro_region = 'Sur'
GROUP BY g.departamento, e.grupo_desenlace
ORDER BY g.departamento, e.grupo_desenlace;
