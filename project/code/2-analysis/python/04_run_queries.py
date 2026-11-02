"""Menjalankan query SQL pada rca.duckdb dan menyimpan hasilnya sebagai CSV (Q1, Q3-Q6)."""
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import DB_PATH, RES_ANALYSIS, SQL_ANALYSIS  # noqa: E402

con = duckdb.connect(str(DB_PATH), read_only=True)
for sql, out in (("02_factor_rates.sql", "factor_rates.csv"), ("03_pareto.sql", "pareto.csv")):
    df = con.execute((SQL_ANALYSIS / sql).read_text(encoding="utf-8")).df()
    for c in df.select_dtypes("float").columns:
        df[c] = df[c].round(10)
    df.to_csv(RES_ANALYSIS / out, index=False)
    print(out, len(df), "baris")
con.close()
