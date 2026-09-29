# Fase 3 — Tren historis dan dashboard React

## Ruang lingkup

Fase 3 menambahkan data country-year Our World in Data (OWID), empat analytical views PostgreSQL, API read-only, dan antarmuka React. Dashboard sengaja memisahkan dua jam data:

- Snapshot WRI 2020 untuk aset, kapasitas, lokasi, dan umur pembangkit.
- Deret waktu OWID untuk produksi listrik dan perubahan baur energi.

Perbandingan utama menggunakan 2005–2022. Data sampai 2025 tetap tersedia, tetapi coverage 2025 hanya 90 entitas sehingga tidak dipakai sebagai endpoint ranking default.

## Arsitektur

```text
PostgreSQL (energy_core + energy_analytics)
                 ↓
       Express read-only API
                 ↓
         React + ECharts
```

Server membaca koneksi PostgreSQL dari `.env` di root proyek. Query menggunakan parameter terikat, daftar field eksplisit, batas hasil, dan pesan error yang tidak membocorkan detail server.

`npm run dev` menjalankan server tanpa Node watch mode karena Vite sudah menangani HMR frontend. Jika sedang mengubah kode Express, `npm run dev:watch` membatasi watcher hanya ke folder `server` agar perubahan cache Vite tidak memicu restart loop.

## Endpoint

| Endpoint | Fungsi |
|---|---|
| `/api/health` | Status koneksi database |
| `/api/overview` | KPI aset global, endpoint tren, dan coverage terbaru |
| `/api/countries` | KPI serta koordinat agregat negara |
| `/api/fuels` | Baur kapasitas global per primary fuel |
| `/api/trends` | Deret waktu maksimal lima entitas |
| `/api/momentum` | Momentum terbarukan 2005–2022 |
| `/api/risk` | Indikator umur dan lock-in aset fosil |
| `/api/age-bands` | Distribusi umur aset per negara |
| `/api/meta` | Entitas, coverage, provenance, dan unmatched country |

## Halaman dashboard

1. **Ikhtisar** — tesis global, energy-mix ribbon, peta, dan komposisi bahan bakar.
2. **Negara** — ranking interaktif menurut skala atau share, dengan filter region.
3. **Jejak transisi** — perbandingan seri 2005–2022 dan ranking momentum.
4. **Risiko aset** — kapasitas fosil, umur >30 tahun, dan batu bara <15 tahun.
5. **Metodologi** — sumber, definisi, coverage, serta guardrail interpretasi.

## Pengujian

`npm run check` memeriksa sintaks server dan membuat production build. `npm run test:e2e` menyalakan server sendiri lalu menjalankan skenario desktop dan mobile: pemuatan data nyata, navigasi seluruh halaman, kesehatan API, console errors, dan horizontal overflow.

Hasil terakhir pada 29 September 2026: production build lulus, audit npm menemukan 0 vulnerability, dan 4/4 test browser lulus.
