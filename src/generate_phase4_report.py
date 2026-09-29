"""Generate the Phase 4 evidence pack and decision-oriented executive summary."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from paths import ANALYTICS_DIR, PHASE4_REPORT_DIR, ensure_directories


def clean_record(record: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in record.items():
        if pd.isna(value):
            cleaned[key] = None
        elif hasattr(value, "item"):
            cleaned[key] = value.item()
        else:
            cleaned[key] = value
    return cleaned


def records(frame: pd.DataFrame, columns: list[str]) -> list[dict[str, Any]]:
    return [clean_record(row) for row in frame[columns].to_dict(orient="records")]


def generate_phase4_report() -> dict[str, Any]:
    ensure_directories()
    global_kpi = pd.read_csv(ANALYTICS_DIR / "mart_global_kpi.csv").iloc[0]
    countries = pd.read_csv(ANALYTICS_DIR / "mart_country_kpi.csv")
    momentum = pd.read_csv(ANALYTICS_DIR / "mart_transition_momentum.csv")
    energy = pd.read_csv(ANALYTICS_DIR / "fact_country_energy_year.csv", low_memory=False)
    validation = json.loads(
        (PHASE4_REPORT_DIR / "validation_summary.json").read_text(encoding="utf-8")
    )

    world = energy[
        energy["entity_code"].eq("OWID_WRL") & energy["year"].isin([2005, 2022])
    ].set_index("year")
    world_start = world.loc[2005]
    world_end = world.loc[2022]

    merged = countries.merge(
        momentum,
        left_on="country_iso3",
        right_on="entity_code",
        how="inner",
        suffixes=("_asset", "_trend"),
        validate="one_to_one",
    )
    large = merged[
        merged["has_comparable_endpoints"].astype(bool)
        & merged["total_capacity_gw"].ge(50)
    ]
    large_fast = large.nlargest(5, "renewable_transition_momentum_pp_per_year")
    large_slow = large.nsmallest(5, "renewable_transition_momentum_pp_per_year")
    old_fossil = countries.nlargest(5, "fossil_capacity_over_30_years_mw")
    young_coal = countries.nlargest(5, "coal_capacity_under_15_years_mw")
    top_capacity = countries.nlargest(5, "total_capacity_mw")
    generated_at = datetime.now(timezone.utc).isoformat()

    evidence = {
        "generated_at_utc": generated_at,
        "validation_status": validation["overall_status"],
        "scope": {
            "asset_reference_year": 2020,
            "trend_period": "2005-2022",
            "plant_rows": int(global_kpi["total_plants"]),
            "asset_countries": int(len(countries)),
            "historical_entities": int(energy["entity_code"].nunique()),
        },
        "global": {
            "capacity_gw": float(global_kpi["total_capacity_gw"]),
            "fossil_capacity_share_pct": float(global_kpi["fossil_share_pct"]),
            "renewable_capacity_share_pct": float(global_kpi["renewable_share_pct"]),
            "low_carbon_capacity_share_pct": float(global_kpi["low_carbon_share_pct"]),
            "age_coverage_by_capacity_pct": float(global_kpi["age_coverage_by_capacity_pct"]),
            "renewable_electricity_share_2005_pct": float(world_start["renewables_share_pct"]),
            "renewable_electricity_share_2022_pct": float(world_end["renewables_share_pct"]),
            "renewable_electricity_change_pp": float(world_end["renewables_share_pct"] - world_start["renewables_share_pct"]),
            "fossil_electricity_change_pp": float(world_end["fossil_share_pct"] - world_start["fossil_share_pct"]),
        },
        "top_capacity": records(top_capacity, ["country_iso3", "country_name", "total_capacity_gw", "fossil_share_pct", "low_carbon_share_pct"]),
        "old_fossil": records(old_fossil, ["country_iso3", "country_name", "fossil_capacity_over_30_years_mw", "fossil_age_coverage_by_capacity_pct"]),
        "young_coal": records(young_coal, ["country_iso3", "country_name", "coal_capacity_under_15_years_mw", "coal_capacity_under_15_years_share_pct", "fossil_age_coverage_by_capacity_pct"]),
        "large_system_fast_momentum": records(large_fast, ["country_iso3", "country_name_asset", "total_capacity_gw", "renewables_share_pct_change", "renewable_transition_momentum_pp_per_year"]),
        "large_system_slow_momentum": records(large_slow, ["country_iso3", "country_name_asset", "total_capacity_gw", "renewables_share_pct_change", "renewable_transition_momentum_pp_per_year"]),
    }
    PHASE4_REPORT_DIR.mkdir(parents=True, exist_ok=True)
    (PHASE4_REPORT_DIR / "evidence_pack.json").write_text(
        json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    fast_leader = large_fast.iloc[0]
    slowest = large_slow.iloc[0]
    old_leader = old_fossil.iloc[0]
    young_leader = young_coal.iloc[0]
    lines = [
        "# Executive Summary — Transisi Listrik Dunia",
        "",
        f"**Decision window:** aset 2020 dan tren produksi listrik 2005–2022  ",
        f"**Validation gate:** {validation['overall_status']} ({validation['pass_count']} pass, {validation['warning_count']} warning, {validation['fail_count']} fail)  ",
        f"**Dibuat:** {generated_at}",
        "",
        "## Ringkasan eksekutif",
        "",
        f"Basis aset global yang dipetakan mencapai **{global_kpi['total_capacity_gw']:,.1f} GW** pada snapshot 2020, dan **{global_kpi['fossil_share_pct']:.1f}%** masih berupa kapasitas fosil. Pada sisi produksi, share listrik terbarukan dunia naik dari **{world_start['renewables_share_pct']:.1f}%** pada 2005 menjadi **{world_end['renewables_share_pct']:.1f}%** pada 2022—kenaikan **{world_end['renewables_share_pct'] - world_start['renewables_share_pct']:.1f} percentage points**. Arah transisi terlihat, tetapi pergantian struktur aset berjalan lebih lambat dan risiko lock-in terkonsentrasi pada sedikit sistem berskala sangat besar.",
        "",
        "## Enam temuan yang dapat ditindaklanjuti",
        "",
        f"1. **Skala fosil masih dominan.** Dari {global_kpi['total_capacity_gw']:,.1f} GW kapasitas yang dipetakan, {global_kpi['fossil_share_pct']:.1f}% berbasis fosil. Keputusan investasi perlu dinilai dalam GW absolut, bukan hanya share, karena penurunan persentase kecil pada sistem besar dapat setara dengan seluruh sistem negara kecil.",
        f"2. **Produksi listrik terbarukan membaik, tetapi belum menggantikan fosil satu banding satu.** Share terbarukan global bertambah {world_end['renewables_share_pct'] - world_start['renewables_share_pct']:.1f} pp pada 2005–2022, sementara share fosil turun hanya {abs(world_end['fossil_share_pct'] - world_start['fossil_share_pct']):.1f} pp. Pertumbuhan permintaan dan perubahan nuklir/komponen lain perlu ikut dipertimbangkan.",
        f"3. **Pensiun aset tua merupakan peluang terbesar sekaligus risiko implementasi.** {old_leader['country_name']} memiliki {old_leader['fossil_capacity_over_30_years_mw'] / 1000:,.1f} GW kapasitas fosil berumur >30 tahun pada snapshot, dengan coverage umur {old_leader['fossil_age_coverage_by_capacity_pct']:.1f}%. Status operasi terkini harus diverifikasi sebelum membuat target retirement.",
        f"4. **Lock-in batu bara muda terkonsentrasi.** {young_leader['country_name']} sendiri mencatat {young_leader['coal_capacity_under_15_years_mw'] / 1000:,.1f} GW batu bara berumur <15 tahun; India berada di posisi berikutnya dengan {young_coal.iloc[1]['coal_capacity_under_15_years_mw'] / 1000:,.1f} GW. Tanpa strategi utilisasi, refinancing, atau retirement dini, aset ini dapat memperpanjang emisi beberapa dekade.",
        f"5. **Momentum cepat juga dapat terjadi pada sistem besar.** Di antara negara dengan kapasitas aset ≥50 GW, {fast_leader['country_name_asset']} mencatat kenaikan renewable electricity share {fast_leader['renewables_share_pct_change']:+.1f} pp ({fast_leader['renewable_transition_momentum_pp_per_year']:.2f} pp/tahun). Kasus ini lebih relevan untuk pembelajaran skala daripada ranking yang didominasi sistem sangat kecil.",
        f"6. **Tidak semua sistem besar bergerak ke arah yang sama.** {slowest['country_name_asset']} mencatat perubahan {slowest['renewables_share_pct_change']:+.1f} pp dalam kelompok ≥50 GW. Analisis lanjutan perlu memisahkan perubahan permintaan, hydro variability, nuklir, perdagangan listrik, dan kebijakan domestik sebelum menyimpulkan penyebab.",
        "",
        "## Rekomendasi",
        "",
        "- **Prioritaskan portofolio, bukan ranking tunggal.** Gunakan matriks skala fosil, umur aset, coverage, dan momentum historis untuk memilih negara yang perlu dianalisis lebih dalam.",
        "- **Buat dua jalur intervensi.** Armada tua membutuhkan verifikasi status dan rencana retirement; batu bara muda membutuhkan strategi pencegahan lock-in, refinancing, atau penurunan utilisasi.",
        "- **Gunakan peer group berskala sebanding.** Untuk transfer kebijakan, bandingkan sistem ≥50 GW atau kelompok region/income yang serupa, bukan seluruh negara dalam satu ranking.",
        "- **Perbarui sumber aset sebelum keputusan aktual.** WRI 1.3.0 adalah snapshot final yang tidak lagi dipelihara; cocok untuk portofolio analitik, bukan inventaris operasi terkini.",
        "- **Tingkatkan observability data.** Pertahankan checksum, tanggal refresh, coverage commissioning year, endpoint coverage, dan unmatched country sebagai bagian dari setiap publikasi.",
        "",
        "## Batas keputusan",
        "",
        "Dashboard mendeskripsikan struktur dan perubahan; ia tidak mengestimasi dampak kausal kebijakan, profitabilitas aset, jadwal penutupan, atau status operasi saat ini. Kapasitas WRI dan produksi OWID berasal dari sumber serta jam data yang berbeda dan tidak boleh dijumlahkan atau diperlakukan sebagai metrik yang sama.",
    ]
    (PHASE4_REPORT_DIR / "executive_summary.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("Executive summary dan evidence pack Fase 4 selesai dibuat.")
    return evidence


if __name__ == "__main__":
    generate_phase4_report()
