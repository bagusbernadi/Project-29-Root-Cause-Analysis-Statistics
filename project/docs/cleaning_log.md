# Cleaning log

Dibuat otomatis oleh `02_clean_data.py`. Temuan dicocokkan dengan `data/ground_truth_dirty.csv` (unit_id yang sama, bukan hanya jumlahnya).

Baris mentah 50.312. baris bersih (satu baris per unit) 50.000. baris bermasalah 1.250 (2.48%).

| Aturan | Masalah | Ditemukan | Ditanam | Dibuang | Diperbaiki | Keputusan |
|---|---|---|---|---|---|---|
| R1 | Baris ganda (unit_id sama) | 312 | 312 | 312 | 0 | Baris kedua dibuang, satu baris per unit dipertahankan |
| R2 | Hasil tidak baku (ok, PASS, ng, FAIL, spasi) | 313 | 313 | 0 | 313 | Dibakukan menjadi OK atau NG |
| R3 | operator_id kosong | 313 | 313 | 0 | 0 | Baris dipertahankan; dikeluarkan hanya dari uji per operator dan regresi |
| R4 | lot_id tidak dikenal (LX99) | 312 | 312 | 0 | 0 | Baris dipertahankan; lot dan supplier dikosongkan, dikeluarkan hanya dari uji per lot/supplier dan regresi |
| R5 | Pemeriksaan konsistensi (6 aturan) | 0 | 0 | 0 | 0 | Tidak ada pelanggaran; data tidak diubah |

Pemeriksaan konsistensi R5: OK tanpa defect_code = 0, NG dengan defect_code = 0, tanggal di luar periode = 0, shift tidak valid = 0, model tidak valid = 0, unit_id ganda setelah R1 = 0.
