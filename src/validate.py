"""Run Phase 1 data-quality checks and write machine/human-readable reports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from paths import (
    FACT_POWER_PLANT_FILE,
    RAW_DATA_FILE,
    REPORT_DIR,
    SOURCE_METADATA_FILE,
    ensure_directories,
)


def result(check: str, status: str, actual: Any, expected: str, detail: str) -> dict[str, Any]:
    return {
        "check": check,
        "status": status,
        "actual": actual,
        "expected": expected,
        "detail": detail,
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_data(
    raw_path: Path = RAW_DATA_FILE,
    processed_path: Path = FACT_POWER_PLANT_FILE,
) -> list[dict[str, Any]]:
    ensure_directories()
    raw = pd.read_csv(raw_path, low_memory=False)
    clean = pd.read_csv(processed_path, low_memory=False)
    checks: list[dict[str, Any]] = []

    metadata = json.loads(SOURCE_METADATA_FILE.read_text(encoding="utf-8"))
    actual_raw_hash = sha256_file(raw_path)
    expected_raw_hash = metadata.get("sha256", "")
    checks.append(
        result(
            "raw_source_integrity",
            "PASS" if actual_raw_hash == expected_raw_hash else "FAIL",
            actual_raw_hash,
            expected_raw_hash,
            "SHA-256 file mentah harus sama dengan metadata provenance.",
        )
    )

    checks.append(
        result(
            "row_count_reconciled",
            "PASS" if len(raw) == len(clean) else "FAIL",
            len(clean),
            str(len(raw)),
            "Transformasi tidak boleh menambah atau menghapus record.",
        )
    )

    missing_ids = int(clean["plant_id"].isna().sum())
    duplicate_ids = int(clean["plant_id"].duplicated(keep=False).sum())
    checks.append(result("plant_id_not_null", "PASS" if missing_ids == 0 else "FAIL", missing_ids, "0", "Plant ID wajib terisi."))
    checks.append(result("plant_id_unique", "PASS" if duplicate_ids == 0 else "FAIL", duplicate_ids, "0", "Plant ID wajib unik."))

    raw_capacity = pd.to_numeric(raw["capacity_mw"], errors="coerce").sum()
    clean_capacity = pd.to_numeric(clean["capacity_mw"], errors="coerce").sum()
    capacity_difference = abs(float(raw_capacity - clean_capacity))
    checks.append(
        result(
            "capacity_sum_reconciled",
            "PASS" if capacity_difference < 1e-6 else "FAIL",
            capacity_difference,
            "< 0.000001 MW",
            f"Raw={raw_capacity:.6f} MW; processed={clean_capacity:.6f} MW.",
        )
    )

    invalid_capacity = int(
        (pd.to_numeric(clean["capacity_mw"], errors="coerce").isna() | clean["capacity_mw"].le(0)).sum()
    )
    checks.append(result("capacity_positive", "PASS" if invalid_capacity == 0 else "FAIL", invalid_capacity, "0", "Kapasitas kosong, nol, atau negatif tidak valid untuk tabel analitik."))

    unmapped_fuel = int(clean["fuel_key"].isna().sum())
    checks.append(result("fuel_mapping_complete", "PASS" if unmapped_fuel == 0 else "FAIL", unmapped_fuel, "0", "Semua primary fuel harus memiliki mapping."))

    unmapped_country = int(clean["country_iso3"].isna().sum())
    invalid_country_format = int(
        (~clean["country_iso3"].fillna("").str.fullmatch(r"[A-Z]{3}")).sum()
    )
    checks.append(result("country_mapping_complete", "PASS" if unmapped_country == 0 else "FAIL", unmapped_country, "0", "Semua record harus memiliki country key."))
    checks.append(result("country_iso3_format", "PASS" if invalid_country_format == 0 else "FAIL", invalid_country_format, "0", "Country key harus terdiri dari tiga huruf kapital."))

    latitude = pd.to_numeric(clean["latitude"], errors="coerce")
    longitude = pd.to_numeric(clean["longitude"], errors="coerce")
    invalid_coordinates = int(
        (latitude.notna() & ~latitude.between(-90, 90)).sum()
        + (longitude.notna() & ~longitude.between(-180, 180)).sum()
    )
    missing_coordinates = int((latitude.isna() | longitude.isna()).sum())
    checks.append(result("coordinate_ranges", "PASS" if invalid_coordinates == 0 else "FAIL", invalid_coordinates, "0", "Latitude dan longitude harus berada dalam rentang WGS84."))
    checks.append(result("coordinate_coverage", "PASS" if missing_coordinates == 0 else "WARN", missing_coordinates, "0 preferred", "Record tanpa koordinat tetap boleh dipakai untuk agregasi negara."))

    commissioning = pd.to_numeric(clean["commissioning_year"], errors="coerce")
    missing_commissioning = int(commissioning.isna().sum())
    fractional_commissioning = int(
        (commissioning.notna() & commissioning.mod(1).ne(0)).sum()
    )
    out_of_snapshot_range = int((commissioning.notna() & ~commissioning.between(1800, 2020)).sum())
    checks.append(result("commissioning_year_range", "PASS" if out_of_snapshot_range == 0 else "WARN", out_of_snapshot_range, "0", "Rentang plausibel snapshot ditetapkan 1800-2020; ini bukan reference year untuk plant age."))
    checks.append(result("commissioning_year_coverage", "PASS" if missing_commissioning == 0 else "WARN", missing_commissioning, "0 preferred", "Missing commissioning year harus terlihat pada dashboard dan analisis umur."))
    checks.append(result("fractional_commissioning_year_preserved", "PASS", fractional_commissioning, "informational", "Nilai desimal dipertahankan karena WRI dapat melaporkan commissioning year sebagai rata-rata tertimbang kapasitas unit."))

    blocking_issues = int(clean["dq_has_blocking_issue"].fillna(True).astype(bool).sum())
    checks.append(result("blocking_quality_flags", "PASS" if blocking_issues == 0 else "FAIL", blocking_issues, "0", "Flag blocking mencakup ID/country/fuel/capacity yang tidak valid."))

    results_frame = pd.DataFrame(checks)
    results_frame.to_csv(REPORT_DIR / "validation_results.csv", index=False)

    summary = {
        "overall_status": "FAIL" if (results_frame["status"] == "FAIL").any() else "PASS_WITH_WARNINGS" if (results_frame["status"] == "WARN").any() else "PASS",
        "pass_count": int((results_frame["status"] == "PASS").sum()),
        "warning_count": int((results_frame["status"] == "WARN").sum()),
        "fail_count": int((results_frame["status"] == "FAIL").sum()),
        "checks": checks,
    }
    (REPORT_DIR / "validation_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    markdown_lines = [
        "# Laporan Validasi Data — Fase 1",
        "",
        f"**Status keseluruhan:** {summary['overall_status']}",
        "",
        f"- Pass: {summary['pass_count']}",
        f"- Warning: {summary['warning_count']}",
        f"- Fail: {summary['fail_count']}",
        "",
        "| Pemeriksaan | Status | Nilai aktual | Ekspektasi | Keterangan |",
        "|---|---:|---:|---|---|",
    ]
    for check in checks:
        detail = str(check["detail"]).replace("|", "\\|")
        markdown_lines.append(
            f"| {check['check']} | {check['status']} | {check['actual']} | {check['expected']} | {detail} |"
        )
    (REPORT_DIR / "validation_report.md").write_text(
        "\n".join(markdown_lines) + "\n", encoding="utf-8"
    )

    print(f"Validasi selesai: {summary['overall_status']}")
    return checks


if __name__ == "__main__":
    validate_data()
