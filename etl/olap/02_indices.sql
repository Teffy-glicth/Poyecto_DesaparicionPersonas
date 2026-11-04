CREATE INDEX IF NOT EXISTS ix_fact_tiempo    ON fact_desaparicion (id_tiempo);
CREATE INDEX IF NOT EXISTS ix_fact_geografia ON fact_desaparicion (id_geografia);
CREATE INDEX IF NOT EXISTS ix_fact_zona      ON fact_desaparicion (id_zona);
CREATE INDEX IF NOT EXISTS ix_fact_victima   ON fact_desaparicion (id_victima);
CREATE INDEX IF NOT EXISTS ix_fact_estado    ON fact_desaparicion (id_estado);
CREATE INDEX IF NOT EXISTS ix_fact_fuente    ON fact_desaparicion (id_fuente);

CREATE INDEX IF NOT EXISTS ix_geografia_depto ON dim_geografia (departamento);
CREATE INDEX IF NOT EXISTS ix_tiempo_anio     ON dim_tiempo (anio);
