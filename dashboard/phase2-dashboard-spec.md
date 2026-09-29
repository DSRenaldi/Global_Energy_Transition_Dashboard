# Spesifikasi Dashboard Fase 2

Dokumen ini bersifat tool-agnostic. Sumber utama visual adalah PostgreSQL schema `energy_analytics`; detail titik pembangkit berasal dari `energy_core.fact_power_plant` yang di-join ke dimensions.

## 1. Global Overview

Tujuan: pengguna memahami struktur kapasitas global dalam kurang dari satu menit.

Data:

- `energy_analytics.v_global_kpi`
- `energy_analytics.v_global_fuel`
- `energy_analytics.v_country_ranking`
- `energy_core.fact_power_plant`

Visual:

1. KPI cards: total capacity (GW), total plants, renewable share, low-carbon share, fossil share.
2. Bubble map: longitude/latitude, ukuran berdasarkan capacity MW, warna berdasarkan fuel group.
3. Horizontal bar: capacity GW per primary fuel.
4. Ranking negara: total capacity GW dengan low-carbon share pada tooltip.
5. Coverage badge: commissioning-year coverage by capacity.

Filter: region, country, fuel group, primary fuel, capacity range, commissioning decade.

Tooltip pembangkit: plant name, country, primary fuel, capacity MW, commissioning year, age band, source name.

## 2. Country Comparison

Tujuan: membandingkan dua sampai lima negara berdasarkan ukuran absolut dan bauran.

Data:

- `energy_analytics.v_country_ranking`
- `energy_analytics.v_country_fuel_mix`

Visual:

1. Bar chart total capacity GW.
2. 100% stacked bar primary-fuel capacity share.
3. Scatter: total capacity GW vs renewable share; ukuran bubble menunjukkan population 2020.
4. Matrix country × primary fuel dalam GW dan persen.
5. Diversity panel: HHI, Diversity Index, Effective Fuel Count, dan dominant fuel share.

Aturan:

- Country selector dibatasi dua sampai lima pilihan untuk mode perbandingan.
- Ranking share default memakai minimum capacity 1 GW.
- Negara yang tidak memiliki population tetap tampil; capacity per million people menjadi null.

## 3. Fossil Asset Risk

Tujuan: mengeksplorasi ketergantungan dan umur indikatif aset fosil.

Data:

- `energy_analytics.v_fossil_asset_risk`
- `energy_analytics.v_country_age_band`
- `energy_core.fact_power_plant`

Visual:

1. Scatter: coal dependency vs fossil capacity-weighted age; ukuran bubble berdasarkan fossil capacity.
2. Stacked bar: fossil capacity per age band.
3. Ranking fossil capacity over 30 years.
4. Ranking coal capacity under 15 years.
5. Drill-through table pembangkit individual.
6. Coverage indicator untuk fossil commissioning year.

Aturan:

- Country dengan fossil-age coverage rendah tetap boleh tampil, tetapi visual harus menampilkan coverage.
- Gunakan istilah “indikasi risiko aset fosil”; jangan menyatakan kepastian penutupan.

## 4. Data Quality & Methodology

Data:

- `energy_analytics.v_data_quality_country`
- metadata sumber dan laporan validasi pipeline.

Visual/informasi:

1. Commissioning-year coverage per country.
2. World Bank match status.
3. Versi WRI, commit, checksum, dan tanggal akses.
4. Reference year dan age-band definitions.
5. Fuel mapping dan definisi low carbon.
6. Batasan snapshot, produksi vs kapasitas, dan coverage.

## Warna konsisten

| Sumber/kelompok | Warna awal |
|---|---|
| Coal | `#3F3F46` |
| Gas | `#F28E2B` |
| Oil/Petcoke | `#8C564B` |
| Solar | `#F6C945` |
| Wind | `#56B4E9` |
| Hydro | `#1769AA` |
| Biomass/Geothermal | `#2E8B57` |
| Nuclear | `#7E57C2` |
| Other / Unknown | `#A0A0A0` |

Warna tidak boleh menjadi satu-satunya pembeda; gunakan label, tooltip, dan legend tekstual.

