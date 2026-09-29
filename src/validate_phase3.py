"""Validate the Phase 3 country-year energy-transition model."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from paths import ANALYTICS_DIR, PHASE3_REPORT_DIR, ensure_directories


def check(name: str, status: str, actual: Any, expected: str, detail: str) -> dict[str, Any]:
    return {
        "check": name,
        "status": status,
        "actual": actual,
        "expected": expected,
        "detail": detail,
    }


def validate_phase3() -> dict[str, Any]:
    ensure_directories()
    fact = pd.read_csv(ANALYTICS_DIR / "fact_country_energy_year.csv", low_memory=False)
    entities = pd.read_csv(ANALYTICS_DIR / "dim_energy_entity.csv")
    coverage = pd.read_csv(ANALYTICS_DIR / "mart_energy_year_coverage.csv")
    momentum = pd.read_csv(ANALYTICS_DIR / "mart_transition_momentum.csv")
    config = json.loads(
        (ANALYTICS_DIR / "phase3_model_config.json").read_text(encoding="utf-8")
    )
    results: list[dict[str, Any]] = []

    duplicate_keys = int(fact.duplicated(["entity_code", "year"], keep=False).sum())
    results.append(check("entity_year_unique", "PASS" if duplicate_keys == 0 else "FAIL", duplicate_keys, "0", "Entity-year harus unik."))

    country_count = int(entities["entity_type"].eq("country").sum())
    world_count = int(entities["entity_type"].eq("world").sum())
    results.append(check("country_entity_count", "PASS" if country_count == 167 else "FAIL", country_count, "167", "Seluruh country keys dari model aset harus tersedia."))
    results.append(check("world_entity_count", "PASS" if world_count == 1 else "FAIL", world_count, "1", "Agregat World memakai key OWID_WRL."))

    invalid_entity_links = int((~fact["entity_code"].isin(entities["entity_code"])).sum())
    results.append(check("entity_mapping_complete", "PASS" if invalid_entity_links == 0 else "FAIL", invalid_entity_links, "0", "Semua fact rows harus memiliki dimension entity."))

    share_columns = [column for column in fact.columns if column.endswith("_share_pct")]
    invalid_shares = int(
        sum((~fact[column].dropna().between(-1e-9, 100 + 1e-9)).sum() for column in share_columns)
    )
    results.append(check("electricity_shares_in_range", "PASS" if invalid_shares == 0 else "FAIL", invalid_shares, "0", "Seluruh share listrik harus berada pada 0-100%."))

    components = fact[["low_carbon_share_pct", "renewables_share_pct", "nuclear_share_pct"]].dropna()
    low_carbon_difference = (
        components["low_carbon_share_pct"]
        - components["renewables_share_pct"]
        - components["nuclear_share_pct"]
    ).abs()
    invalid_low_carbon = int((low_carbon_difference > 0.01).sum())
    results.append(check("low_carbon_share_definition", "PASS" if invalid_low_carbon == 0 else "FAIL", invalid_low_carbon, "0 at 0.01 pp tolerance", "Low-carbon share harus sama dengan renewable + nuclear ketika ketiganya tersedia."))

    negative_generation_columns = [
        "electricity_generation_twh",
        "fossil_electricity_twh",
        "renewables_electricity_twh",
        "nuclear_electricity_twh",
        "low_carbon_electricity_twh",
    ]
    negative_generation = int(
        sum((fact[column].dropna() < 0).sum() for column in negative_generation_columns)
    )
    results.append(check("generation_non_negative", "PASS" if negative_generation == 0 else "FAIL", negative_generation, "0", "Generation TWh tidak boleh negatif."))

    comparable_count = int(momentum["has_comparable_endpoints"].sum())
    results.append(check("default_period_coverage", "WARN" if comparable_count < 167 else "PASS", comparable_count, "167 preferred", f"Comparable endpoints {config['default_start_year']}-{config['default_end_year']}; ATA dan ESH tidak memiliki seri lengkap."))

    latest_year = int(fact["year"].max())
    latest_coverage = coverage.loc[
        coverage["year"].eq(latest_year), "countries_with_renewable_share"
    ].iloc[0]
    results.append(check("latest_year_coverage", "WARN" if latest_coverage < 160 else "PASS", int(latest_coverage), "at least 160 entities", "Tahun paling baru tetap tersedia untuk eksplorasi tetapi bukan endpoint ranking default."))

    world = fact[fact["entity_code"].eq("OWID_WRL")]
    world_endpoint_rows = int(
        world["year"].isin([config["default_start_year"], config["default_end_year"]]).sum()
    )
    results.append(check("world_default_endpoints", "PASS" if world_endpoint_rows == 2 else "FAIL", world_endpoint_rows, "2", "World harus memiliki start dan end year default."))

    result_frame = pd.DataFrame(results)
    overall = (
        "FAIL"
        if result_frame["status"].eq("FAIL").any()
        else "PASS_WITH_WARNINGS"
        if result_frame["status"].eq("WARN").any()
        else "PASS"
    )
    summary = {
        "overall_status": overall,
        "pass_count": int(result_frame["status"].eq("PASS").sum()),
        "warning_count": int(result_frame["status"].eq("WARN").sum()),
        "fail_count": int(result_frame["status"].eq("FAIL").sum()),
        "checks": results,
    }
    result_frame.to_csv(PHASE3_REPORT_DIR / "validation_results.csv", index=False)
    (PHASE3_REPORT_DIR / "validation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    lines = [
        "# Laporan Validasi Tren Transisi — Fase 3",
        "",
        f"**Status keseluruhan:** {overall}",
        "",
        f"- Pass: {summary['pass_count']}",
        f"- Warning: {summary['warning_count']}",
        f"- Fail: {summary['fail_count']}",
        "",
        "| Pemeriksaan | Status | Aktual | Ekspektasi | Keterangan |",
        "|---|---:|---|---|---|",
    ]
    for item in results:
        actual = str(item["actual"]).replace("|", "\\|")
        detail = str(item["detail"]).replace("|", "\\|")
        lines.append(
            f"| {item['check']} | {item['status']} | {actual} | {item['expected']} | {detail} |"
        )
    (PHASE3_REPORT_DIR / "validation_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(f"Validasi Fase 3 selesai: {overall}")
    return summary


if __name__ == "__main__":
    validate_phase3()
