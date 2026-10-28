[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 29: Root Cause Analysis Statistics

**Status: Design (rancangan).** Halaman rancangan ada di [`index.html`](index.html). Uji statistik, dashboard, dan angka hasil belum dikerjakan, sehingga bagian Analysis, Recommendation, dan Impact di bawah masih kosong.

**Tujuan:** menguji secara statistik apakah perbedaan defect rate antar shift, operator, lot material, dan supplier benar-benar nyata atau hanya variasi acak, lalu mengukur seberapa kuat setiap faktor terkait NG, agar investigasi difokuskan pada faktor yang terbukti.

| | |
|---|---|
| Kategori | Manufaktur (pabrik lampu LED) |
| Tingkat | Menengah |
| Data | Simulasi: hasil inspeksi per unit dengan shift, operator, lot, dan supplier (generator disertakan) |
| Tools | Python (pandas, SciPy, statsmodels), DuckDB + SQL, Excel (cek silang), Streamlit + Plotly |

## 1. Problem

**Pertanyaan utama:** Apakah perbedaan defect rate antar shift, operator, atau lot material benar-benar signifikan secara statistik, dan faktor mana yang paling kuat terkait dengan NG?

Rancangan memecahnya menjadi 14 pertanyaan (9 Utama, 4 Pendukung, 1 Tambahan) dalam 6 tema: gambaran, perbandingan, kekuatan, faktor mandiri, dampak, dan validitas.

## 2. Data

- Sumber: data simulasi buatan sendiri, dibuat oleh `scripts/generate_data.py` (Versi: v1; Tanggal dibuat: 28 Okt 2026; Seed: 29260302). Tidak memakai dataset publik atau data perusahaan. Operator ditulis sebagai kode.
- Konteks: lampu LED model 5W, 9W, dan 12W; 2 shift; ±20 operator; ±40 lot chip LED dari 3 supplier.
- Ukuran (perkiraan): ±50.000 unit diinspeksi selama ±6 bulan, dengan sekitar 2–3% NG.
- Rencana tabel: `unit_result`, `dim_lot`, `dim_operator`, `test_results`.
- Fakta yang sengaja ditanam: dua lot supplier B dengan defect rate ±1,6 kali rata-rata, efek shift yang sebenarnya berasal dari operator baru, satu operator noise, operator dengan sampel kecil (butuh Fisher exact), dan 2–3% data kotor.

## 3. Analysis

Belum dikerjakan. Alur uji: defect rate + confidence interval → chi-square (atau Fisher exact jika expected count < 5) → koreksi multiple testing (Benjamini-Hochberg, Bonferroni sebagai pembanding) → odds ratio + 95% CI → regresi logistik untuk faktor mandiri. Hasil dicek silang dengan Excel (CHISQ.TEST).

## 4. Recommendation

Belum dikerjakan. Output yang direncanakan: daftar faktor yang terbukti, faktor yang dianggap noise, dan faktor yang datanya belum cukup.

## 5. Impact

Belum dikerjakan. Rumus yang akan dipakai (semua hasil diberi label `estimated` dan `simulated`):

```
Unit NG terhindari = (defect rate faktor − defect rate baseline) × volume faktor
```

## Batasan yang sudah diketahui

- Uji statistik menunjukkan keterkaitan, bukan sebab.
- Banyak perbandingan sekaligus memperbesar peluang hasil signifikan yang hanya kebetulan, sehingga koreksi wajib.
- Faktor yang tidak dicatat (mesin, suhu ruangan) bisa menjadi penyebab sebenarnya.
- Signifikan belum tentu penting; odds ratio dan effect size selalu ditampilkan.
- Hasil per operator dipakai untuk perbaikan proses dan pelatihan, bukan untuk menilai orang.

## Struktur repository

```
index.html   Halaman rancangan project (bisa dibuka di browser atau lewat GitHub Pages)
README.md    Dokumen ini
```

Folder `docs/`, `data/`, `scripts/`, `sql/`, `notebooks/`, `dashboard/`, dan `outputs/` ditambahkan saat pengerjaan dimulai.
