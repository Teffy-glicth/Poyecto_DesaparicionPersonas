SELECT 'dim_tiempo'    AS tabla, id_tiempo    AS clave, COUNT(*) AS repeticiones FROM dim_tiempo    GROUP BY id_tiempo    HAVING COUNT(*) > 1;
SELECT 'dim_geografia' AS tabla, id_geografia AS clave, COUNT(*) AS repeticiones FROM dim_geografia GROUP BY id_geografia HAVING COUNT(*) > 1;
SELECT 'dim_zona'      AS tabla, id_zona      AS clave, COUNT(*) AS repeticiones FROM dim_zona      GROUP BY id_zona      HAVING COUNT(*) > 1;
SELECT 'dim_victima'   AS tabla, id_victima   AS clave, COUNT(*) AS repeticiones FROM dim_victima   GROUP BY id_victima   HAVING COUNT(*) > 1;
SELECT 'dim_estado'    AS tabla, id_estado    AS clave, COUNT(*) AS repeticiones FROM dim_estado    GROUP BY id_estado    HAVING COUNT(*) > 1;
SELECT 'dim_fuente'    AS tabla, id_fuente    AS clave, COUNT(*) AS repeticiones FROM dim_fuente    GROUP BY id_fuente    HAVING COUNT(*) > 1;

SELECT COUNT(*) FROM fact_desaparicion f LEFT JOIN dim_tiempo    d ON f.id_tiempo = d.id_tiempo       WHERE d.id_tiempo    IS NULL;
SELECT COUNT(*) FROM fact_desaparicion f LEFT JOIN dim_geografia d ON f.id_geografia = d.id_geografia WHERE d.id_geografia IS NULL;
SELECT COUNT(*) FROM fact_desaparicion f LEFT JOIN dim_zona      d ON f.id_zona = d.id_zona           WHERE d.id_zona      IS NULL;
SELECT COUNT(*) FROM fact_desaparicion f LEFT JOIN dim_victima   d ON f.id_victima = d.id_victima     WHERE d.id_victima   IS NULL;
SELECT COUNT(*) FROM fact_desaparicion f LEFT JOIN dim_estado    d ON f.id_estado = d.id_estado       WHERE d.id_estado    IS NULL;
SELECT COUNT(*) FROM fact_desaparicion f LEFT JOIN dim_fuente    d ON f.id_fuente = d.id_fuente       WHERE d.id_fuente    IS NULL;

SELECT id_registro, COUNT(*) AS repeticiones FROM fact_desaparicion GROUP BY id_registro HAVING COUNT(*) > 1;

SELECT 'id_tiempo'    AS dimension, COUNT(*) AS hechos FROM fact_desaparicion WHERE id_tiempo    = 0
UNION ALL
SELECT 'id_geografia' AS dimension, COUNT(*) AS hechos FROM fact_desaparicion WHERE id_geografia = 0
UNION ALL
SELECT 'id_zona'      AS dimension, COUNT(*) AS hechos FROM fact_desaparicion WHERE id_zona      = 0
UNION ALL
SELECT 'id_victima'   AS dimension, COUNT(*) AS hechos FROM fact_desaparicion WHERE id_victima   = 0
UNION ALL
SELECT 'id_estado'    AS dimension, COUNT(*) AS hechos FROM fact_desaparicion WHERE id_estado    = 0
UNION ALL
SELECT 'id_fuente'    AS dimension, COUNT(*) AS hechos FROM fact_desaparicion WHERE id_fuente    = 0;
