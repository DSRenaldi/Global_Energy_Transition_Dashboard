"""Run the Phase 4 cross-source, model, filter, and double-counting audit."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pandas as pd

from load_postgres import connection_args, find_psql, load_dotenv, run
from paths import (
    ANALYTICS_DIR,
    OWID_ENERGY_FILE,
    OWID_METADATA_FILE,
    PHASE2_REPORT_DIR,
    PHASE3_REPORT_DIR,
    PHASE4_REPORT_DIR,
    RAW_DATA_FILE,
    SOURCE_METADATA_FILE,
    ensure_directories,
)


CAPACITY_TOLERANCE_MW = 0.000001
METRIC_TOLERANCE = 0.000001


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(
    category: str,
    name: str,
    status: str,
    actual: Any,
    expected: str,
    detail: str,
) -> dict[str, Any]:
    return {
        "category": category,
        "check": name,
        "status": status,
        "actual": actual,
        "expected": expected,
        "detail": detail,
    }


def scalar_query(args: SimpleNamespace, query: str) -> str:
    result = run(
        connection_args(args, args.database) + ["-A", "-t", "-c", query],
        capture=True,
    )
    return result.stdout.strip()


def database_metrics(args: SimpleNamespace) -> dict[str, Any]:
    query = """
    SELECT json_build_object(
      'plant_rows', (SELECT COUNT(*) FROM energy_core.fact_power_plant),
      'plant_capacity_mw', (SELECT SUM(capacity_mw) FROM energy_core.fact_power_plant),
      'duplicate_plant_ids', (
        SELECT COUNT(*) FROM (
          SELECT plant_id FROM energy_core.fact_power_plant
          GROUP BY plant_id HAVING COUNT(*) > 1
        ) AS duplicates
      ),
      'duplicate_asset_signatures', (
        SELECT COUNT(*) FROM (
          SELECT country_iso3, LOWER(plant_name), latitude, longitude, capacity_mw
          FROM energy_core.fact_power_plant
          GROUP BY country_iso3, LOWER(plant_name), latitude, longitude, capacity_mw
          HAVING COUNT(*) > 1
        ) AS duplicates
      ),
      'plant_country_orphans', (
        SELECT COUNT(*) FROM energy_core.fact_power_plant AS f
        LEFT JOIN energy_core.dim_country AS d USING (country_iso3)
        WHERE d.country_iso3 IS NULL
      ),
      'plant_fuel_orphans', (
        SELECT COUNT(*) FROM energy_core.fact_power_plant AS f
        LEFT JOIN energy_core.dim_fuel AS d USING (fuel_key)
        WHERE d.fuel_key IS NULL
      ),
      'energy_rows', (SELECT COUNT(*) FROM energy_core.fact_country_energy_year),
      'duplicate_entity_years', (
        SELECT COUNT(*) FROM (
          SELECT entity_code, year FROM energy_core.fact_country_energy_year
          GROUP BY entity_code, year HAVING COUNT(*) > 1
        ) AS duplicates
      ),
      'energy_entity_orphans', (
        SELECT COUNT(*) FROM energy_core.fact_country_energy_year AS f
        LEFT JOIN energy_core.dim_energy_entity AS d USING (entity_code)
        WHERE d.entity_code IS NULL
      ),
      'country_capacity_mw', (SELECT SUM(total_capacity_mw) FROM energy_analytics.v_country_kpi),
      'fuel_capacity_mw', (SELECT SUM(capacity_mw) FROM energy_analytics.v_global_fuel),
      'region_capacity_mw', (SELECT SUM(total_capacity_mw) FROM energy_analytics.v_region_kpi),
      'age_band_capacity_mw', (SELECT SUM(capacity_mw) FROM energy_analytics.v_country_age_band),
      'global_capacity_mw', (SELECT total_capacity_mw FROM energy_analytics.v_global_kpi),
      'idn_capacity_direct_mw', (
        SELECT SUM(capacity_mw) FROM energy_core.fact_power_plant WHERE country_iso3 = 'IDN'
      ),
      'idn_capacity_view_mw', (
        SELECT total_capacity_mw FROM energy_analytics.v_country_kpi WHERE country_iso3 = 'IDN'
      ),
      'idn_renewable_direct_mw', (
        SELECT SUM(p.capacity_mw) FROM energy_core.fact_power_plant AS p
        JOIN energy_core.dim_fuel AS f USING (fuel_key)
        WHERE p.country_iso3 = 'IDN' AND f.is_renewable
      ),
      'idn_renewable_view_mw', (
        SELECT renewable_capacity_mw FROM energy_analytics.v_country_kpi WHERE country_iso3 = 'IDN'
      ),
      'ineligible_ranked_countries', (
        SELECT COUNT(*) FROM energy_analytics.v_country_ranking
        WHERE NOT eligible_for_share_ranking
          AND (renewable_share_rank_eligible IS NOT NULL
            OR low_carbon_share_rank_eligible IS NOT NULL
            OR coal_dependency_rank_eligible IS NOT NULL)
      ),
      'world_dimension_rows', (
        SELECT COUNT(*) FROM energy_core.dim_energy_entity
        WHERE entity_code = 'OWID_WRL' AND entity_type = 'world'
      ),
      'world_rows_in_country_momentum', (
        SELECT COUNT(*) FROM energy_analytics.v_transition_momentum_2005_2022
        WHERE entity_code = 'OWID_WRL'
      ),
      'default_filter_endpoint_rows', (
        SELECT COUNT(*) FROM energy_analytics.v_energy_trend
        WHERE entity_code = ANY(ARRAY['OWID_WRL','CHN','USA','IDN'])
          AND year IN (2005, 2022)
      ),
      'unmatched_world_bank_countries', (
        SELECT COUNT(*) FROM energy_core.dim_country WHERE world_bank_match_status = 'unmatched'
      ),
      'latest_renewable_coverage', (
        SELECT entities_with_renewable_share FROM energy_analytics.v_energy_year_coverage
        WHERE year = 2025
      )
    )::text;
    """
    return json.loads(scalar_query(args, query))


def validate_phase4() -> dict[str, Any]:
    ensure_directories()
    load_dotenv()
    args = SimpleNamespace(
        psql=find_psql(),
        host=os.getenv("PGHOST", "localhost"),
        port=int(os.getenv("PGPORT", "5432")),
        user=os.getenv("PGUSER"),
        database=os.getenv("PGDATABASE", "energy_transition"),
        no_password=True,
    )

    wri_metadata = json.loads(SOURCE_METADATA_FILE.read_text(encoding="utf-8"))
    owid_metadata = json.loads(OWID_METADATA_FILE.read_text(encoding="utf-8"))
    phase2_validation = json.loads(
        (PHASE2_REPORT_DIR / "validation_summary.json").read_text(encoding="utf-8")
    )
    phase3_validation = json.loads(
        (PHASE3_REPORT_DIR / "validation_summary.json").read_text(encoding="utf-8")
    )

    wri = pd.read_csv(RAW_DATA_FILE, usecols=["gppd_idnr", "capacity_mw"], low_memory=False)
    plants = pd.read_csv(
        ANALYTICS_DIR / "fact_power_plant.csv",
        usecols=["plant_id", "capacity_mw"],
        low_memory=False,
    )
    entities = pd.read_csv(ANALYTICS_DIR / "dim_energy_entity.csv")
    energy = pd.read_csv(
        ANALYTICS_DIR / "fact_country_energy_year.csv",
        usecols=["entity_code", "year", "renewables_share_pct", "fossil_share_pct"],
        low_memory=False,
    )
    owid = pd.read_csv(
        OWID_ENERGY_FILE,
        usecols=["country", "year", "iso_code", "renewables_share_elec", "fossil_share_elec"],
        low_memory=False,
    )
    owid.loc[owid["country"].eq("Kosovo"), "iso_code"] = "XKX"
    owid.loc[owid["country"].eq("World"), "iso_code"] = "OWID_WRL"
    selected_owid = owid[owid["iso_code"].isin(set(entities["entity_code"]))]
    db = database_metrics(args)
    results: list[dict[str, Any]] = []

    wri_hash = file_sha256(RAW_DATA_FILE)
    results.append(check("source", "wri_checksum", "PASS" if wri_hash == wri_metadata["sha256"] else "FAIL", wri_hash, wri_metadata["sha256"], "Snapshot WRI lokal harus identik dengan file yang dipatok."))
    expected_owid_hash = next(item["sha256"] for item in owid_metadata["files"] if item["local_file"] == OWID_ENERGY_FILE.name)
    owid_hash = file_sha256(OWID_ENERGY_FILE)
    results.append(check("source", "owid_checksum", "PASS" if owid_hash == expected_owid_hash else "FAIL", owid_hash, expected_owid_hash, "Snapshot OWID lokal harus identik dengan file yang dipatok."))

    raw_capacity = float(pd.to_numeric(wri["capacity_mw"], errors="coerce").sum())
    processed_capacity = float(plants["capacity_mw"].sum())
    capacity_spread = max(raw_capacity, processed_capacity, float(db["plant_capacity_mw"])) - min(raw_capacity, processed_capacity, float(db["plant_capacity_mw"]))
    results.append(check("reconciliation", "wri_row_count_end_to_end", "PASS" if len(wri) == len(plants) == int(db["plant_rows"]) else "FAIL", {"source": len(wri), "analytics": len(plants), "postgresql": int(db["plant_rows"])}, "all equal", "Tidak boleh ada aset hilang atau berlipat dari sumber ke database."))
    results.append(check("reconciliation", "wri_capacity_end_to_end", "PASS" if capacity_spread < CAPACITY_TOLERANCE_MW else "FAIL", capacity_spread, f"< {CAPACITY_TOLERANCE_MW} MW", f"Source={raw_capacity:.6f}; analytics={processed_capacity:.6f}; PostgreSQL={float(db['plant_capacity_mw']):.6f} MW."))
    results.append(check("reconciliation", "owid_row_count_end_to_end", "PASS" if len(selected_owid) == len(energy) == int(db["energy_rows"]) else "FAIL", {"source_selected": len(selected_owid), "analytics": len(energy), "postgresql": int(db["energy_rows"])}, "all equal", "Seleksi 167 negara/wilayah dan World harus konsisten sampai database."))

    endpoint_source = selected_owid[selected_owid["iso_code"].eq("OWID_WRL") & selected_owid["year"].isin([2005, 2022])].set_index("year")
    endpoint_model = energy[energy["entity_code"].eq("OWID_WRL") & energy["year"].isin([2005, 2022])].set_index("year")
    endpoint_difference = max(
        abs(float(endpoint_source.loc[year, source_col]) - float(endpoint_model.loc[year, model_col]))
        for year in (2005, 2022)
        for source_col, model_col in (("renewables_share_elec", "renewables_share_pct"), ("fossil_share_elec", "fossil_share_pct"))
    )
    results.append(check("reconciliation", "owid_world_endpoints_match", "PASS" if endpoint_difference < METRIC_TOLERANCE else "FAIL", endpoint_difference, f"< {METRIC_TOLERANCE} pp", "World renewable/fossil shares 2005 dan 2022 cocok dengan snapshot sumber."))

    for name, value, detail in [
        ("plant_id_unique", db["duplicate_plant_ids"], "Primary key aset tidak boleh berulang."),
        ("plant_country_relationship", db["plant_country_orphans"], "Seluruh aset harus terhubung ke dim_country."),
        ("plant_fuel_relationship", db["plant_fuel_orphans"], "Seluruh aset harus terhubung ke dim_fuel."),
        ("entity_year_unique", db["duplicate_entity_years"], "Grain historis adalah satu baris per entity-year."),
        ("energy_entity_relationship", db["energy_entity_orphans"], "Seluruh seri historis harus terhubung ke dim_energy_entity."),
        ("ineligible_share_rank_is_null", db["ineligible_ranked_countries"], "Negara <1 GW tidak boleh memperoleh ranking share default."),
        ("world_excluded_from_country_momentum", db["world_rows_in_country_momentum"], "World tidak boleh dihitung sebagai negara pada ranking momentum."),
    ]:
        results.append(check("model", name, "PASS" if int(value) == 0 else "FAIL", int(value), "0", detail))

    global_capacity = float(db["global_capacity_mw"])
    for label, key in [
        ("country_rollup_matches_global", "country_capacity_mw"),
        ("fuel_rollup_matches_global", "fuel_capacity_mw"),
        ("region_rollup_matches_global", "region_capacity_mw"),
        ("age_band_rollup_matches_global", "age_band_capacity_mw"),
    ]:
        difference = abs(float(db[key]) - global_capacity)
        results.append(check("filter", label, "PASS" if difference < CAPACITY_TOLERANCE_MW else "FAIL", difference, f"< {CAPACITY_TOLERANCE_MW} MW", "Agregasi pada filter context harus kembali ke total global."))

    for label, direct_key, view_key in [
        ("country_filter_contract_idn", "idn_capacity_direct_mw", "idn_capacity_view_mw"),
        ("fuel_filter_contract_idn_renewable", "idn_renewable_direct_mw", "idn_renewable_view_mw"),
    ]:
        difference = abs(float(db[direct_key]) - float(db[view_key]))
        results.append(check("filter", label, "PASS" if difference < CAPACITY_TOLERANCE_MW else "FAIL", difference, f"< {CAPACITY_TOLERANCE_MW} MW", "Hasil view harus identik dengan agregasi fact pada filter yang sama."))
    results.append(check("filter", "default_trend_filter_endpoints", "PASS" if int(db["default_filter_endpoint_rows"]) == 8 else "FAIL", int(db["default_filter_endpoint_rows"]), "8", "Empat seri default masing-masing harus memiliki endpoint 2005 dan 2022."))

    exact_signature_count = int(db["duplicate_asset_signatures"])
    results.append(check("double_counting", "duplicate_asset_signatures", "PASS" if exact_signature_count == 0 else "WARN", exact_signature_count, "0 preferred", "Signature memakai country, normalized name, koordinat, dan kapasitas. Temuan tidak boleh dihapus otomatis tanpa review."))
    results.append(check("double_counting", "world_dimension_is_singular", "PASS" if int(db["world_dimension_rows"]) == 1 else "FAIL", int(db["world_dimension_rows"]), "1", "World adalah seri pembanding terpisah, bukan anggota agregasi negara."))

    results.append(check("known_limitations", "phase2_validation_has_no_failures", "PASS" if int(phase2_validation["fail_count"]) == 0 else "FAIL", int(phase2_validation["fail_count"]), "0", "Validation gate Fase 2 tetap harus bersih dari failure."))
    results.append(check("known_limitations", "phase3_validation_has_no_failures", "PASS" if int(phase3_validation["fail_count"]) == 0 else "FAIL", int(phase3_validation["fail_count"]), "0", "Validation gate Fase 3 tetap harus bersih dari failure."))
    unmatched = int(db["unmatched_world_bank_countries"])
    results.append(check("known_limitations", "world_bank_unmatched_explicit", "WARN" if unmatched else "PASS", unmatched, "0 preferred", "ATA, ESH, GUF, dan TWN tetap ada dalam total global tetapi region/populasinya tidak terklasifikasi."))
    latest_coverage = int(db["latest_renewable_coverage"])
    results.append(check("known_limitations", "latest_year_partial_coverage", "WARN" if latest_coverage < 160 else "PASS", latest_coverage, ">= 160 preferred", "Tahun 2025 tidak digunakan sebagai endpoint ranking default."))

    result_frame = pd.DataFrame(results)
    fail_count = int(result_frame["status"].eq("FAIL").sum())
    warning_count = int(result_frame["status"].eq("WARN").sum())
    pass_count = int(result_frame["status"].eq("PASS").sum())
    overall = "FAIL" if fail_count else "PASS_WITH_WARNINGS" if warning_count else "PASS"
    generated_at = datetime.now(timezone.utc).isoformat()
    summary = {
        "overall_status": overall,
        "generated_at_utc": generated_at,
        "database": args.database,
        "pass_count": pass_count,
        "warning_count": warning_count,
        "fail_count": fail_count,
        "checks": results,
    }
    PHASE4_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    result_frame.to_csv(PHASE4_REPORT_DIR / "validation_results.csv", index=False)
    (PHASE4_REPORT_DIR / "validation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    lines = [
        "# Laporan Validasi dan Audit — Fase 4",
        "",
        f"**Status keseluruhan:** {overall}",
        "",
        f"Dibuat pada `{generated_at}`. Pass: **{pass_count}**, warning: **{warning_count}**, fail: **{fail_count}**.",
        "",
        "| Kategori | Pemeriksaan | Status | Aktual | Ekspektasi |",
        "|---|---|---:|---|---|",
    ]
    for item in results:
        actual = json.dumps(item["actual"], ensure_ascii=False) if isinstance(item["actual"], (dict, list)) else str(item["actual"])
        lines.append(f"| {item['category']} | {item['check']} | {item['status']} | {actual.replace('|', '/')} | {item['expected']} |")
    lines.extend([
        "",
        "## Kesimpulan audit double counting",
        "",
        "Fact aset menggunakan `plant_id` unik dan seluruh rollup kapasitas kembali ke total global. Fact historis menggunakan grain entity-year unik. Seri `OWID_WRL` diperlakukan sebagai benchmark terpisah dan dikeluarkan dari ranking negara; menjumlahkan `World` bersama negara dilarang karena akan menggandakan agregat.",
        "",
        "## Warning yang diterima",
        "",
        "Warning merupakan keterbatasan sumber yang sudah diekspos di dashboard, bukan kegagalan transformasi: empat country code tidak cocok dengan World Bank dan coverage 2025 belum memadai untuk ranking lintas negara.",
    ])
    (PHASE4_REPORT_DIR / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Validasi Fase 4 selesai: {overall} ({pass_count} pass, {warning_count} warning, {fail_count} fail)")
    return summary


if __name__ == "__main__":
    validate_phase4()
