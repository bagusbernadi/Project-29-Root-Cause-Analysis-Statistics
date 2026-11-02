# Data simulasi

- Versi data: v1
- Tanggal dibuat: 28 Okt 2026
- Seed: 29260302
- Data mentah, data bersih, dan database tidak disimpan di repo. Dibuat ulang (hasil identik) dengan:

```
pip install -r project/requirements.txt
python project/code/1-data-preparation/python/01_generate_data.py
```

- Hasil di `project/data/raw/` (tidak di-commit): `unit_result.csv` (50.312 baris), `dim_lot.csv`, `dim_operator.csv`. Fakta yang ditanam ada di repo: `project/data/ground_truth.json` dan `project/data/ground_truth_dirty.csv`.
- Data bersih (`project/data/clean/`, tidak di-commit) dibuat oleh `02_clean_data.py`; database `project/rca.duckdb` oleh `03_build_db.py`.
- Uji determinisme: SHA-256 semua berkas identik dengan daftar di repo DataCenter, `simulasi/fingerprints/project-29.sha256`.
- Lisensi: tidak ada dataset pihak ketiga (data buatan sendiri).
