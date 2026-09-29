# Etapa 3 · Proceso ETL con SSIS

Carga `data/processed/dataset_consolidado.csv` (337.444 registros) en la base
`DesaparicionPersonasETL`, aplicando las reglas de tratamiento de la Etapa 2.

## Contenido

| Ruta | Descripción |
|---|---|
| `ssis/ETL_Principal.dtsx` | Paquete SSIS (Control Flow + Data Flow `ETL Principal`) |
| `sql/01_crear_esquema.sql` | Base de datos y esquemas `staging`, `ref`, `revision`, `control` |
| `sql/02_staging.sql` | `staging.desaparecidos_raw`: copia cruda del CSV |
| `sql/03_referencia_tipo_evento.sql` | Catálogo `ref.tipo_evento_homologado` (Lookup) |
| `sql/04_control_cargas.sql` | Bitácora `control.control_cargas` |
| `sql/05_final_y_revision.sql` | `dbo.desaparecidos_final` y `revision.desaparecidos_pendientes` |
| `resultados/iteraciones.json` | Conteos y ajustes de las tres iteraciones (lo usa la app Flask) |

El informe técnico está en `static/etapa3/informe_tecnico_etl.pdf`.

## Requisitos

- SQL Server (LocalDB, Express o Developer) y `sqlcmd`.
- Visual Studio con la extensión **SQL Server Integration Services Projects**.
- Git LFS para descargar `data/processed/dataset_consolidado.csv`.

## Pasos

1. Crear la base y las tablas, en orden (`-f 65001` conserva los acentos del catálogo):

   ```powershell
   $srv = "(localdb)\MSSQLLocalDB"
   foreach ($f in "01_crear_esquema","02_staging","03_referencia_tipo_evento","04_control_cargas","05_final_y_revision") {
       sqlcmd -S $srv -f 65001 -i "etl\sql\$f.sql"
   }
   ```

2. Abrir `etl/ssis/ETL_Principal.dtsx` en Visual Studio (agregarlo a un proyecto de
   Integration Services si hace falta).
3. En **Administradores de conexión**:
   - `CM_CSV_Consolidado`: apuntar a `data\processed\dataset_consolidado.csv` de tu copia del repositorio.
   - `CM_SQL`: servidor `(localdb)\MSSQLLocalDB`, base `DesaparicionPersonasETL`, autenticación de Windows.
4. Asignar la variable `User::Iteracion` (1, 2 o 3) y ejecutar el paquete.
5. Revisar los resultados:

   ```sql
   SELECT id_carga, iteracion, registros_recibidos, registros_aceptados,
          registros_duplicados, registros_revision
   FROM control.control_cargas ORDER BY id_carga;
   ```

Para repetir la prueba de idempotencia, ejecutar el paquete dos veces sin vaciar
`dbo.desaparecidos_final`: la segunda ejecución debe dejar `registros_aceptados = 0`.

## Credenciales

El paquete usa seguridad integrada de Windows; no contiene usuarios ni contraseñas.
Antes de publicar, dejar la propiedad `ProtectionLevel` del paquete en `DontSaveSensitive`.
