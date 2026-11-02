# Kamus data

Data simulasi (generator `01_generate_data.py`, seed 29260302, versi v1). Tabel ada di `rca.duckdb`.

## unit_result (satu baris = satu unit lampu yang diinspeksi; 50.000 baris setelah cleaning)
| Kolom | Arti |
|---|---|
| unit_id | Kode unit (U000001 dan seterusnya), kunci utama |
| inspect_date | Tanggal inspeksi (130 hari kerja mulai 2026-03-02) |
| model | 5W, 9W, atau 12W |
| shift | Shift 1 atau Shift 2 |
| operator_id | Kode operator (OP01 sampai OP20), boleh kosong (cleaning R3) |
| lot_id | Kode lot chip LED (LA/LB/LC + nomor), boleh kosong (cleaning R4) |
| result | OK atau NG |
| defect_code | LED-OPEN, SOLDER, DRIVER, HOUSING, COSMETIC (hanya untuk NG) |

## dim_lot (satu baris = satu lot chip LED; 40 baris)
lot_id, supplier (Supplier A/B/C), receive_date.

## dim_operator (satu baris = satu operator, kode tanpa nama; 20 baris)
operator_id, hire_date, primary_shift.

## test_results (satu baris = satu level faktor; diisi oleh `06_stats_tests.py`)
factor, level, n, ng, rate, ci_low, ci_high (Wilson 95%), expected_min, test (Chi-square / Fisher exact), p_value, p_adj (BH), p_adj_bonf, odds_ratio, or_ci_low, or_ci_high, family_size, status, direction.

## Perbedaan dengan rancangan
Rancangan menyebut kolom `serial_no`, `driver_lot`, `inspect_station`, `chip_lot`, `date`, serta `material`, `qty` pada dim_lot dan `experience_months` pada dim_operator. Generator v1 tidak membuat kolom itu; nama kolom yang berbeda dan kolom yang tidak ada dicatat di Report bagian 3 dan 5.
