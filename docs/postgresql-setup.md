# PostgreSQL Setup

Model Fase 2 menggunakan PostgreSQL sebagai database utama. Instalasi lokal yang terdeteksi saat pengembangan adalah PostgreSQL 18.4 pada `localhost:5432`.

## Kredensial

Isi file `.env` pada root proyek. File tersebut diabaikan oleh Git dan otomatis dibaca oleh `src/load_postgres.py`.

```dotenv
PGHOST=localhost
PGPORT=5432
PGUSER=postgres
PGPASSWORD=isi_password_anda
PGDATABASE=energy_transition
PGMAINTENANCE_DATABASE=postgres
```

Jangan melakukan commit atau membagikan isi `.env`. Alternatif lain:

- PostgreSQL password file (`pgpass.conf` pada Windows atau `.pgpass` pada Linux/macOS).
- Environment variable `PGPASSWORD` hanya untuk proses terminal aktif.
- Prompt password interaktif dari `psql`.

Environment variable yang didukung:

```powershell
$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGUSER = "postgres"
$env:PGDATABASE = "energy_transition"
```

## Build dan load

```powershell
python src/download_world_bank.py
python src/run_phase1.py
python src/build_phase2.py
python src/validate_phase2.py
python src/load_postgres.py
python src/verify_postgres.py
```

Loader akan:

1. Membuat database `energy_transition` jika belum ada.
2. Membuat ulang schema proyek `energy_core` dan `energy_analytics`.
3. Memuat dimension dan fact tables dengan `\copy` client-side.
4. Membuat analytical views.
5. Menjalankan pemeriksaan kualitas SQL.

`verify_postgres.py` kemudian membandingkan row counts dan KPI global PostgreSQL dengan mart lokal menggunakan toleransi numerik `0.000001`.

Gunakan `--skip-create-database` bila akun tidak memiliki hak `CREATE DATABASE`. Database target harus sudah tersedia.

```powershell
python src/load_postgres.py --skip-create-database
```

Untuk memeriksa konfigurasi tanpa koneksi atau perubahan database:

```powershell
python src/load_postgres.py --dry-run
```

## Schema

- `energy_core.dim_country`
- `energy_core.dim_fuel`
- `energy_core.dim_age_band`
- `energy_core.fact_power_plant`
- `energy_analytics.v_global_kpi`
- `energy_analytics.v_country_kpi`
- `energy_analytics.v_country_ranking`
- `energy_analytics.v_country_fuel_mix`
- `energy_analytics.v_country_age_band`
- `energy_analytics.v_global_fuel`
- `energy_analytics.v_region_kpi`
- `energy_analytics.v_fossil_asset_risk`
- `energy_analytics.v_data_quality_country`

`sql/01_create_schema.sql` bersifat idempotent untuk database proyek, tetapi akan menghapus dan membuat ulang dua schema bernama `energy_core` dan `energy_analytics`. Jangan arahkan loader ke database lain yang menggunakan nama schema tersebut untuk data berbeda.
