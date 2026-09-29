# Data mentah

Direktori ini menyimpan snapshot sumber yang tidak boleh diedit atau ditimpa oleh proses transformasi.

Jalankan perintah berikut dari root proyek:

```powershell
python src/download_wri.py
```

Pipeline memverifikasi SHA-256 terhadap snapshot WRI yang dipatok ke commit tertentu. Detail provenance tersimpan di `source_metadata.json`.

