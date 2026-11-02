# Aturan analisis (Tahap A, langkah 1)

Aturan ini ditetapkan sebelum uji dijalankan dan dipakai apa adanya oleh `06_stats_tests.py`. Nilai konstanta ada di `code/common.py`.

| Hal | Aturan |
|---|---|
| Defect rate | NG ÷ unit diinspeksi, per level faktor. Confidence interval 95% memakai metode Wilson. |
| Faktor | Shift (2), operator (20), lot chip LED (40), supplier (3), model lampu (3), pengalaman operator (2: baru atau berpengalaman). |
| Pengalaman operator | "Baru" jika `hire_date` pada atau setelah 2026-03-02 (awal data): OP19 dan OP20. Lainnya "berpengalaman". |
| Unit uji | Satu level lawan sisanya (tabel 2x2). Faktor dua level (shift, pengalaman) membandingkan level kedua dengan level pembanding (Shift 1, berpengalaman). |
| Level terlalu kecil | n < 30: tidak diuji, label "Data belum cukup". |
| Syarat uji | Expected count terkecil ≥ 5: chi-square Pearson tanpa koreksi kontinuitas (sama dengan `CHISQ.TEST` Excel). Di bawah 5: Fisher exact. Semua uji dua sisi. |
| Signifikansi | α = 5%. |
| Banyak perbandingan | Koreksi per keluarga faktor (operator 20 uji, lot 40, supplier 3, model 3, shift 1, pengalaman 1). Benjamini-Hochberg (BH) sebagai koreksi utama, Bonferroni sebagai pembanding. |
| Label level | Terbukti (p BH < 0,05) · Noise (tidak lolos koreksi) · Data belum cukup (n < 30) · Pembanding. |
| Ukuran efek | Odds ratio dan CI 95% (Woolf, koreksi Haldane bila ada sel nol); Cramér's V untuk uji keseluruhan per faktor. |
| Faktor mandiri | Regresi logistik pada kasus lengkap (operator dan lot terisi): shift + model + supplier + pengalaman operator, BH antar suku. Uji rasio kemungkinan untuk kelompok operator, lot, dan model pada model penuh. |
| Dampak | (defect rate level − defect rate baseline) × jumlah unit level; baseline = unit lain pada faktor yang sama. Periode data sekitar 6 bulan, diproyeksikan ke 12 bulan dengan faktor 2. Dilabeli estimated dan simulated. |
| Data kotor | Lihat `cleaning_log.md`. Baris dengan operator kosong atau lot tidak dikenal tetap dipakai untuk faktor lain. |

## Penafsiran yang ditetapkan sendiri (rancangan tidak mendefinisikannya)

- Keluarga koreksi per faktor, bukan satu keluarga untuk semua uji.
- Definisi "operator baru" berdasarkan tanggal masuk (di atas).
- Proyeksi 12 bulan = 2 × periode data.
- Pareto 80%: jumlah jenis defect terkecil yang kumulatifnya mencapai 80% atau lebih.
