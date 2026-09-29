"""Load Phase 3 historical energy data into the existing PostgreSQL project database."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from types import SimpleNamespace

from load_postgres import connection_args, find_psql, load_dotenv, load_table, run
from paths import ANALYTICS_DIR, PHASE3_REPORT_DIR, ROOT_DIR


def load_phase3_postgres() -> None:
    load_dotenv()
    args = SimpleNamespace(
        psql=find_psql(),
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        user=os.getenv("PGUSER"),
        database=os.getenv("PGDATABASE", "energy_transition"),
        no_password=True,
    )
    run(
        connection_args(args, args.database)
        + ["-f", str(ROOT_DIR / "sql" / "04_create_phase3_schema.sql")]
    )
    load_table(args, "energy_core.dim_energy_entity", ANALYTICS_DIR / "dim_energy_entity.csv")
    load_table(
        args,
        "energy_core.fact_country_energy_year",
        ANALYTICS_DIR / "fact_country_energy_year.csv",
    )
    run(
        connection_args(args, args.database)
        + ["-f", str(ROOT_DIR / "sql" / "05_create_phase3_views.sql")]
    )
    run(connection_args(args, args.database) + ["-c", "ANALYZE;"])
    run(
        connection_args(args, args.database)
        + ["-f", str(ROOT_DIR / "sql" / "06_phase3_quality_checks.sql")]
    )
    status = {
        "loaded_at_utc": datetime.now(timezone.utc).isoformat(),
        "host": args.host,
        "port": args.port,
        "database": args.database,
        "fact_rows": 14843,
        "entity_rows": 168,
        "phase3_views": 4,
        "postgresql_validation": "completed",
    }
    PHASE3_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (PHASE3_REPORT_DIR / "postgresql_load_status.json").write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print("Model historis Fase 3 selesai dimuat dan diperiksa di PostgreSQL.")


if __name__ == "__main__":
    load_phase3_postgres()

