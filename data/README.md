# Data simulasi

- Versi data: v1
- Tanggal dibuat: 28 Okt 2026
- Seed: 29260302
- Data tidak disimpan di repo. Dibuat ulang (hasil identik) dengan:

```
pip install numpy pandas openpyxl Faker reportlab Pillow   # sesuai impor skrip
python scripts/generate_data.py
```

- Hasil di `data/sim/`: `unit_result.csv` (50.312 baris), `dim_lot.csv`, `dim_operator.csv`, `ground_truth_dirty.csv`, `ground_truth.json`.
- Uji determinisme: dijalankan 2x, SHA-256 semua berkas identik. Daftar hash ada di repo DataCenter, `simulasi/fingerprints/project-29.sha256`.
