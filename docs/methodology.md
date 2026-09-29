# Metodologi Fase 1

## Provenance

Snapshot WRI Global Power Plant Database versi 1.3.0 dipatok ke commit repository yang tercatat di `data/raw/source_metadata.json`. Integritas file diverifikasi menggunakan SHA-256. File mentah tidak dimodifikasi oleh pipeline.

## Profiling

Profiling mencakup struktur dan tipe hasil inferensi, missing value, cardinality, statistik numerik, distribusi primary fuel dan negara, keunikan ID, kandidat duplikat, validitas kapasitas dan koordinat, serta coverage commissioning year.

Kandidat duplikat diperiksa menggunakan kombinasi negara, nama, koordinat, dan kapasitas. Pemeriksaan ini tidak menjadi dasar penghapusan otomatis.

## Standardisasi

- Seluruh teks dibersihkan dari spasi pada awal dan akhir; string kosong menjadi null.
- Kolom numerik dikonversi dengan nilai yang tidak dapat diparsing menjadi null dan kemudian dilaporkan oleh validasi.
- Kode negara sumber dipertahankan sebagai audit trail.
- `KOS` dipetakan ke `XKX` melalui tabel override eksplisit.
- Fuel classification berasal dari `data/reference/fuel_mapping.csv`.
- Commissioning year desimal dipertahankan karena dapat merepresentasikan rata-rata tertimbang kapasitas unit.
- Tidak ada imputasi kapasitas, koordinat, commissioning year, atau pembangkitan.

## Validasi

Pipeline merekonsiliasi jumlah baris dan total kapasitas antara sumber dan tabel hasil. Pemeriksaan blocking mencakup ID, country mapping, fuel mapping, dan kapasitas. Missing commissioning year merupakan warning karena record tetap sah untuk analisis kapasitas, tetapi tidak boleh digunakan dalam analisis umur.

Rentang 1800–2020 hanya digunakan untuk mendeteksi anomali commissioning year pada snapshot WRI. Rentang tersebut bukan keputusan reference year untuk perhitungan umur aset.

