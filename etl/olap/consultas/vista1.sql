SELECT
    v.sexo,
    SUM(h.num_personas)                                   AS personas,
    SUM(h.flag_aparecio_viva) * 100.0 / SUM(h.num_personas) AS pct_aparecio_con_vida
FROM fact_desaparicion h
JOIN dim_victima v ON h.id_victima = v.id_victima
WHERE v.sexo IN ('Hombre', 'Mujer')
GROUP BY v.sexo;

SELECT
    v.sexo,
    e.estado_victima,
    SUM(h.num_personas) AS personas
FROM fact_desaparicion h
JOIN dim_victima v ON h.id_victima = v.id_victima
JOIN dim_estado  e ON h.id_estado = e.id_estado
GROUP BY v.sexo, e.estado_victima
ORDER BY v.sexo, e.estado_victima;

SELECT
    t.anio,
    v.sexo,
    SUM(h.num_personas)                                   AS personas,
    SUM(h.flag_aparecio_viva) * 100.0 / SUM(h.num_personas) AS pct_aparecio_con_vida
FROM fact_desaparicion h
JOIN dim_tiempo  t ON h.id_tiempo = t.id_tiempo
JOIN dim_victima v ON h.id_victima = v.id_victima
WHERE t.anio IS NOT NULL AND v.sexo IN ('Hombre', 'Mujer')
GROUP BY t.anio, v.sexo
ORDER BY t.anio, v.sexo;

SELECT
    v.sexo,
    e.estado_victima,
    SUM(h.num_personas) AS personas
FROM fact_desaparicion h
JOIN dim_victima v ON h.id_victima = v.id_victima
JOIN dim_estado  e ON h.id_estado = e.id_estado
GROUP BY v.sexo, e.estado_victima;

SELECT
    v.sexo,
    e.estado_victima,
    SUM(h.num_personas) AS personas
FROM fact_desaparicion h
JOIN dim_victima v ON h.id_victima = v.id_victima
JOIN dim_estado  e ON h.id_estado = e.id_estado
JOIN dim_fuente  f ON h.id_fuente = f.id_fuente
WHERE f.fuente = 'SIEVCAC (CNMH)'
GROUP BY v.sexo, e.estado_victima;

SELECT
    e.estado_victima,
    v.sexo,
    SUM(h.num_personas) AS personas
FROM fact_desaparicion h
JOIN dim_estado  e ON h.id_estado = e.id_estado
JOIN dim_victima v ON h.id_victima = v.id_victima
GROUP BY e.estado_victima, v.sexo;

SELECT
    f.fuente,
    t.periodo_acuerdo,
    v.sexo,
    e.estado_victima,
    SUM(h.num_personas) AS personas
FROM fact_desaparicion h
JOIN dim_fuente  f ON h.id_fuente = f.id_fuente
JOIN dim_tiempo  t ON h.id_tiempo = t.id_tiempo
JOIN dim_victima v ON h.id_victima = v.id_victima
JOIN dim_estado  e ON h.id_estado = e.id_estado
GROUP BY f.fuente, t.periodo_acuerdo, v.sexo, e.estado_victima
ORDER BY f.fuente, t.periodo_acuerdo, v.sexo, e.estado_victima;
