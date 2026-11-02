"""Cek silang SQL vs pandas (Q13/Q14): hitung ulang defect rate per level dan Pareto dari CSV bersih."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import CLEAN_DIR, RAW_DIR, RES_ANALYSIS, STUDY_START, result  # noqa: E402

u = pd.read_csv(CLEAN_DIR / "unit_result_clean.csv")
lot, op = pd.read_csv(RAW_DIR / "dim_lot.csv"), pd.read_csv(RAW_DIR / "dim_operator.csv")
u = u.merge(lot[["lot_id", "supplier"]], on="lot_id", how="left").merge(op[["operator_id", "hire_date"]], on="operator_id", how="left")
u["experience"] = pd.Series(pd.NA, index=u.index, dtype="object")
u.loc[u.hire_date.notna(), "experience"] = (u.hire_date[u.hire_date.notna()] >= STUDY_START).map({True: "baru", False: "berpengalaman"})
u["ng"] = (u.result == "NG").astype(int)
sql = pd.read_csv(result("factor_rates.csv"))
rows = []
for f in ("shift", "operator_id", "lot_id", "supplier", "model", "experience"):
    g = u.dropna(subset=[f]).groupby(f).ng.agg(["size", "sum"]).reset_index().rename(columns={f: "level", "size": "n", "sum": "ng"})
    m = sql[sql.factor == f].merge(g, on="level", how="outer", suffixes=("_sql", "_pd"))
    for r in m.itertuples():
        ok = r.n_sql == r.n_pd and r.ng_sql == r.ng_pd
        rows.append(dict(check=f"{f} = {r.level}", sql_n=r.n_sql, pandas_n=r.n_pd, sql_ng=r.ng_sql, pandas_ng=r.ng_pd, status="PASS" if ok else "FAIL"))
par = pd.read_csv(result("pareto.csv"))
pp = u[u.ng == 1].defect_code.value_counts()
for r in par.itertuples():
    rows.append(dict(check=f"pareto {r.defect_code}", sql_n=r.ng, pandas_n=int(pp[r.defect_code]), sql_ng=r.ng, pandas_ng=int(pp[r.defect_code]),
                     status="PASS" if r.ng == pp[r.defect_code] else "FAIL"))
out = pd.DataFrame(rows)
out.to_csv(RES_ANALYSIS / "crosscheck.csv", index=False)
assert (out.status == "PASS").all(), out[out.status != "PASS"]
print(len(out), "pemeriksaan SQL vs pandas, semua PASS")
