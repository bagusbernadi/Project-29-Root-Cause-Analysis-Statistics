"""Project 29: hasil inspeksi per unit lampu LED (simulasi) dengan shift, operator, lot, dan supplier. Seed tetap.

+-50.000 unit, +-6 bulan (130 hari kerja), model 5W/9W/12W, 2 shift, 20 operator (kode), 40 lot dari 3 supplier, NG +-2,5%.
Hasil (data/sim/): unit_result.csv, dim_lot.csv, dim_operator.csv, ground_truth.json, ground_truth_dirty.csv.
Tabel `test_results` (hasil uji statistik) dihasilkan oleh analisis, bukan oleh skrip ini.
Jalankan: python scripts/generate_data.py   (versi data: v1)
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sim"
SEED = 29260302
DATA_VERSION = "v1"
N_UNITS, N_DAYS, START = 50_000, 130, "2026-03-02"
MODELS, MODEL_P, MODEL_F = ["5W", "9W", "12W"], [0.35, 0.40, 0.25], {"5W": 0.95, "9W": 1.00, "12W": 1.08}
BASE_RATE = 0.0225
N_LOTS, LOT_DAYS = 40, N_DAYS / 40
BAD_LOTS = (10, 28)                    # dua lot Supplier B (indeks lot), NG +-1,6x
BAD_LOT_F = 1.6
NEW_OP = dict(operator="OP19", shift="Shift 2", start_day=20, share=0.14, factor=2.6)   # operator baru hanya di Shift 2
SMALL_OP = dict(operator="OP20", n=40, days=(100, 101), ng=3)                            # sampel kecil (Fisher exact)
NOISE_OP = dict(operator="OP08", share_s1=0.016, factor=1.6)                             # sampel kecil, efek tidak terdeteksi
DEFECTS = ["LED-OPEN", "SOLDER", "DRIVER", "HOUSING", "COSMETIC"]
DEFECT_W = [0.30, 0.25, 0.20, 0.15, 0.10]
DIRTY_RATE = 0.025

rng = np.random.default_rng(SEED)
days = pd.bdate_range(START, periods=N_DAYS)
day_idx = np.sort(rng.integers(0, N_DAYS, N_UNITS))
shift = np.where(rng.random(N_UNITS) < 0.5, "Shift 1", "Shift 2")
model = rng.choice(MODELS, N_UNITS, p=MODEL_P)

# operator reguler: OP01-OP09 Shift 1, OP10-OP18 Shift 2
s1 = np.array([f"OP{i:02d}" for i in range(1, 10)])
s2 = np.array([f"OP{i:02d}" for i in range(10, 19)])
w1 = np.array([1.0] * 9); w1[7] = NOISE_OP["share_s1"] * 9 / (1 - NOISE_OP["share_s1"]) * 1.0   # OP08 kecil
op = np.empty(N_UNITS, dtype=object)
m1 = shift == "Shift 1"
op[m1] = rng.choice(s1, m1.sum(), p=w1 / w1.sum())
m2 = shift == "Shift 2"
op[m2] = rng.choice(s2, m2.sum())
new_mask = m2 & (day_idx >= NEW_OP["start_day"]) & (rng.random(N_UNITS) < NEW_OP["share"])
op[new_mask] = NEW_OP["operator"]
cand = np.flatnonzero(m1 & (day_idx >= SMALL_OP["days"][0]) & (day_idx <= SMALL_OP["days"][1]))
small_idx = rng.choice(cand, SMALL_OP["n"], replace=False)
op[small_idx] = SMALL_OP["operator"]

lot_i = np.minimum((day_idx / LOT_DAYS).astype(int), N_LOTS - 1)
sup = np.array(list("ABC"))[lot_i % 3]
lot_id = np.array([f"L{s}{i + 1:02d}" for s, i in zip(sup, lot_i)])

p = BASE_RATE * np.vectorize(MODEL_F.get)(model)
p = np.where(np.isin(lot_i, BAD_LOTS), p * BAD_LOT_F, p)
p = np.where(op == NEW_OP["operator"], p * NEW_OP["factor"], p)
p = np.where(op == NOISE_OP["operator"], p * NOISE_OP["factor"], p)
ng = rng.random(N_UNITS) < p
ng_small = rng.choice(small_idx, SMALL_OP["ng"], replace=False)       # tepat 3 NG dari 40 unit
ng[small_idx] = False
ng[ng_small] = True
code = np.where(ng, rng.choice(DEFECTS, N_UNITS, p=DEFECT_W), "")

df = pd.DataFrame({"unit_id": [f"U{i + 1:06d}" for i in range(N_UNITS)], "inspect_date": days[day_idx].date,
                   "model": model, "shift": shift, "operator_id": op, "lot_id": lot_id,
                   "result": np.where(ng, "NG", "OK"), "defect_code": code})
truth = df.copy()

# data kotor (+-2,5%): operator kosong, hasil tidak baku, lot tidak dikenal, baris ganda
n_dirty = int(round(DIRTY_RATE * N_UNITS))
pick = rng.permutation(N_UNITS)[:n_dirty]
kinds = ["blank_operator", "result_variant", "unknown_lot", "duplicate_row"]
dirty, dup = [], []
for k, i in enumerate(pick):
    kind = kinds[k % 4]
    if kind == "blank_operator":
        df.at[i, "operator_id"] = None
    elif kind == "result_variant":
        df.at[i, "result"] = {"OK": ["ok", "PASS", "OK "], "NG": ["ng", "FAIL", "NG "]}[df.at[i, "result"]][int(rng.integers(0, 3))]
    elif kind == "unknown_lot":
        df.at[i, "lot_id"] = "LX99"
    else:
        dup.append(i)
    dirty.append([df.at[i, "unit_id"], kind])
df["_o"] = np.arange(N_UNITS, dtype=float)
d2 = df.loc[dup].copy(); d2["_o"] += 0.5
df = pd.concat([df, d2]).sort_values("_o").drop(columns="_o").reset_index(drop=True)

dim_lot = pd.DataFrame({"lot_id": [f"L{'ABC'[i % 3]}{i + 1:02d}" for i in range(N_LOTS)],
                        "supplier": [f"Supplier {'ABC'[i % 3]}" for i in range(N_LOTS)],
                        "receive_date": [days[min(int(i * LOT_DAYS), N_DAYS - 1)].date() for i in range(N_LOTS)]})
ops = [f"OP{i:02d}" for i in range(1, 21)]
first = truth.groupby("operator_id")["inspect_date"].min()
dim_op = pd.DataFrame({"operator_id": ops,
                       "hire_date": [str(first.get(o, days[0].date())) if o in (NEW_OP["operator"], SMALL_OP["operator"]) else "2025-01-06" for o in ops],
                       "primary_shift": ["Shift 1" if o in set(s1) | {SMALL_OP["operator"]} else "Shift 2" for o in ops]})

OUT.mkdir(parents=True, exist_ok=True)
df.to_csv(OUT / "unit_result.csv", index=False)
dim_lot.to_csv(OUT / "dim_lot.csv", index=False)
dim_op.to_csv(OUT / "dim_operator.csv", index=False)
pd.DataFrame(dirty, columns=["unit_id", "dirty_type"]).to_csv(OUT / "ground_truth_dirty.csv", index=False)
rate = lambda d: round(float((d["result"] == "NG").mean()) * 100, 3)
gt = {"seed": SEED, "version": DATA_VERSION, "n_units_clean": N_UNITS, "rows_with_dirt": len(df), "ng_rate_pct_clean": rate(truth),
      "facts": [
          {"id": 1, "fact": "Dua lot Supplier B punya defect rate +-1,6x rata-rata", "lots": [f"LB{i + 1:02d}" for i in BAD_LOTS], "factor": BAD_LOT_F},
          {"id": 2, "fact": "Efek shift sebenarnya berasal dari operator baru (hanya Shift 2)", **NEW_OP,
           "ng_rate_pct": {"Shift 1": rate(truth[truth["shift"] == "Shift 1"]), "Shift 2": rate(truth[truth["shift"] == "Shift 2"]),
                           "Shift 2 tanpa OP19": rate(truth[(truth["shift"] == "Shift 2") & (truth["operator_id"] != "OP19")])}},
          {"id": 3, "fact": "Operator noise: sampel kecil, efek tidak terdeteksi", **NOISE_OP, "n_units": int((truth["operator_id"] == "OP08").sum())},
          {"id": 4, "fact": "Operator sampel kecil (butuh Fisher exact)", **SMALL_OP},
          {"id": 5, "fact": "Data kotor", "rate": DIRTY_RATE, "types": kinds}]}
(OUT / "ground_truth.json").write_text(json.dumps(gt, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
print(f"unit_result {len(df)} baris (NG bersih {rate(truth)}%), kotor {len(dirty)}; ", gt["facts"][1]["ng_rate_pct"])
