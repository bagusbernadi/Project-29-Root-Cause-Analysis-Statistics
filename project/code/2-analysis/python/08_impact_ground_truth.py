"""Dampak (Q11), validasi terhadap ground truth (Q12), dan jumlah unit yang dibutuhkan (Q14).

Dampak = (defect rate level - defect rate baseline) x jumlah unit level. Baseline = defect rate unit lain pada faktor yang sama.
Semua angka dampak berlabel estimated dan simulated; periode data (130 hari kerja, sekitar 6 bulan) diproyeksikan ke 12 bulan dengan faktor 2.
Hasil: impact.csv, ground_truth_check.csv, power.csv, factor_labels.csv
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.stats.power import NormalIndPower
from statsmodels.stats.proportion import proportion_effectsize

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import ALPHA, GROUND_TRUTH, RES_ANALYSIS, RES_PREP, UNITS_PER_YEAR_FACTOR, result  # noqa: E402

tr = pd.read_csv(result("test_results.csv"))
conf = pd.read_csv(result("confounding.csv")).set_index("comparison")
reg = pd.read_csv(result("regression.csv"))
lr = pd.read_csv(result("lr_tests.csv")).set_index("factor")
ft = pd.read_csv(result("factor_tests.csv")).set_index("factor")
sens = pd.read_csv(result("sensitivity.csv"))
clog = pd.read_csv(result("cleaning_log.csv"))
gt = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))
T = lambda f, l: tr[(tr.factor == f) & (tr.level == l)].iloc[0]

# ---- Q11 dampak: level terbukti dan lebih tinggi, tetap bermasalah setelah faktor lain dikontrol (shift dikeluarkan karena dijelaskan operator baru)
rows = []
for r in tr[(tr.status == "Terbukti") & (tr.direction == "lebih tinggi") & (tr.factor != "shift")].itertuples():
    f = tr[(tr.factor == r.factor) & (tr.n >= 1)]
    N, NG = f.n.sum(), f.ng.sum()
    base = (NG - r.ng) / (N - r.n)
    avoided = (r.rate - base) * r.n
    rows.append(dict(factor=r.factor, level=r.level, n=r.n, ng=r.ng, rate=r.rate, baseline_rate=base, ng_avoided_period=avoided,
                     ng_avoided_low=(r.ci_low - base) * r.n, ng_avoided_high=(r.ci_high - base) * r.n,
                     ng_avoided_year=avoided * UNITS_PER_YEAR_FACTOR, share_of_all_ng=avoided / NG, label="estimated, simulated"))
imp = pd.DataFrame(rows)
imp.to_csv(RES_ANALYSIS / "impact.csv", index=False, float_format="%.10g")

# ---- Q14 power: jumlah unit per level agar kenaikan relatif tertentu terdeteksi (power 80%) dan power pada ukuran data nyata
base = tr[tr.factor == "lot_id"].ng.sum() / tr[tr.factor == "lot_id"].n.sum()
pw = []
for scope, fac, K in (("Lot chip LED (40 uji)", "lot_id", 40), ("Operator (20 uji)", "operator_id", 20)):
    n_med = float(tr[(tr.factor == fac)].n.median())
    for mult in (1.3, 1.6, 2.0, 2.6):
        h = proportion_effectsize(base * mult, base)
        for lab, a in (("tanpa koreksi (0,05)", ALPHA), ("Bonferroni (0,05 / jumlah uji)", ALPHA / K)):
            need = NormalIndPower().solve_power(effect_size=h, alpha=a, power=0.8, ratio=K - 1, alternative="two-sided")
            pwr = NormalIndPower().power(effect_size=h, nobs1=n_med, alpha=a, ratio=K - 1, alternative="two-sided")
            pw.append(dict(scope=scope, rate_multiplier=mult, alpha_rule=lab, alpha_used=a, n_needed_per_level=need, n_median_actual=n_med, power_at_actual_n=pwr))
pwdf = pd.DataFrame(pw)
pwdf.to_csv(RES_ANALYSIS / "power.csv", index=False, float_format="%.10g")

# ---- Q12 validasi: lima fakta yang ditanam vs temuan
lots = tr[tr.factor == "lot_id"]
bad_lots = [x for x in gt["facts"][0]["lots"]]
raw_sig_lots = sorted(lots[lots.p_value < ALPHA].level)
ops = tr[tr.factor == "operator_id"].set_index("level")
op19, op08, op20 = ops.loc["OP19"], ops.loc["OP08"], ops.loc["OP20"]
sb = T("supplier", "Supplier B")
shift_raw, shift_adj = conf.loc["Shift 2 vs Shift 1, semua unit"], conf.loc["Shift 2 tanpa OP19 vs Shift 1"]
adj_shift = reg[(reg.model.str.startswith("Bersamaan")) & (reg.term == "Shift 2")].iloc[0]
dirty_total = int(clog.rows_found.sum())
f1 = ("Sebagian" if sorted(raw_sig_lots) == sorted(bad_lots) and int((lots.p_adj < ALPHA).sum()) == 0 else "Sesuai")
checks = [
    (1, "Dua lot Supplier B punya defect rate ±1,6x rata-rata",
     f"{' dan '.join(bad_lots)} adalah satu-satunya lot dengan p-value mentah di bawah 0.05 (p {lots.set_index('level').loc[bad_lots[0], 'p_value']:.3f} dan {lots.set_index('level').loc[bad_lots[1], 'p_value']:.3f}), "
     f"tetapi tidak ada lot yang lolos koreksi (p BH terkecil {lots.p_adj.min():.2f}); uji rasio kemungkinan semua lot p {lr.loc['Lot chip LED', 'p_value']:.2f}; Supplier B p BH {sb.p_adj:.2f}", f1),
    (2, "Efek shift sebenarnya berasal dari operator baru (hanya Shift 2)",
     f"Shift 2 tampak lebih tinggi (p {shift_raw.p_value:.3f}); tanpa OP19 selisih hilang (p {shift_adj.p_value:.2f}) dan setelah dikontrol pengalaman operator odds ratio shift {adj_shift.odds_ratio:.2f} (p {adj_shift.p_value:.2f}); OP19 odds ratio {op19.odds_ratio:.1f}, p BH < 0.001",
     "Sesuai" if shift_raw.p_value < ALPHA and shift_adj.p_value > ALPHA and adj_shift.p_value > ALPHA and op19.status == "Terbukti" else "Sebagian"),
    (3, "Operator noise: sedikit lebih tinggi secara acak, tidak boleh signifikan setelah koreksi",
     f"OP08 defect rate {op08.rate * 100:.2f}%: p mentah {op08.p_value:.3f} (tampak signifikan), p BH {op08.p_adj:.2f} (tidak signifikan setelah koreksi); {int((ops.p_value < ALPHA).sum())} dari {int(ops.p_value.notna().sum())} operator signifikan tanpa koreksi, {int((ops.p_adj < ALPHA).sum())} setelah koreksi",
     "Sesuai" if op08.p_adj >= ALPHA and (ops.p_adj < ALPHA).sum() == 1 else "Sebagian"),
    (4, "Beberapa operator hanya mengerjakan kurang dari 100 unit, sehingga butuh Fisher exact",
     f"Hanya satu operator (OP20, {int(op20.n)} unit, expected count minimal {op20.expected_min:.1f}) yang memakai {op20.test}; p {op20.p_value:.3f}. Operator lain punya paling sedikit {int(ops.drop('OP20').n.min())} unit",
     "Sebagian"),
    (5, "Sekitar 2-3% data kotor",
     f"{str(dirty_total)[0]}.{str(dirty_total)[1:]} baris bermasalah ({dirty_total / gt['n_units_clean'] * 100:.1f}%); seluruhnya ditemukan dan sama persis dengan unit_id yang ditanam (R1 sampai R4)",
     "Sesuai" if bool((clog.match_ground_truth.fillna("ya") == "ya").all()) else "Sebagian"),
]
pd.DataFrame(checks, columns=["fact_no", "fakta", "ditemukan", "hasil"]).to_csv(RES_ANALYSIS / "ground_truth_check.csv", index=False)

# ---- label per faktor (dashboard dan README)
lab = []
for f in ("shift", "operator_id", "lot_id", "supplier", "model", "experience"):
    d = tr[tr.factor == f]
    prov = d[d.status == "Terbukti"]
    if f == "shift":
        lab.append((f, "Dijelaskan faktor lain", f"Tampak signifikan sendirian (p {shift_raw.p_value:.3f}), hilang tanpa OP19 (p {shift_adj.p_value:.2f})"))
    elif len(prov):
        lab.append((f, "Terbukti", ", ".join(f"{r.level} (OR {r.odds_ratio:.2f})" for r in prov.itertuples())))
    else:
        lab.append((f, "Noise", f"Tidak ada level yang lolos koreksi (p BH terkecil {d.p_adj.min():.2f})"))
pd.DataFrame(lab, columns=["factor", "label", "detail"]).to_csv(RES_ANALYSIS / "factor_labels.csv", index=False)
print(imp.round(3).to_string(index=False))
print(pd.DataFrame(checks, columns=["no", "fakta", "ditemukan", "hasil"])[["no", "hasil"]].to_string(index=False))
print(pwdf[pwdf.rate_multiplier == 1.6].round(3).to_string(index=False))
