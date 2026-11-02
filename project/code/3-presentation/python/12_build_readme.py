"""Menulis README.md di root repo dari CSV hasil (angka tidak diketik tangan)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import ROOT, result  # noqa: E402

R = lambda n: pd.read_csv(result(n))
D = lambda x, d=1: f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
P3 = lambda p: "< 0,001" if p < 0.001 else D(p, 3)
tr, par, conf, imp, pw, gt = R("test_results.csv"), R("pareto.csv"), R("confounding.csv"), R("impact.csv"), R("power.csv"), R("ground_truth_check.csv")
reg, lr, dq, sens, ft = R("regression.csv"), R("lr_tests.csv"), R("data_quality_summary.csv"), R("sensitivity.csv"), R("factor_tests.csv").set_index("factor")
ops, lots, sup = (tr[tr.factor == f].set_index("level") for f in ("operator_id", "lot_id", "supplier"))
sh = tr[tr.factor == "shift"].set_index("level")
mdl = tr[(tr.factor == "model") & (tr.level == "12W")].iloc[0]
radj = reg[reg.model.str.startswith("Bersamaan")].set_index("term")
c0, c1 = conf.iloc[0], conf.iloc[1]
n_ng = int(par.ng.sum())
k80 = int((par.cum_share < 0.8).sum() + 1)
p16 = pw[(pw.rate_multiplier == 1.6) & (pw.scope.str.startswith("Lot"))].set_index("alpha_rule")
nb = ops[ops.status == "Terbukti"]
i19 = imp[imp.level == "OP19"].iloc[0]
pw_unc, pw_bon = p16.iloc[0], p16.iloc[1]
readme = f"""[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 29: Root Cause Analysis Statistics

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
- {D(dq.clean_rows[0], 0)} unit diinspeksi (±6 bulan, 130 hari kerja), {D(n_ng, 0)} unit NG ({D(n_ng / dq.clean_rows[0] * 100, 2)}%), 3 model, 2 shift, 20 operator (kode), 40 lot dari 3 supplier.
- Data mentah {D(dq.raw_rows[0], 0)} baris, {D(dq.bad_rows[0], 0)} baris bermasalah ({D(dq.bad_pct[0], 1)}%): baris ganda, hasil tidak baku, operator kosong, lot tidak dikenal. Semuanya ditemukan dan sama persis dengan yang ditanam (`project/docs/cleaning_log.md`).
- Tabel di DuckDB: `unit_result`, `dim_lot`, `dim_operator`, `test_results`. Jejak pembuatan data (seed, commit, SHA-256) ada di repo `DataCenter`, folder `simulasi/`.

## 3. Analysis

Alur uji: defect rate + CI Wilson → chi-square (atau Fisher exact bila expected count < 5) → koreksi Benjamini-Hochberg dan Bonferroni → odds ratio + CI 95% → regresi logistik. Aturan lengkap: `project/docs/analysis_rules.md`. Hasil dicek silang SQL vs pandas dan dengan Excel.

- **Pareto:** {k80} jenis defect pertama menyumbang {D(par.cum_share.iloc[k80 - 1] * 100)}% NG; terbesar {par.defect_code.iloc[0]} ({D(par.share.iloc[0] * 100)}%).
- **Operator:** {int((ops.p_value < 0.05).sum())} dari {int(ops.p_value.notna().sum())} operator tampak signifikan tanpa koreksi, hanya {int((ops.p_adj < 0.05).sum())} setelah koreksi: {', '.join(nb.index)} (defect rate {D(nb.rate.iloc[0] * 100)}%, odds ratio {D(nb.odds_ratio.iloc[0], 2)}, p BH {P3(nb.p_adj.iloc[0])}). OP08 tampak buruk sendirian (p {P3(ops.loc['OP08', 'p_value'])}) tetapi tidak setelah koreksi (p BH {D(ops.loc['OP08', 'p_adj'], 2)}).
- **Shift:** Shift 2 tampak lebih tinggi ({D(c0.rate_shift2 * 100, 2)}% vs {D(c0.rate_shift1 * 100, 2)}%, p {P3(c0.p_value)}), tetapi tanpa OP19 selisihnya hilang (p {D(c1.p_value, 2)}); pada regresi bersamaan odds ratio shift {D(radj.loc['Shift 2', 'odds_ratio'], 2)} (p {D(radj.loc['Shift 2', 'p_value'], 2)}).
- **Lot dan supplier:** tidak ada lot yang lolos koreksi untuk 40 lot (p BH terkecil {D(lots.p_adj.min(), 2)}); Supplier B belum terbukti (p BH {D(sup.loc['Supplier B', 'p_adj'], 2)}). Dua lot yang ditanam lebih buruk ({', '.join(lots[lots.p_value < 0.05].index)}) memang satu-satunya lot dengan p mentah di bawah 0,05, tetapi tidak bertahan setelah koreksi.
- **Model lampu:** 12W sedikit lebih tinggi (odds ratio {D(mdl.odds_ratio, 2)}, p BH {D(mdl.p_adj, 3)}); efek kecil dan memang ditanam generator.
- **Jumlah unit (Q14):** untuk kenaikan defect rate 1,6 kali pada satu lot, dibutuhkan sekitar {D(pw_bon.n_needed_per_level, 0)} unit per lot dengan koreksi Bonferroni (data punya sekitar {D(pw_bon.n_median_actual, 0)}); power pada ukuran data ini {D(pw_bon.power_at_actual_n * 100, 0)}% dengan koreksi dan {D(pw_unc.power_at_actual_n * 100, 0)}% tanpa koreksi.

## 4. Recommendation

- **Terbukti, perlu ditindaklanjuti:** pelatihan dan pendampingan operator baru (OP19, odds ratio {D(i19.odds_ratio if 'odds_ratio' in i19 else nb.odds_ratio.iloc[0], 2)}); efek shift tidak perlu ditindak sendiri karena dijelaskan operator baru.
- **Noise, hanya dipantau:** operator lain (termasuk OP08), shift, dan supplier. Jangan menegur orang atau mengganti supplier hanya dari p-value mentah.
- **Data belum cukup:** lot. Kumpulkan lebih banyak unit per lot (sekitar {D(pw_bon.n_needed_per_level, 0)} untuk efek 1,6 kali) atau gabungkan lot per supplier sebelum menyimpulkan.

## 5. Impact

Semua angka berlabel `estimated` dan `simulated`. Unit NG terhindari = (defect rate faktor − defect rate baseline) × volume faktor; periode data ±6 bulan diproyeksikan ke 12 bulan.

- OP19 dibawa ke tingkat baseline: sekitar {D(i19.ng_avoided_period, 0)} unit NG per periode data, ±{D(i19.ng_avoided_year, 0)} per tahun ({D(i19.share_of_all_ng * 100)}% dari semua NG).

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
"""
(ROOT.parent / "README.md").write_text(readme, encoding="utf-8")
print("README.md ditulis,", len(readme), "karakter")
