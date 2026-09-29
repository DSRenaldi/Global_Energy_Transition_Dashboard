# Kamus Data — Fase 1

## `data/processed/fact_power_plant.csv`

Grain tabel adalah satu record aset pembangkit dari WRI Global Power Plant Database versi 1.3.0. Transformasi tidak menghapus record sumber.

| Kolom | Definisi |
|---|---|
| `plant_id` | ID pembangkit dari WRI (`gppd_idnr` pada sumber). |
| `plant_name` | Nama pembangkit yang telah dibersihkan dari spasi di awal/akhir. |
| `country_iso3` | Key negara tiga karakter; `KOS` dipetakan manual menjadi `XKX`. |
| `country_name` | Nama negara terstandardisasi dari mapping proyek. |
| `source_country_code` | Kode negara asli dari WRI untuk audit trail. |
| `source_country_name` | Nama negara asli dari WRI. |
| `primary_fuel` | Bahan bakar utama dari WRI. |
| `fuel_key` | Key bahan bakar yang aman digunakan pada model. |
| `fuel_group` | `Fossil`, `Renewable`, `Nuclear`, atau `Other / Unknown`. |
| `is_fossil` | Flag 1 jika primary fuel masuk kelompok fosil. |
| `is_renewable` | Flag 1 jika primary fuel masuk kelompok terbarukan. |
| `is_nuclear` | Flag 1 jika primary fuel adalah nuklir. |
| `is_low_carbon` | Flag 1 untuk renewable atau nuclear. |
| `capacity_mw` | Kapasitas terpasang dalam MW. |
| `latitude` | Latitude WGS84. |
| `longitude` | Longitude WGS84. |
| `commissioning_year` | Tahun commissioning dari WRI; nilai desimal dipertahankan karena dapat berupa rata-rata tertimbang kapasitas unit. |
| `commissioning_year_is_fractional` | Flag yang menunjukkan commissioning year berbentuk desimal. |
| `dq_capacity_issue` | `ok`, `missing`, atau `non_positive`. |
| `dq_coordinate_issue` | `ok`, `missing`, atau `out_of_range`. |
| `dq_commissioning_issue` | `ok`, `missing`, atau `outside_snapshot_range`. |
| `dq_has_blocking_issue` | Flag masalah yang menghalangi record digunakan pada analisis kapasitas utama. |

Kolom WRI lain seperti owner, sumber, bahan bakar tambahan, pembangkitan, dan estimasi pembangkitan tetap dipertahankan untuk audit dan analisis lanjutan.

## `data/processed/dim_country.csv`

Mapping unik kode negara sumber ke key negara proyek. Kolom `mapping_method` membedakan mapping langsung dengan override manual. `XKX` untuk Kosovo adalah kode bergaya ISO yang umum digunakan, tetapi merupakan user-assigned code dan bukan entri resmi ISO 3166-1.

## `data/processed/dim_fuel.csv`

Tabel referensi yang memetakan setiap primary fuel ke kelompok energi dan empat flag klasifikasi. Waste, Cogeneration, Other, dan Storage tidak otomatis dikategorikan sebagai renewable.

## Model analitik Fase 2

CSV pada `data/analytics` adalah staging untuk PostgreSQL dan dapat dibangun ulang dengan `python src/run_phase2.py`.

### `energy_core.fact_power_plant`

| Kolom tambahan | Definisi |
|---|---|
| `commissioning_decade` | Dekade commissioning; null bila tahun tidak tersedia. |
| `plant_age_years` | `2020 - commissioning_year`; null bila commissioning year tidak tersedia. |
| `age_band` | `0-14 years`, `15-29 years`, `30-39 years`, `40+ years`, atau `Unknown`. |
| `age_band_sort` | Urutan tampilan age band. |
| `is_fossil_over_30` | True untuk aset fosil dengan `plant_age_years > 30`. |
| `is_coal_under_15` | True untuk aset Coal dengan `plant_age_years < 15`. |

### `energy_core.dim_country`

Dimension negara Fase 1 yang diperkaya dengan World Bank region, current income group saat tanggal akses, dan population 2020. `world_bank_match_status` menandai empat kode yang tidak cocok agar missing enrichment tidak tersembunyi.

### Analytical views

| View | Grain/fungsi |
|---|---|
| `energy_analytics.v_global_kpi` | Satu baris KPI kapasitas global. |
| `energy_analytics.v_global_fuel` | Satu baris per primary fuel. |
| `energy_analytics.v_country_kpi` | Satu baris per negara/wilayah. |
| `energy_analytics.v_country_ranking` | KPI negara ditambah ranking share untuk negara eligible. |
| `energy_analytics.v_country_fuel_mix` | Satu baris per negara dan primary fuel. |
| `energy_analytics.v_country_age_band` | Satu baris per negara, age band, dan fuel group. |
| `energy_analytics.v_region_kpi` | Satu baris per World Bank region atau unmatched group. |
| `energy_analytics.v_fossil_asset_risk` | KPI negara yang relevan untuk indikasi risiko aset fosil. |
| `energy_analytics.v_data_quality_country` | Coverage commissioning dan enrichment per negara. |
