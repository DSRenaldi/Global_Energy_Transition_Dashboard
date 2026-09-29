# Fase 4 — Validasi dan komunikasi

## Tujuan

Fase 4 adalah acceptance gate sebelum dashboard dipakai sebagai artefak portofolio atau dasar eksplorasi kebijakan. Gate ini merekonsiliasi sumber hingga PostgreSQL, menguji relasi dan filter, meninjau double counting, serta menghasilkan executive summary yang dapat ditelusuri kembali ke evidence pack.

## Menjalankan

```powershell
python src/run_phase4.py
```

Proses berhenti apabila satu pemeriksaan berstatus `FAIL`. Warning tidak disembunyikan dan harus tetap muncul dalam komunikasi hasil.

Artefak yang dihasilkan:

- `reports/phase4/validation_summary.json`
- `reports/phase4/validation_results.csv`
- `reports/phase4/validation_report.md`
- `reports/phase4/evidence_pack.json`
- `reports/phase4/executive_summary.md`

## Acceptance criteria

Validation gate memeriksa:

1. Checksum snapshot WRI dan OWID sesuai metadata provenance.
2. Jumlah baris serta total kapasitas WRI identik pada sumber, mart, dan PostgreSQL.
3. Jumlah entity-year OWID identik pada seleksi sumber, mart, dan PostgreSQL.
4. Primary key, grain entity-year, dan seluruh dimension relationship tidak memiliki orphan.
5. Rollup negara, fuel, region, dan age band kembali ke total global.
6. Filter negara/fuel menghasilkan nilai yang sama antara direct fact aggregation dan analytical view.
7. Negara di bawah 1 GW tidak memperoleh ranking share default.
8. `OWID_WRL` tidak masuk ranking negara dan tidak pernah dijumlahkan bersama country rows.
9. Validation gate Fase 2 dan Fase 3 tidak memiliki failure.

## Audit double counting

- Aset menggunakan grain satu baris per `plant_id`.
- Candidate duplicate ditinjau menggunakan kombinasi country, normalized plant name, koordinat, dan kapasitas; tidak ada penghapusan otomatis berbasis nama.
- Historis menggunakan grain satu baris per `entity_code` dan `year`.
- `World` merupakan agregat pembanding OWID. Menjumlahkan baris `World` dengan seluruh negara akan menggandakan nilai dan dilarang.
- Kapasitas WRI dan produksi OWID tidak pernah dijumlahkan karena berbeda unit, konsep, dan periode.

## Asumsi dan batasan

- Reference year umur aset adalah 2020.
- Low carbon adalah renewable + nuclear.
- Periode pembanding lintas negara adalah 2005–2022.
- Ranking share kapasitas mensyaratkan minimal 1 GW.
- WRI 1.3.0 adalah snapshot final yang tidak lagi dipelihara dan tidak membuktikan status operasi saat ini.
- Commissioning-year coverage global adalah 66,69% berdasarkan kapasitas; ranking umur wajib dibaca bersama coverage.
- ATA, ESH, GUF, dan TWN tidak cocok dengan World Bank tetapi tetap termasuk dalam total global.
- Coverage renewable share 2025 hanya 90 entitas, sehingga tahun tersebut tidak menjadi endpoint ranking default.
- Dashboard bersifat deskriptif dan tidak mengestimasi kausalitas, profitabilitas, jadwal penutupan, atau kepastian stranded asset.

## Provenance dan tanggal refresh

| Komponen | Versi/cutoff | Diakses atau dimuat |
|---|---|---|
| WRI Global Power Plant Database | 1.3.0, commit `7a91cfbb2a4e272597acbc00506d61fc1ec73b3d` | 29 September 2026 UTC |
| OWID Energy Data | commit `7e387a16f70a510e433f8aac7efeac6faa1e5059` | 29 September 2026 UTC |
| World Bank | Population 2020 dan metadata country API v2 | 29 September 2026 UTC |
| PostgreSQL asset model | Snapshot 2020 | Dimuat 29 September 2026 UTC |
| PostgreSQL historical model | Data tersedia sampai 2025; comparison cutoff 2022 | Dimuat 29 September 2026 UTC |

Tanggal eksekusi validation gate disimpan sebagai `generated_at_utc` pada `reports/phase4/validation_summary.json`. Tabel di atas menjelaskan cutoff data, bukan klaim bahwa sumber menggambarkan kondisi kalender 2026.

## Aturan komunikasi

- Selalu sebut unit, periode, dan populasi pembanding.
- Gunakan “percentage points” untuk perubahan share.
- Gunakan istilah “indikasi risiko” untuk umur aset, bukan kepastian stranded asset.
- Pisahkan fakta dari interpretasi dan rekomendasi.
- Jangan menyajikan tahun 2025 sebagai perbandingan global penuh sampai coverage memadai.
