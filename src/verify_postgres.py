"""Reconcile PostgreSQL analytical views with the generated Phase 2 marts."""

from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pandas as pd

from load_postgres import connection_args, find_psql, load_dotenv, run
from paths import ANALYTICS_DIR, PHASE2_REPORT_DIR


TOLERANCE = 0.000001


def scalar_query(args: SimpleNamespace, query: str) -> str:
    result = run(
        connection_args(args, args.database) + ["-A", "-t", "-c", query],
        capture=True,
    )
    return result.stdout.strip()


def verify_postgres() -> dict[str, object]:
    load_dotenv()
    args = SimpleNamespace(
        psql=find_psql(),
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        user=os.getenv("PGUSER"),
        database=os.getenv("PGDATABASE", "energy_transition"),
        no_password=True,
    )

    postgres_global = json.loads(
        scalar_query(
            args,
            """
            SELECT json_build_object(
                'total_plants', total_plants,
                'total_capacity_mw', total_capacity_mw,
                'fossil_share_pct', fossil_share_pct,
                'renewable_share_pct', renewable_share_pct,
                'low_carbon_share_pct', low_carbon_share_pct,
                'age_coverage_by_capacity_pct', age_coverage_by_capacity_pct
            )::text
            FROM energy_analytics.v_global_kpi;
            """,
        )
    )
    local_global = pd.read_csv(ANALYTICS_DIR / "mart_global_kpi.csv").iloc[0]

    metrics = [
        "total_plants",
        "total_capacity_mw",
        "fossil_share_pct",
        "renewable_share_pct",
        "low_carbon_share_pct",
        "age_coverage_by_capacity_pct",
    ]
    comparisons: list[dict[str, object]] = []
    for metric in metrics:
        database_value = float(postgres_global[metric])
        local_value = float(local_global[metric])
        difference = abs(database_value - local_value)
        comparisons.append(
            {
                "metric": metric,
                "postgresql": database_value,
                "local_mart": local_value,
                "absolute_difference": difference,
                "status": "PASS" if difference < TOLERANCE else "FAIL",
            }
        )

    database_counts = {
        "fact_rows": int(
            scalar_query(args, "SELECT COUNT(*) FROM energy_core.fact_power_plant;")
        ),
        "country_rows": int(
            scalar_query(args, "SELECT COUNT(*) FROM energy_core.dim_country;")
        ),
        "fuel_rows": int(scalar_query(args, "SELECT COUNT(*) FROM energy_core.dim_fuel;")),
        "analytical_views": int(
            scalar_query(
                args,
                "SELECT COUNT(*) FROM pg_views WHERE schemaname = 'energy_analytics';",
            )
        ),
    }
    count_expectations = {
        "fact_rows": 34936,
        "country_rows": 167,
        "fuel_rows": 15,
        "analytical_views": 9,
    }
    count_status = {
        key: "PASS" if database_counts[key] == expected else "FAIL"
        for key, expected in count_expectations.items()
    }

    failed_metrics = [item for item in comparisons if item["status"] == "FAIL"]
    failed_counts = [key for key, status in count_status.items() if status == "FAIL"]
    summary: dict[str, object] = {
        "overall_status": "PASS" if not failed_metrics and not failed_counts else "FAIL",
        "database": args.database,
        "host": args.host,
        "counts": database_counts,
        "count_expectations": count_expectations,
        "count_status": count_status,
        "metric_comparisons": comparisons,
    }
    PHASE2_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (PHASE2_REPORT_DIR / "postgresql_verification.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Verifikasi PostgreSQL selesai: {summary['overall_status']}")
    return summary


if __name__ == "__main__":
    verify_postgres()

