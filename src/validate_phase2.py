"""Validate Phase 2 analytical marts before they are loaded to PostgreSQL or BI."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from paths import ANALYTICS_DIR, FACT_POWER_PLANT_FILE, PHASE2_REPORT_DIR, ensure_directories


TOLERANCE_MW = 0.000001


def check(name: str, status: str, actual: Any, expected: str, detail: str) -> dict[str, Any]:
    return {
        "check": name,
        "status": status,
        "actual": actual,
        "expected": expected,
        "detail": detail,
    }


def validate_phase2() -> dict[str, Any]:
    ensure_directories()
    phase1 = pd.read_csv(FACT_POWER_PLANT_FILE, low_memory=False)
    fact = pd.read_csv(ANALYTICS_DIR / "fact_power_plant.csv", low_memory=False)
    global_kpi = pd.read_csv(ANALYTICS_DIR / "mart_global_kpi.csv")
    country = pd.read_csv(ANALYTICS_DIR / "mart_country_kpi.csv")
    country_fuel = pd.read_csv(ANALYTICS_DIR / "mart_country_fuel.csv")
    dim_country = pd.read_csv(ANALYTICS_DIR / "dim_country.csv")
    dim_fuel = pd.read_csv(ANALYTICS_DIR / "dim_fuel.csv")
    config = json.loads((ANALYTICS_DIR / "model_config.json").read_text(encoding="utf-8"))
    results: list[dict[str, Any]] = []

    results.append(
        check(
            "reference_year",
            "PASS" if config["reference_year"] == 2020 else "FAIL",
            config["reference_year"],
            "2020",
            "Reference year harus selaras dengan snapshot aset, bukan tahun kalender saat ini.",
        )
    )

    results.append(
        check(
            "fact_row_count_reconciled",
            "PASS" if len(fact) == len(phase1) else "FAIL",
            len(fact),
            str(len(phase1)),
            "Fase 2 tidak boleh menghapus atau menggandakan pembangkit.",
        )
    )
    phase1_capacity = float(phase1["capacity_mw"].sum())
    fact_capacity = float(fact["capacity_mw"].sum())
    capacity_difference = abs(phase1_capacity - fact_capacity)
    results.append(
        check(
            "fact_capacity_reconciled",
            "PASS" if capacity_difference < TOLERANCE_MW else "FAIL",
            capacity_difference,
            f"< {TOLERANCE_MW} MW",
            f"Phase 1={phase1_capacity:.6f}; Phase 2={fact_capacity:.6f} MW.",
        )
    )

    global_capacity = float(global_kpi.loc[0, "total_capacity_mw"])
    country_capacity = float(country["total_capacity_mw"].sum())
    global_country_difference = abs(global_capacity - country_capacity)
    results.append(
        check(
            "global_country_capacity_reconciled",
            "PASS" if global_country_difference < TOLERANCE_MW else "FAIL",
            global_country_difference,
            f"< {TOLERANCE_MW} MW",
            "Jumlah mart negara harus sama dengan KPI global.",
        )
    )

    share_columns = [
        "fossil_share_pct",
        "renewable_share_pct",
        "nuclear_share_pct",
        "low_carbon_share_pct",
        "other_share_pct",
        "coal_dependency_pct",
        "age_coverage_by_capacity_pct",
        "unknown_commissioning_capacity_share_pct",
    ]
    invalid_shares = int(
        sum((~country[column].dropna().between(-1e-9, 100 + 1e-9)).sum() for column in share_columns)
    )
    results.append(check("country_shares_in_range", "PASS" if invalid_shares == 0 else "FAIL", invalid_shares, "0", "Semua persentase negara harus berada pada rentang 0-100%."))

    component_total = (
        country["fossil_share_pct"]
        + country["renewable_share_pct"]
        + country["nuclear_share_pct"]
        + country["other_share_pct"]
    )
    invalid_component_totals = int((component_total.sub(100).abs() > 1e-6).sum())
    results.append(check("country_group_mix_sums_to_100", "PASS" if invalid_component_totals == 0 else "FAIL", invalid_component_totals, "0", "Fossil + renewable + nuclear + other harus berjumlah 100%."))

    low_carbon_difference = (
        country["low_carbon_capacity_mw"]
        - country["renewable_capacity_mw"]
        - country["nuclear_capacity_mw"]
    ).abs()
    invalid_low_carbon = int((low_carbon_difference > TOLERANCE_MW).sum())
    results.append(check("low_carbon_definition", "PASS" if invalid_low_carbon == 0 else "FAIL", invalid_low_carbon, "0", "Low carbon harus sama dengan renewable + nuclear."))

    mix_totals = country_fuel.groupby("country_iso3")["country_capacity_share_pct"].sum()
    invalid_fuel_mix = int((mix_totals.sub(100).abs() > 1e-6).sum())
    results.append(check("country_fuel_mix_sums_to_100", "PASS" if invalid_fuel_mix == 0 else "FAIL", invalid_fuel_mix, "0", "Primary-fuel mix per negara harus berjumlah 100%."))

    negative_ages = int((pd.to_numeric(fact["plant_age_years"], errors="coerce") < 0).sum())
    results.append(check("plant_age_non_negative", "PASS" if negative_ages == 0 else "FAIL", negative_ages, "0", "Plant age tidak boleh negatif."))

    known_unknown_difference = (
        country["known_age_capacity_mw"]
        + country["unknown_commissioning_capacity_mw"]
        - country["total_capacity_mw"]
    ).abs()
    invalid_known_unknown = int((known_unknown_difference > TOLERANCE_MW).sum())
    results.append(check("known_unknown_age_capacity_reconciled", "PASS" if invalid_known_unknown == 0 else "FAIL", invalid_known_unknown, "0", "Known + unknown commissioning capacity harus sama dengan total kapasitas."))

    expected_age_bands = {"0-14 years", "15-29 years", "30-39 years", "40+ years", "Unknown"}
    actual_age_bands = set(fact["age_band"].dropna())
    results.append(check("age_band_domain", "PASS" if actual_age_bands == expected_age_bands else "FAIL", sorted(actual_age_bands), str(sorted(expected_age_bands)), "Age band harus memakai domain terdokumentasi."))

    unmatched = dim_country.loc[
        dim_country["world_bank_match_status"].eq("unmatched"), "country_iso3"
    ].tolist()
    results.append(check("world_bank_country_coverage", "WARN" if unmatched else "PASS", len(unmatched), "0 preferred", f"Unmatched dipertahankan sebagai kategori eksplisit: {', '.join(unmatched) or 'none'}."))

    fuel_mapping_count = len(dim_fuel)
    results.append(check("fuel_dimension_complete", "PASS" if fuel_mapping_count == 15 else "FAIL", fuel_mapping_count, "15", "Semua primary fuel WRI harus tersedia pada dimension."))

    postgres_status = PHASE2_REPORT_DIR / "postgresql_load_status.json"
    results.append(
        check(
            "postgresql_load_verified",
            "PASS" if postgres_status.exists() else "WARN",
            "loaded" if postgres_status.exists() else "not yet loaded",
            "loaded",
            "Schema SQL dan loader sudah tersedia; status PASS dibuat setelah load PostgreSQL berhasil.",
        )
    )

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
    result_frame.to_csv(PHASE2_REPORT_DIR / "validation_results.csv", index=False)
    (PHASE2_REPORT_DIR / "validation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    lines = [
        "# Laporan Validasi Model Analitik — Fase 2",
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
        detail = str(item["detail"]).replace("|", "\\|")
        actual = str(item["actual"]).replace("|", "\\|")
        lines.append(
            f"| {item['check']} | {item['status']} | {actual} | {item['expected']} | {detail} |"
        )
    (PHASE2_REPORT_DIR / "validation_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print(f"Validasi Fase 2 selesai: {overall}")
    return summary


if __name__ == "__main__":
    validate_phase2()

