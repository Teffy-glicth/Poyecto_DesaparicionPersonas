-- Vista 4 · Perfiles combinados
-- Cada % se calcula como SUM(flag) * 100.0 / SUM(num_personas) dentro del grupo.
-- Parámetros (?): fuente (siempre) y, opcionalmente, macro_region, departamento,
-- zona_hecho y sexo (Dice). Se agregan como "AND columna = ?" al WHERE.

-- 1. Indicadores: personas y % sin resolver de la combinación seleccionada
SELECT SUM(h.num_personas) AS personas,
       SUM(h.flag_sigue_desaparecida) AS siguen_desaparecidas,
       SUM(h.flag_sigue_desaparecida) * 100.0 / SUM(h.num_personas) AS pct_siguen_desaparecidas
FROM fact_desaparicion h
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_zona z      ON h.id_zona = z.id_zona
JOIN dim_victima v   ON h.id_victima = v.id_victima
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
WHERE f.fuente = ?;

-- 2. Referencia para la diferencia en pp: mismo cálculo solo con la fuente
--    (WHERE f.fuente = ?, sin los demás cortes).

-- 3. Gráfica 1: % sin resolver por sexo + zona
SELECT v.sexo, z.zona_hecho,
       SUM(h.num_personas) AS personas,
       SUM(h.flag_sigue_desaparecida) * 100.0 / SUM(h.num_personas) AS pct_siguen_desaparecidas
FROM fact_desaparicion h
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_zona z      ON h.id_zona = z.id_zona
JOIN dim_victima v   ON h.id_victima = v.id_victima
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
WHERE f.fuente = ?
GROUP BY v.sexo, z.zona_hecho
ORDER BY pct_siguen_desaparecidas DESC;

-- 4. Gráfica 2: estado por zona (el % por zona se calcula con el total de cada zona)
SELECT z.zona_hecho, e.grupo_desenlace, SUM(h.num_personas) AS personas
FROM fact_desaparicion h
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_zona z      ON h.id_zona = z.id_zona
JOIN dim_victima v   ON h.id_victima = v.id_victima
JOIN dim_estado e    ON h.id_estado = e.id_estado
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
WHERE f.fuente = ?
GROUP BY z.zona_hecho, e.grupo_desenlace;

-- 5. Matriz zona × sexo (Pivot: GROUP BY v.sexo, z.zona_hecho, que se vuelve a consultar)
SELECT z.zona_hecho, v.sexo,
       SUM(h.num_personas) AS personas,
       SUM(h.flag_sigue_desaparecida) * 100.0 / SUM(h.num_personas) AS pct_siguen_desaparecidas
FROM fact_desaparicion h
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_zona z      ON h.id_zona = z.id_zona
JOIN dim_victima v   ON h.id_victima = v.id_victima
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
WHERE f.fuente = ?
GROUP BY z.zona_hecho, v.sexo;

-- 6. Ranking sexo + zona + departamento (se filtran en Python n >= 30 y "Sin informacion")
SELECT v.sexo, z.zona_hecho, g.departamento,
       SUM(h.num_personas) AS personas,
       SUM(h.flag_sigue_desaparecida) * 100.0 / SUM(h.num_personas) AS pct_siguen_desaparecidas
FROM fact_desaparicion h
JOIN dim_geografia g ON h.id_geografia = g.id_geografia
JOIN dim_zona z      ON h.id_zona = z.id_zona
JOIN dim_victima v   ON h.id_victima = v.id_victima
JOIN dim_fuente f    ON h.id_fuente = f.id_fuente
WHERE f.fuente = ?
GROUP BY v.sexo, z.zona_hecho, g.departamento
HAVING SUM(h.num_personas) >= 30
ORDER BY pct_siguen_desaparecidas DESC;

-- 7. Dice (ejemplo): tres dimensiones a la vez
--    WHERE f.fuente = ? AND g.macro_region = 'Sur'
--      AND z.zona_hecho = 'Rural disperso' AND v.sexo = 'Hombre'