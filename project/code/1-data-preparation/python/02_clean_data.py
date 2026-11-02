"""Membersihkan unit_result.csv. Setiap keputusan dicatat (Q13) dan dicocokkan dengan ground_truth_dirty.csv.

Aturan (urutan eksekusi):
  R1 baris ganda       : baris identik dengan unit_id yang sama -> sisakan satu
  R2 hasil tidak baku  : 'ok', 'PASS', 'OK ' -> OK; 'ng', 'FAIL', 'NG ' -> NG (nilai diperbaiki)
  R3 operator kosong   : baris dipertahankan, operator_id dikosongkan; dikeluarkan hanya dari uji per operator dan regresi
  R4 lot tidak dikenal : lot_id yang tidak ada di dim_lot (LX99) -> lot dan supplier dikosongkan; dikeluarkan hanya dari uji per lot/supplier dan regresi
  R5 konsistensi       : OK tanpa defect_code, NG dengan defect_code, tanggal dalam periode, shift dan model valid (hanya diperiksa, tidak ada perubahan)
Hasil: data/clean/unit_result_clean.csv (tidak di-commit), results/1-data-preparation/{cleaning_log,data_quality_summary}.csv, docs/cleaning_log.md
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import CLEAN_DIR, DOCS_DIR, GROUND_TRUTH_DIRTY, RAW_DIR, RES_PREP  # noqa: E402

raw = pd.read_csv(RAW_DIR / "unit_result.csv", dtype=str, keep_default_na=False, na_values=[""])
lots = pd.read_csv(RAW_DIR / "dim_lot.csv")
inj = pd.read_csv(GROUND_TRUTH_DIRTY).groupby("dirty_type").unit_id.apply(set).to_dict()
n_raw = len(raw)

log = []
# R1
dup_mask = raw.duplicated(keep="first")
log.append(dict(rule="R1", problem="Baris ganda (unit_id sama)", found_ids=set(raw[dup_mask].unit_id), rows_found=int(dup_mask.sum()),
                rows_dropped=int(dup_mask.sum()), rows_fixed=0, decision="Baris kedua dibuang, satu baris per unit dipertahankan"))
df = raw[~dup_mask].copy().reset_index(drop=True)
# R2
variant = ~df.result.isin(["OK", "NG"])
fix = {"ok": "OK", "PASS": "OK", "OK ": "OK", "ng": "NG", "FAIL": "NG", "NG ": "NG"}
assert set(df[variant].result) <= set(fix), set(df[variant].result)
log.append(dict(rule="R2", problem="Hasil tidak baku (ok, PASS, ng, FAIL, spasi)", found_ids=set(df[variant].unit_id), rows_found=int(variant.sum()),
                rows_dropped=0, rows_fixed=int(variant.sum()), decision="Dibakukan menjadi OK atau NG"))
df.loc[variant, "result"] = df.loc[variant, "result"].map(fix)
# R3
blank = df.operator_id.isna()
log.append(dict(rule="R3", problem="operator_id kosong", found_ids=set(df[blank].unit_id), rows_found=int(blank.sum()),
                rows_dropped=0, rows_fixed=0, decision="Baris dipertahankan; dikeluarkan hanya dari uji per operator dan regresi"))
# R4
unk = ~df.lot_id.isin(lots.lot_id)
log.append(dict(rule="R4", problem="lot_id tidak dikenal (LX99)", found_ids=set(df[unk].unit_id), rows_found=int(unk.sum()),
                rows_dropped=0, rows_fixed=0, decision="Baris dipertahankan; lot dan supplier dikosongkan, dikeluarkan hanya dari uji per lot/supplier dan regresi"))
df.loc[unk, "lot_id"] = pd.NA
# R5 pemeriksaan konsistensi (tidak mengubah data)
d = pd.to_datetime(df.inspect_date)
checks = {"OK tanpa defect_code": int(((df.result == "OK") & df.defect_code.notna()).sum()),
          "NG dengan defect_code": int(((df.result == "NG") & df.defect_code.isna()).sum()),
          "tanggal di luar periode": int(((d < "2026-03-02") | (d > "2026-08-31")).sum()),
          "shift tidak valid": int((~df["shift"].isin(["Shift 1", "Shift 2"])).sum()),
          "model tidak valid": int((~df.model.isin(["5W", "9W", "12W"])).sum()),
          "unit_id ganda setelah R1": int(df.unit_id.duplicated().sum())}
violations = sum(v for k, v in checks.items() if k != "NG dengan defect_code")
assert violations == 0 and checks["NG dengan defect_code"] == 0, checks
log.append(dict(rule="R5", problem="Pemeriksaan konsistensi (6 aturan)", found_ids=set(), rows_found=0, rows_dropped=0, rows_fixed=0,
                decision="Tidak ada pelanggaran; data tidak diubah"))

# pembuktian: hasil temuan = yang ditanam generator
planted = {"R1": inj["duplicate_row"], "R2": inj["result_variant"], "R3": inj["blank_operator"], "R4": inj["unknown_lot"]}
rows = []
for r in log:
    pl = planted.get(r["rule"])
    rows.append(dict(rule=r["rule"], problem=r["problem"], rows_found=r["rows_found"], rows_planted=len(pl) if pl is not None else 0,
                     match=(r["found_ids"] == pl) if pl is not None else True, rows_dropped=r["rows_dropped"], rows_fixed=r["rows_fixed"], decision=r["decision"]))
clog = pd.DataFrame(rows)
assert clog.match.all(), clog
clog.drop(columns="match").assign(match_ground_truth=clog.match.map({True: "ya"}).fillna("tidak")).to_csv(RES_PREP / "cleaning_log.csv", index=False)

df["result"] = df.result.astype(str)
df.to_csv(CLEAN_DIR / "unit_result_clean.csv", index=False)
n_clean = len(df)
dq = pd.DataFrame([dict(table="unit_result", raw_rows=n_raw, clean_rows=n_clean, bad_rows=int(clog.rows_found.sum()),
                        bad_pct=round(clog.rows_found.sum() / n_raw * 100, 4), rows_without_operator=int(blank.sum()), rows_without_lot=int(unk.sum()),
                        complete_case_rows=int((~blank & ~unk).sum()))])
dq.to_csv(RES_PREP / "data_quality_summary.csv", index=False)
pd.DataFrame([dict(check=k, violations=v) for k, v in checks.items()]).to_csv(RES_PREP / "consistency_checks.csv", index=False)

md = ["# Cleaning log", "", "Dibuat otomatis oleh `02_clean_data.py`. Temuan dicocokkan dengan `data/ground_truth_dirty.csv` (unit_id yang sama, bukan hanya jumlahnya).", "",
      f"Baris mentah {n_raw:,}, baris bersih (satu baris per unit) {n_clean:,}, baris bermasalah {int(clog.rows_found.sum()):,} ({dq.bad_pct[0]:.2f}%).".replace(",", "."), "",
      "| Aturan | Masalah | Ditemukan | Ditanam | Dibuang | Diperbaiki | Keputusan |", "|---|---|---|---|---|---|---|"]
md += [f"| {r.rule} | {r.problem} | {r.rows_found} | {r.rows_planted} | {r.rows_dropped} | {r.rows_fixed} | {r.decision} |" for r in clog.itertuples()]
md += ["", f"Pemeriksaan konsistensi R5: {', '.join(f'{k} = {v}' for k, v in checks.items())}."]
(DOCS_DIR / "cleaning_log.md").write_text("\n".join(md) + "\n", encoding="utf-8")
print(f"mentah {n_raw}, bersih {n_clean}, bermasalah {int(clog.rows_found.sum())}; tanpa operator {int(blank.sum())}, tanpa lot {int(unk.sum())}")
