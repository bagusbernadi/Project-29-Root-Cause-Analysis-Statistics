[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 29: Root Cause Analysis Statistics

**Halaman web:** https://bagusbernadi.github.io/Project-29-Root-Cause-Analysis-Statistics/

**Status: Selesai di branch `project-29-build` (menunggu tinjauan sebelum digabung ke `main`).** Halaman rancangan dan Report ada di [`design-and-report/index.html`](design-and-report/index.html).

**Tujuan:** menguji secara statistik apakah perbedaan defect rate antar shift, operator, lot material, dan supplier benar-benar nyata atau hanya variasi acak, lalu mengukur seberapa kuat setiap faktor terkait NG, agar investigasi difokuskan pada faktor yang terbukti.

| | |
|---|---|
| Kategori | Manufaktur (pabrik lampu LED) |
| Tingkat | Menengah |
| Data | Simulasi: hasil inspeksi per unit dengan shift, operator, lot, dan supplier (generator disertakan) |
| Tools | Python (pandas, SciPy, statsmodels), DuckDB + SQL, Excel (cek silang), Streamlit + Plotly |

## 1. Problem

**Pertanyaan utama:** Apakah perbedaan defect rate antar shift, operator, atau lot material benar-benar signifikan secara statistik, dan faktor mana yang paling kuat terkait dengan NG?

Rancangan memecahnya menjadi 14 pertanyaan (9 Utama, 4 Pendukung, 1 Tambahan). Q2 (NG per stasiun inspeksi) tidak bisa dijawab karena data simulasi v1 tidak punya kolom stasiun.

## 2. Data

- **Data adalah simulasi buatan sendiri.** Angka menggambarkan simulasi, bukan lini produksi. Dibuat oleh `project/code/1-data-preparation/python/01_generate_data.py` (Versi: v1; Tanggal dibuat: 28 Okt 2026; Seed: 29260302). Tidak memakai dataset publik atau data perusahaan, jadi tidak ada masalah lisensi.
- 50.000 unit diinspeksi (±6 bulan, 130 hari kerja), 1.285 unit NG (2,57%), 3 model, 2 shift, 20 operator (kode), 40 lot dari 3 supplier.
- Data mentah 50.312 baris, 1.250 baris bermasalah (2,5%): baris ganda, hasil tidak baku, operator kosong, lot tidak dikenal. Semuanya ditemukan dan sama persis dengan yang ditanam (`project/docs/cleaning_log.md`).
- Tabel di DuckDB: `unit_result`, `dim_lot`, `dim_operator`, `test_results`. Jejak pembuatan data (seed, commit, SHA-256) ada di repo `DataCenter`, folder `simulasi/`.

## 3. Analysis

Alur uji: defect rate + CI Wilson → chi-square (atau Fisher exact bila expected count < 5) → koreksi Benjamini-Hochberg dan Bonferroni → odds ratio + CI 95% → regresi logistik. Aturan lengkap: `project/docs/analysis_rules.md`. Hasil dicek silang SQL vs pandas dan dengan Excel.

- **Pareto:** 4 jenis defect pertama menyumbang 89,4% NG; terbesar LED-OPEN (31,0%).
- **Operator:** 3 dari 20 operator tampak signifikan tanpa koreksi, hanya 1 setelah koreksi: OP19 (defect rate 6,2%, odds ratio 2,73, p BH < 0,001). OP08 tampak buruk sendirian (p 0,018) tetapi tidak setelah koreksi (p BH 0,18).
- **Shift:** Shift 2 tampak lebih tinggi (2,74% vs 2,40%, p 0,015), tetapi tanpa OP19 selisihnya hilang (p 0,46); pada regresi bersamaan odds ratio shift 0,96 (p 0,46).
- **Lot dan supplier:** tidak ada lot yang lolos koreksi untuk 40 lot (p BH terkecil 0,70); Supplier B belum terbukti (p BH 0,13). Dua lot yang ditanam lebih buruk (LB11, LB29) memang satu-satunya lot dengan p mentah di bawah 0,05, tetapi tidak bertahan setelah koreksi.
- **Model lampu:** 12W sedikit lebih tinggi (odds ratio 1,18, p BH 0,026); efek kecil dan memang ditanam generator.
- **Jumlah unit (Q14):** untuk kenaikan defect rate 1,6 kali pada satu lot, dibutuhkan sekitar 2.276 unit per lot dengan koreksi Bonferroni (data punya sekitar 1.152); power pada ukuran data ini 37% dengan koreksi dan 83% tanpa koreksi.

## 4. Recommendation

- **Terbukti, perlu ditindaklanjuti:** pelatihan dan pendampingan operator baru (OP19, odds ratio 2,73); efek shift tidak perlu ditindak sendiri karena dijelaskan operator baru.
- **Noise, hanya dipantau:** operator lain (termasuk OP08), shift, dan supplier. Jangan menegur orang atau mengganti supplier hanya dari p-value mentah.
- **Data belum cukup:** lot. Kumpulkan lebih banyak unit per lot (sekitar 2.276 untuk efek 1,6 kali) atau gabungkan lot per supplier sebelum menyimpulkan.

## 5. Impact

Semua angka berlabel `estimated` dan `simulated`. Unit NG terhindari = (defect rate faktor − defect rate baseline) × volume faktor; periode data ±6 bulan diproyeksikan ke 12 bulan.

- OP19 dibawa ke tingkat baseline: sekitar 110 unit NG per periode data, ±220 per tahun (8,6% dari semua NG).

## Batasan

- Data adalah simulasi; fakta yang ditemukan adalah fakta yang ditanam sendiri.
- Uji statistik menunjukkan keterkaitan, bukan sebab. Faktor yang tidak dicatat (mesin, suhu ruangan) bisa menjadi penyebab sebenarnya.
- Dua lot yang ditanam tidak terbukti pada ukuran data ini (Fakta 1 hanya sebagian). Q2 tidak terjawab (tidak ada kolom stasiun). Hanya satu operator bersampel kecil (OP20), bukan beberapa.
- Keluarga koreksi, definisi operator baru, dan proyeksi 12 bulan adalah penafsiran sendiri (`project/docs/analysis_rules.md`).
- Dashboard belum di-deploy ke Streamlit Community Cloud; one-sheet belum diuji ke pembaca awam; slide opsional tidak dibuat. Cek silang Excel dihitung LibreOffice.
- Hasil per operator dipakai untuk perbaikan proses dan pelatihan, bukan untuk menilai orang.

## Menjalankan

Dari folder `project/` (Python 3.13; hasil identik diuji pada numpy 2.5.3 dan pandas 3.0.5):

```
pip install -r requirements.txt
python code/1-data-preparation/python/01_generate_data.py
python code/1-data-preparation/python/02_clean_data.py
python code/1-data-preparation/python/03_build_db.py
python code/2-analysis/python/04_run_queries.py
python code/2-analysis/python/05_crosscheck.py
python code/2-analysis/python/06_stats_tests.py
python code/2-analysis/python/07_excel_crosscheck.py      # butuh LibreOffice (soffice)
python code/2-analysis/python/08_impact_ground_truth.py
python code/3-presentation/python/09_build_dashboard_data.py
python code/3-presentation/python/10_build_infographic.py
python code/3-presentation/python/11_build_notebook.py
python code/3-presentation/python/12_build_readme.py
streamlit run code/3-presentation/streamlit/app.py
python ../design-and-report/src/build_report.py            # dari root repo
```

## Struktur repository

```
README.md
index.html                     pengalihan ke design-and-report/
design-and-report/             index.html (tab Design dan Report), src/ (page_v1.html, report.css, report_lib.py, build_report.py)
project/
  code/
    common.py
    1-data-preparation/        python/ (01 generate, 02 clean, 03 build db)  sql/ (01_schema.sql)
    2-analysis/                python/ (04 queries, 05 crosscheck, 06 stats, 07 excel, 08 impact)  sql/
    3-presentation/            python/ (09 sampai 12, test_app.py)  streamlit/app.py
  results/                     CSV hasil per tahap, crosscheck.xlsx, analysis.ipynb, onesheet.pdf/.png
  data/                        ground_truth.json, ground_truth_dirty.csv, README.md (raw/ dan clean/ tidak di-commit)
  docs/                        analysis_rules.md, data_dictionary.md, cleaning_log.md
  requirements.txt
```
