# Metodologi Fase 2 — Analisis Aset Pembangkit

## Ruang lingkup

Fase 2 menganalisis struktur kapasitas aset pada snapshot WRI 1.3.0. Fase ini tidak mengukur perubahan historis dan tidak menggunakan kapasitas sebagai pengganti produksi listrik.

## Reference year

Umur indikatif dihitung dengan:

```text
plant_age_years = 2020 - commissioning_year
```

Tahun 2020 dipilih karena merupakan batas maksimum commissioning year pada snapshot. Menggunakan tahun kalender saat dashboard dibuka akan membuat aset terlihat terus bertambah tua tanpa bukti bahwa pembangkit masih beroperasi.

Commissioning year desimal dipertahankan. Karena itu, plant age juga dapat berbentuk desimal.

## Kelompok umur

| Age band | Aturan |
|---|---|
| 0–14 years | `0 <= age < 15` |
| 15–29 years | `15 <= age < 30` |
| 30–39 years | `30 <= age < 40` |
| 40+ years | `age >= 40` |
| Unknown | Commissioning year tidak tersedia atau tidak valid |

KPI `Fossil Capacity Over 30 Years` memakai aturan ketat `age > 30`. KPI `Coal Capacity Under 15 Years` memakai `age < 15`.

## Bauran dan diversifikasi

Seluruh share kapasitas menggunakan total capacity pada filter context sebagai denominator. Low-carbon capacity adalah renewable + nuclear.

Diversifikasi dihitung pada level primary fuel:

```text
Fuel Concentration HHI = SUM(primary_fuel_capacity_share ^ 2)
Fuel Diversity Index = 1 - HHI
Effective Fuel Count = 1 / HHI
```

HHI mendekati 1 menunjukkan dominasi satu primary fuel. Diversity Index mendekati 1 menunjukkan bauran lebih tersebar. Metrik ini menggambarkan kapasitas, bukan produksi listrik.

## Ranking share

Ranking renewable share, low-carbon share, dan coal dependency menggunakan ambang default minimum total capacity 1 GW. Negara di bawah ambang tetap tersedia pada model dan visual, tetapi tidak mendapat ranking share default. Ambang disimpan pada kolom `minimum_capacity_for_share_ranking_mw` agar transparan dan dapat diubah kemudian.

## Data World Bank

Population year ditetapkan 2020 agar selaras dengan reference year aset. Region dan income group berasal dari klasifikasi World Bank yang berlaku pada tanggal akses API, sehingga income group bukan klasifikasi historis tahun 2020.

Sebanyak 163 dari 167 kode negara/wilayah WRI cocok dengan World Bank. ATA, ESH, GUF, dan TWN dipertahankan sebagai `Unmatched / Not classified`. Nilai tersebut tidak dibuang dari total global.

## PostgreSQL

PostgreSQL menjadi database utama dengan dua schema:

- `energy_core`: dimensions dan fact table.
- `energy_analytics`: view KPI dan dataset dashboard.

CSV pada `data/analytics` adalah staging/interchange output yang dapat dibangun ulang, bukan sumber kebenaran terpisah. Setelah database dimuat, alat BI sebaiknya membaca view pada schema `energy_analytics`.

## Batasan

- WRI 1.3.0 adalah snapshot lama dan tidak membuktikan status operasi saat ini.
- Umur hanya tersedia jika commissioning year terisi; gunakan coverage bersama setiap ranking umur.
- Primary fuel tidak menggambarkan seluruh pola operasi atau bahan bakar sekunder.
- Capacity-weighted age tidak sama dengan usia setiap unit di dalam satu fasilitas.
- Capacity per million people hanya tersedia ketika population 2020 cocok dengan kode negara.
- Indikator risiko fosil adalah alat eksplorasi, bukan prediksi penutupan atau stranded asset.

