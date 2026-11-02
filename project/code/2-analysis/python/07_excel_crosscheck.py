"""Cek silang dengan Excel (Q13/Q14): defect rate dan p-value chi-square per faktor dihitung ulang dengan rumus Excel
(COUNTIFS, CHISQ.TEST), lalu dihitung oleh LibreOffice (bukan Microsoft Excel) dan dibandingkan dengan hasil Python.
Keluaran: results/2-analysis/crosscheck.xlsx dan crosscheck_excel.csv
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pandas as pd
from openpyxl import Workbook, load_workbook

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import DB_PATH, RES_ANALYSIS, result  # noqa: E402
import duckdb  # noqa: E402

con = duckdb.connect(str(DB_PATH), read_only=True)
d = con.execute("SELECT unit_id, inspect_date::VARCHAR AS inspect_date, model, shift, operator_id, lot_id, supplier, experience, result FROM v_unit ORDER BY unit_id").df()
con.close()
ft = pd.read_csv(result("factor_tests.csv")).set_index("factor")
fr = pd.read_csv(result("factor_rates.csv"))

wb = Workbook()
ws = wb.active
ws.title = "data"
cols = list(d.columns)
ws.append(cols)
for row in d.itertuples(index=False):
    ws.append([None if pd.isna(v) else v for v in row])
N = len(d) + 1
col = {c: chr(65 + i) for i, c in enumerate(cols)}
rng = lambda c: f"data!${col[c]}$2:${col[c]}${N}"
checks = []          # (sheet, factor, python p-value, cell p, python rows)
for f, sheet in (("shift", "shift"), ("model", "model"), ("supplier", "supplier"), ("experience", "experience"), ("operator_id", "operator")):
    s = wb.create_sheet(sheet)
    lv = fr[fr.factor == f].level.tolist()
    s.append(["level", "n", "NG", "OK", "defect rate", "ekspektasi NG", "ekspektasi OK"])
    for i, l in enumerate(lv, 2):
        s.append([l, f'=COUNTIFS({rng(f)},A{i})', f'=COUNTIFS({rng(f)},A{i},{rng("result")},"NG")', f"=B{i}-C{i}", f"=C{i}/B{i}",
                  f"=B{i}*SUM($C$2:$C${len(lv) + 1})/SUM($B$2:$B${len(lv) + 1})", f"=B{i}-F{i}"])
    last = len(lv) + 1
    s[f"I1"], s[f"I2"] = "CHISQ.TEST", f"=_xlfn.CHISQ.TEST(C2:D{last},F2:G{last})"
    s["F1"].value = "ekspektasi NG"
    # ekspektasi untuk CHISQ.TEST harus berpasangan (NG, OK)
    checks.append((sheet, f, ft.loc[f, "p_value"], f"{sheet}!I2", lv))
wb.save(RES_ANALYSIS / "crosscheck.xlsx")

tmp = Path(tempfile.mkdtemp())
subprocess.run(["soffice", "--headless", "--convert-to", "xlsx", "--outdir", str(tmp), str(RES_ANALYSIS / "crosscheck.xlsx")], check=True, capture_output=True, timeout=280)
wv = load_workbook(tmp / "crosscheck.xlsx", data_only=True)
rows = []
for sheet, f, p_py, cell, lv in checks:
    s = wv[sheet]
    p_x = s["I2"].value
    rows.append(dict(scope=f"{f}: p-value chi-square keseluruhan", python=float(p_py), excel=float(p_x), status="PASS" if abs(float(p_py) - float(p_x)) < 1e-9 else "FAIL"))
    for i, l in enumerate(lv, 2):
        n_x, ng_x = s[f"B{i}"].value, s[f"C{i}"].value
        r = fr[(fr.factor == f) & (fr.level == l)].iloc[0]
        rows.append(dict(scope=f"{f} = {l}: n dan NG", python=f"{r.n}/{r.ng}", excel=f"{int(n_x)}/{int(ng_x)}", status="PASS" if (int(n_x), int(ng_x)) == (r.n, r.ng) else "FAIL"))
        rate_x = float(s[f"E{i}"].value)
        rows.append(dict(scope=f"{f} = {l}: defect rate", python=float(r.ng / r.n), excel=rate_x, status="PASS" if abs(r.ng / r.n - rate_x) < 1e-12 else "FAIL"))
out = pd.DataFrame(rows)
out.to_csv(RES_ANALYSIS / "crosscheck_excel.csv", index=False, float_format="%.12g")
shutil.copy(tmp / "crosscheck.xlsx", RES_ANALYSIS / "crosscheck.xlsx")          # simpan versi yang sudah berisi nilai hasil hitung
assert (out.status == "PASS").all(), out[out.status != "PASS"]
print(len(out), "pemeriksaan Excel, semua PASS")
