# Mapeo de variables — Etapa 5

De `data/processed/dataset_tratado.csv` (Etapa 2) a las tablas del modelo estrella,
cargado por `scripts/cargar_modelo_estrella.py`. Solo se usan las filas con
`fuente` en {`Medicina Legal (SIRDEC)`, `SIEVCAC (CNMH)`} y
`unidad_de_analisis = "persona"` (288.396 de 337.416 filas del CSV tratado); ver
`docs/etapa5/diccionario_modelo.md` para la justificación de ese filtro.

## 1. Variable original → campo del modelo

| Variable en `dataset_tratado.csv` | Campo del modelo | Transformación |
|---|---|---|
| `id_registro` | `fact_desaparicion.id_registro` | Se copia tal cual (ya es único en el CSV tratado). |
| `anio`, `mes` | `fact_desaparicion.id_tiempo` → `dim_tiempo` | `id_tiempo = anio*100 + mes`; `anio*100` si falta el mes; `0` si falta el año. Ver la sección "Dos niveles de 'falta información'" en el diccionario. |
| `departamento` | `dim_geografia.departamento`, `.macro_region` | Normalización de formato + corrección de codificación (sección 2). `macro_region = "Sur"` si el departamento normalizado está en {Nariño, Cauca, Putumayo, Caquetá, Huila}, si no `"Resto"`. |
| `municipio` | `dim_geografia.municipio` | `str.title()` tras limpiar el caracter de reemplazo Unicode; si el valor (ya limpio) es alguna variante de "sin información", queda exactamente `"Sin informacion"` (evita un duplicado case-sensitive contra la clave 0). |
| `codigo_dane_departamento`, `codigo_dane_municipio` | `dim_geografia.codigo_dane_departamento`, `.codigo_dane_municipio` | El CSV los trae como texto de un float (`"11001.0"`); se recorta el sufijo `".0"`. `NULL` cuando faltan (toda SIEVCAC para departamento; casos del extranjero para ambos). |
| `detalle` (solo filas de Medicina Legal) | `fact_desaparicion.id_zona` → `dim_zona.zona_hecho` | Mismo valor, con la codificación corregida (sección 2). En SIEVCAC, `detalle` guarda otra cosa (ver `calidad_victima` abajo), así que a esas filas se les asigna `id_zona = 0`. |
| `sexo` | `dim_victima.sexo` | `str.title()`; vacío o nulo → `"Sin informacion"`. |
| `detalle` (solo filas de SIEVCAC) | `fact_desaparicion.id_victima` (parte) → `dim_victima.calidad_victima` | Mismo valor, con la codificación corregida. En Medicina Legal, que no reporta esta variable, queda `"Sin informacion"`. |
| `estado_victima` | `fact_desaparicion.id_estado` → `dim_estado.estado_victima`, `.grupo_desenlace` | Se copia tal cual; `grupo_desenlace` se deriva: `"Desaparecido"` → `"Sin resolver"`; `"Aparecido con vida"`/`"Aparecido sin vida"` → `"Resuelto"`. |
| `estado_victima` | `fact_desaparicion.flag_sigue_desaparecida`, `.flag_aparecio_viva`, `.flag_aparecio_sin_vida` | Un flag 0/1 derivado por comparación directa con cada valor de `estado_victima` (para poder sumarlos con SQL sin `CASE` en cada consulta). |
| `fuente`, `tipo_evento`, `nivel_fuente` | `dim_fuente.fuente`, `.tipo_evento`, `.nivel_fuente` | Se copian tal cual (ya vienen limpios del tratamiento de la Etapa 2). |
| — | `fact_desaparicion.num_personas` | Constante `1` (cada fila del CSV tratado, en este subconjunto, ya es una persona). |

Variables del CSV tratado que **no** se usan en este modelo: `id_original` (trazabilidad
interna de la Etapa 2, no aporta una dimensión nueva), `edad` (100 % nula en Medicina
Legal y SIEVCAC — ver `data/diccionario_datos.json`), `pais` (constante "Colombia" para
estas dos fuentes), `latitud`/`longitud` (sin agregar valor sobre `departamento`/
`municipio` para este análisis), `narrativa` (texto libre, exclusivo de las fuentes
primarias que aquí se excluyen), `num_personas_atipico`/`anio_atipico` (banderas de
calidad de la Etapa 2, ya resueltas en el tratamiento).

## 2. Transformaciones adicionales (no son un simple renombre)

1. **Dos formatos de texto por fuente.** Medicina Legal entrega `departamento` en
   formato título (`"Antioquia"`) y SIEVCAC en mayúsculas (`"ANTIOQUIA"`) — detectado en
   la Etapa 4. `normalizar_departamento()` usa un mapa explícito de 36 categorías
   (33 departamentos + Bogotá D.C. ya contado, "Desaparecidos en el extranjero",
   "Exterior" y "Sin informacion") para que ambos formatos caigan en el mismo valor
   canónico, sin inventar departamentos nuevos.
2. **Corrección de codificación.** Un tramo anterior del pipeline perdió el acento de
   algunas palabras (quedó el caracter de reemplazo Unicode `�` en vez de la vocal
   acentuada: `"informaci�n"`, `"Nari�o"`, `"Boyac�"`, etc.) en `departamento` y en
   `detalle`. Como el dominio de ambas columnas es cerrado y conocido (36 departamentos,
   4 valores de zona, 3 de calidad de la víctima), se corrige con el mismo mapa
   explícito en vez de intentar adivinar el caracter perdido.
3. **`id_tiempo` con dos niveles de "sin dato".** Ver la fila de `anio`/`mes` arriba y la
   sección correspondiente en `docs/etapa5/diccionario_modelo.md`: separar "sin año" de
   "con año, sin mes" evita que 818 personas desaparezcan de los conteos anuales por no
   tener mes.
4. **Clave 0 por dimensión.** Cada dimensión trae un miembro `"Sin informacion"` de
   clave `0` (excepto `dim_victima`, donde "Sin informacion" ya es una combinación real
   de `sexo`/`calidad_victima` que sale de los datos, así que no hace falta inventar una
   fila aparte). Esto evita FK nulas en `fact_desaparicion` y hace que los faltantes se
   vean como una fila más en las matrices, en vez de desaparecer silenciosamente.
5. **`detalle` es una columna compartida con dos significados.** Según la fuente, la
   misma columna del CSV tratado representa cosas distintas (zona del hecho en Medicina
   Legal, calidad de la víctima en SIEVCAC); el script la reparte hacia `dim_zona` o
   `dim_victima.calidad_victima` según el valor de `fuente`, y pone `"Sin informacion"`
   del lado que no aplica.

## 3. Verificación

`scripts/cargar_modelo_estrella.py` corre dos aserciones antes de escribir la base de
datos: que `id_registro` siga siendo único en `fact_desaparicion` (no se duplicó
ninguna fila al cruzar con las dimensiones) y que el número de filas cargadas sea
exactamente igual al número de filas filtradas del CSV tratado (ninguna relación
dimensión↔hecho multiplicó valores). Las comprobaciones adicionales contra el CSV de
origen están en `scripts/validar_modelo.py` (ver `data/olap/validaciones.json`).
