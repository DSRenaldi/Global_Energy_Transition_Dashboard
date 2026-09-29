"""Profile the immutable WRI source dataset and write reproducible reports."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from paths import RAW_DATA_FILE, REPORT_DIR, ensure_directories


ID_COLUMN = "gppd_idnr"
DUPLICATE_CANDIDATE_COLUMNS = [
    "country",
    "name",
    "latitude",
    "longitude",
    "capacity_mw",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def python_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if hasattr(value, "item"):
        return value.item()
    return value


def profile_data(input_path: Path = RAW_DATA_FILE) -> dict[str, Any]:
    ensure_directories()
    if not input_path.exists():
        raise FileNotFoundError(f"Dataset mentah tidak ditemukan: {input_path}")

    data = pd.read_csv(input_path, low_memory=False)
    row_count = len(data)

    missingness = pd.DataFrame(
        {
            "column": data.columns,
            "dtype_inferred": [str(dtype) for dtype in data.dtypes],
            "non_null_count": [int(data[column].notna().sum()) for column in data.columns],
            "missing_count": [int(data[column].isna().sum()) for column in data.columns],
            "missing_pct": [round(float(data[column].isna().mean() * 100), 4) for column in data.columns],
            "distinct_non_null": [int(data[column].nunique(dropna=True)) for column in data.columns],
        }
    )
    missingness.to_csv(REPORT_DIR / "missingness.csv", index=False)

    numeric_summary = data.select_dtypes(include="number").describe(percentiles=[0.01, 0.25, 0.5, 0.75, 0.99]).T
    numeric_summary.index.name = "column"
    numeric_summary.reset_index().to_csv(REPORT_DIR / "numeric_summary.csv", index=False)

    fuel_counts = (
        data["primary_fuel"]
        .value_counts(dropna=False)
        .rename_axis("primary_fuel")
        .reset_index(name="plant_count")
    )
    fuel_counts.to_csv(REPORT_DIR / "fuel_counts.csv", index=False)

    country_counts = (
        data.groupby(["country", "country_long"], dropna=False)
        .agg(plant_count=(ID_COLUMN, "size"), total_capacity_mw=("capacity_mw", "sum"))
        .reset_index()
        .sort_values("total_capacity_mw", ascending=False)
    )
    country_counts.to_csv(REPORT_DIR / "country_counts.csv", index=False)

    duplicate_mask = data.duplicated(DUPLICATE_CANDIDATE_COLUMNS, keep=False)
    duplicate_candidates = data.loc[
        duplicate_mask,
        [ID_COLUMN, *DUPLICATE_CANDIDATE_COLUMNS, "primary_fuel", "source"],
    ].sort_values(DUPLICATE_CANDIDATE_COLUMNS)
    duplicate_candidates.to_csv(REPORT_DIR / "duplicate_candidates.csv", index=False)

    capacity = pd.to_numeric(data["capacity_mw"], errors="coerce")
    latitude = pd.to_numeric(data["latitude"], errors="coerce")
    longitude = pd.to_numeric(data["longitude"], errors="coerce")
    commissioning = pd.to_numeric(data["commissioning_year"], errors="coerce")
    commissioning_known_capacity = capacity.where(commissioning.notna()).sum()
    total_capacity = capacity.sum()

    summary: dict[str, Any] = {
        "input_file": str(input_path.relative_to(input_path.parents[2])),
        "sha256": sha256_file(input_path),
        "row_count": row_count,
        "column_count": len(data.columns),
        "columns": data.columns.tolist(),
        "country_count": int(data["country"].nunique(dropna=True)),
        "primary_fuel_count": int(data["primary_fuel"].nunique(dropna=True)),
        "primary_fuels": sorted(data["primary_fuel"].dropna().astype(str).unique().tolist()),
        "id_quality": {
            "missing": int(data[ID_COLUMN].isna().sum()),
            "duplicate_rows": int(data[ID_COLUMN].duplicated(keep=False).sum()),
            "unique_non_null": int(data[ID_COLUMN].nunique(dropna=True)),
        },
        "duplicate_candidate_rows": int(duplicate_mask.sum()),
        "capacity_mw": {
            "missing": int(capacity.isna().sum()),
            "zero": int(capacity.eq(0).sum()),
            "negative": int(capacity.lt(0).sum()),
            "sum": python_value(capacity.sum()),
            "min": python_value(capacity.min()),
            "median": python_value(capacity.median()),
            "max": python_value(capacity.max()),
        },
        "coordinates": {
            "missing_latitude": int(latitude.isna().sum()),
            "missing_longitude": int(longitude.isna().sum()),
            "invalid_latitude": int((latitude.notna() & ~latitude.between(-90, 90)).sum()),
            "invalid_longitude": int((longitude.notna() & ~longitude.between(-180, 180)).sum()),
            "zero_zero_rows": int((latitude.eq(0) & longitude.eq(0)).sum()),
        },
        "commissioning_year": {
            "missing": int(commissioning.isna().sum()),
            "coverage_pct": round(float(commissioning.notna().mean() * 100), 4),
            "capacity_coverage_pct": round(
                float(commissioning_known_capacity / total_capacity * 100), 4
            ),
            "min": python_value(commissioning.min()),
            "max": python_value(commissioning.max()),
            "fractional": int((commissioning.notna() & commissioning.mod(1).ne(0)).sum()),
        },
    }

    (REPORT_DIR / "profile_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    report_lines = [
        "# Laporan Profiling Data Mentah — Fase 1",
        "",
        f"- Baris: {row_count:,}",
        f"- Kolom: {len(data.columns)}",
        f"- Negara/wilayah: {summary['country_count']}",
        f"- Primary fuel: {summary['primary_fuel_count']}",
        f"- Total kapasitas: {summary['capacity_mw']['sum'] / 1000:,.3f} GW",
        f"- Plant ID kosong/duplikat: {summary['id_quality']['missing']}/{summary['id_quality']['duplicate_rows']}",
        f"- Kandidat duplikat berbasis negara, nama, koordinat, dan kapasitas: {summary['duplicate_candidate_rows']}",
        f"- Coverage commissioning year (record): {summary['commissioning_year']['coverage_pct']:.2f}%",
        f"- Coverage commissioning year (kapasitas): {summary['commissioning_year']['capacity_coverage_pct']:.2f}%",
        f"- Commissioning year desimal yang dipertahankan: {summary['commissioning_year']['fractional']:,}",
        "",
        "## Catatan interpretasi",
        "",
        "- Nilai commissioning year desimal bukan otomatis error. WRI dapat melaporkannya sebagai rata-rata tertimbang kapasitas unit.",
        "- Data pembangkitan tahunan memiliki coverage jauh lebih rendah daripada data kapasitas; jangan mengganti nilai aktual dengan estimasi tanpa penanda.",
        "- Dataset ini merupakan snapshot aset. Analisis perubahan historis membutuhkan sumber country-year terpisah.",
        "- Rincian missing value, statistik numerik, frekuensi fuel, dan jumlah negara tersedia pada file CSV pendamping di direktori yang sama.",
    ]
    (REPORT_DIR / "profile_report.md").write_text(
        "\n".join(report_lines) + "\n", encoding="utf-8"
    )
    print(f"Profiling selesai: {row_count:,} baris, {len(data.columns)} kolom")
    return summary


if __name__ == "__main__":
    profile_data()
