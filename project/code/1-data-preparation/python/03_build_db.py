"""Membuat rca.duckdb dari data bersih dan menguji bahwa database menolak data salah (constraint)."""
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import CLEAN_DIR, DB_PATH, RAW_DIR, RES_PREP, SQL_PREP  # noqa: E402

DB_PATH.unlink(missing_ok=True)
con = duckdb.connect(str(DB_PATH))
con.execute((SQL_PREP / "01_schema.sql").read_text(encoding="utf-8"))
con.execute(f"INSERT INTO dim_lot SELECT lot_id, supplier, CAST(receive_date AS DATE) FROM read_csv('{(RAW_DIR / 'dim_lot.csv').as_posix()}', header=true)")
con.execute(f"INSERT INTO dim_operator SELECT operator_id, CAST(hire_date AS DATE), primary_shift FROM read_csv('{(RAW_DIR / 'dim_operator.csv').as_posix()}', header=true)")
con.execute(f"""INSERT INTO unit_result
    SELECT unit_id, CAST(inspect_date AS DATE), model, shift, operator_id, lot_id, result, defect_code
    FROM read_csv('{(CLEAN_DIR / 'unit_result_clean.csv').as_posix()}', header=true, all_varchar=true) ORDER BY unit_id""")

counts = {t: con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("unit_result", "dim_lot", "dim_operator", "test_results")}
pd.DataFrame([dict(table=t, rows=n) for t, n in counts.items()]).to_csv(RES_PREP / "table_rows.csv", index=False)

# uji constraint: setiap baris salah harus ditolak
bad = {
    "hasil bukan OK atau NG": "INSERT INTO unit_result VALUES ('U9','2026-03-02','9W','Shift 1','OP01','LA01','LULUS',NULL)",
    "model tidak dikenal": "INSERT INTO unit_result VALUES ('U9','2026-03-02','7W','Shift 1','OP01','LA01','OK',NULL)",
    "shift tidak dikenal": "INSERT INTO unit_result VALUES ('U9','2026-03-02','9W','Shift 3','OP01','LA01','OK',NULL)",
    "unit_id ganda": "INSERT INTO unit_result SELECT * FROM unit_result LIMIT 1",
    "operator tidak ada di dim_operator": "INSERT INTO unit_result VALUES ('U9','2026-03-02','9W','Shift 1','OP99','LA01','OK',NULL)",
    "lot tidak ada di dim_lot": "INSERT INTO unit_result VALUES ('U9','2026-03-02','9W','Shift 1','OP01','LX99','OK',NULL)",
    "NG tanpa defect_code": "INSERT INTO unit_result VALUES ('U9','2026-03-02','9W','Shift 1','OP01','LA01','NG',NULL)",
    "OK dengan defect_code": "INSERT INTO unit_result VALUES ('U9','2026-03-02','9W','Shift 1','OP01','LA01','OK','SOLDER')",
}
tests = []
for name, sql in bad.items():
    try:
        con.execute(sql)
        tests.append(dict(test=name, outcome="diterima"))
        con.execute("DELETE FROM unit_result WHERE unit_id = 'U9'")
    except duckdb.Error:
        tests.append(dict(test=name, outcome="ditolak"))
pd.DataFrame(tests).to_csv(RES_PREP / "constraint_tests.csv", index=False)
assert all(t["outcome"] == "ditolak" for t in tests), tests
assert con.execute("SELECT count(*) FROM unit_result").fetchone()[0] == counts["unit_result"]
con.close()
print(counts, "| semua", len(tests), "uji constraint ditolak")
