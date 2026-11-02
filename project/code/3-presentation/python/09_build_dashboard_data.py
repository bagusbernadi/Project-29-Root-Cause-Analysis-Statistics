"""Menyiapkan CSV kecil untuk dashboard dan infografik dari hasil analisis (kolom dibulatkan, label sudah Bahasa Indonesia)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import FACTOR_LABEL, RES_PRESENT, result  # noqa: E402

tr = pd.read_csv(result("test_results.csv"))
tr["factor_label"] = tr.factor.map(FACTOR_LABEL)
cols = ["factor", "factor_label", "level", "n", "ng", "rate", "ci_low", "ci_high", "test", "p_value", "p_adj", "p_adj_bonf", "odds_ratio", "or_ci_low", "or_ci_high", "status", "direction"]
tr[cols].round(6).to_csv(RES_PRESENT / "dash_levels.csv", index=False)
pd.read_csv(result("pareto.csv")).round(6).to_csv(RES_PRESENT / "dash_pareto.csv", index=False)
fl = pd.read_csv(result("factor_labels.csv"))
fl["factor_label"] = fl.factor.map(FACTOR_LABEL)
fl.to_csv(RES_PRESENT / "dash_labels.csv", index=False)
pd.read_csv(result("regression.csv")).round(6).to_csv(RES_PRESENT / "dash_regression.csv", index=False)
pd.read_csv(result("impact.csv")).round(4).to_csv(RES_PRESENT / "dash_impact.csv", index=False)
pd.read_csv(result("confounding.csv")).round(6).to_csv(RES_PRESENT / "dash_confounding.csv", index=False)
pd.read_csv(result("power.csv")).round(4).to_csv(RES_PRESENT / "dash_power.csv", index=False)
print(len(list(RES_PRESENT.glob("dash_*.csv"))), "CSV dashboard")
