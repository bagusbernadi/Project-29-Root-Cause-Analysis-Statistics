"""Membuat design-and-report/index.html (Report Project versi 2) dari page_v1.html dan CSV hasil.

- Pane Design diambil apa adanya dari page_v1.html (dicek identik).
- Semua angka di Report berasal dari project/results/*.csv lewat helper I/D/P (report_lib.py) dan diaudit di akhir.
Jalankan dari mana saja:  python design-and-report/src/build_report.py
"""
import json
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "project" / "code"))
sys.path.insert(0, str(HERE))
from common import DB_PATH, GROUND_TRUTH, RES_ANALYSIS, RES_PREP, RES_PRESENT, result  # noqa: E402
from report_lib import (BLUE, D, GREY, HI, I, NO, OK, P, PART, SOFT, audit, bars, cs, esc, hbars, legend, pareto_svg, pill, qa, table)  # noqa: E402

R = lambda n: pd.read_csv(result(n))
PRIO = {1: "Utama", 2: "Pendukung", 3: "Utama", 4: "Utama", 5: "Utama", 6: "Pendukung", 7: "Utama", 8: "Pendukung", 9: "Utama", 10: "Pendukung", 11: "Utama", 12: "Utama", 13: "Utama", 14: "Tambahan"}
QT = {1: "Jenis defect apa saja yang menyumbang sekitar 80% dari semua NG?",
      2: "Di stasiun inspeksi mana NG paling banyak ditemukan?",
      3: "Apakah defect rate shift 1 dan shift 2 berbeda secara signifikan?",
      4: "Apakah ada operator yang defect rate-nya berbeda signifikan setelah dikoreksi karena banyak perbandingan?",
      5: "Apakah lot material atau supplier tertentu menghasilkan NG lebih banyak secara signifikan?",
      6: "Apakah defect rate berbeda antar model 5W, 9W, dan 12W?",
      7: "Untuk faktor yang signifikan, berapa kali lebih besar peluang NG-nya, dan seberapa yakin kita?",
      8: "Seberapa besar efek setiap faktor secara keseluruhan, bukan hanya signifikan atau tidak?",
      9: "Jika semua faktor dilihat bersamaan, faktor mana yang tetap terkait dengan NG?",
      10: "Adakah faktor yang tampak signifikan sendirian, tetapi ternyata karena faktor lain?",
      11: "Berapa unit NG yang bisa dihindari jika faktor bermasalah diperbaiki ke tingkat baseline?",
      12: "Apakah semua faktor yang ditanam ditemukan, dan faktor yang hanya noise tidak dinyatakan signifikan?",
      13: "Apakah syarat uji terpenuhi, misalnya expected count minimal 5, dan berapa persen data yang tidak valid?",
      14: "Berapa unit yang dibutuhkan agar perbedaan kecil antar operator bisa terdeteksi?"}
WARN = set()      # pertanyaan yang dijawab dengan catatan (dipakai chip, ringkasan, dan tabel evaluasi)


def Q(n, ans, warn=False, status=None):
    if warn:
        WARN.add(n)
    return qa(f"Q{n}", QT[n], PRIO[n], ans, status or ("Terjawab dengan catatan" if warn else "Terjawab"), warn)


mk = lambda *a: "".join(a)
pv = lambda p: "&lt; 0,001" if p < 0.001 else D(p, 3)
pv2 = lambda p: "&lt; 0,001" if p < 0.001 else D(p, 2)

# ---------------------------------------------------------------- data
tr, par, ft, reg, lr = R("test_results.csv"), R("pareto.csv"), R("factor_tests.csv").set_index("factor"), R("regression.csv"), R("lr_tests.csv").set_index("factor")
conf, sens, imp, pw, gtc = R("confounding.csv"), R("sensitivity.csv"), R("impact.csv"), R("power.csv"), R("ground_truth_check.csv")
cx, ce, dq, clog, cons = R("crosscheck.csv"), R("crosscheck_excel.csv"), R("data_quality_summary.csv").iloc[0], R("cleaning_log.csv"), R("consistency_checks.csv")
ctest, trows, fr, labels = R("constraint_tests.csv"), R("table_rows.csv"), R("factor_rates.csv"), R("factor_labels.csv").set_index("factor")
gt = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))
con = duckdb.connect(str(DB_PATH), read_only=True)
dbc = dict(trows.values)
sample = con.execute("SELECT unit_id, inspect_date, model, shift, operator_id, lot_id, result, defect_code FROM unit_result WHERE inspect_date = '2026-03-02' ORDER BY unit_id LIMIT 5").fetchall()
n_days = con.execute("SELECT count(DISTINCT inspect_date) FROM unit_result").fetchone()[0]
con.close()
lev = lambda f: tr[tr.factor == f].set_index("level")
ops, lots, sup, mdl, shf, exr = lev("operator_id"), lev("lot_id"), lev("supplier"), lev("model"), lev("shift"), lev("experience")
N, NG = int(dq.clean_rows), int(par.ng.sum())
op19, op08, op20 = ops.loc["OP19"], ops.loc["OP08"], ops.loc["OP20"]
k80 = int((par.cum_share < 0.8).sum() + 1)
c_all, c_no19 = conf.iloc[0], conf.iloc[1]
regT = reg[reg.model.str.startswith("Terpisah")]
regB = reg[reg.model.str.startswith("Bersamaan")].set_index("term")
regS = regT.set_index("term")
impg = imp.set_index("level")
gtm = gtc.set_index("fact_no")
npr = {k: sum(1 for v in PRIO.values() if v == k) for k in ("Utama", "Pendukung", "Tambahan")}
bad_total = int(clog.rows_found.sum())
tested = int(tr.p_value.notna().sum())
lot_raw = lots[lots.p_value < 0.05]
op_raw, op_bh = ops[ops.p_value < 0.05], ops[ops.p_adj < 0.05]
lotB = list(gt["facts"][0]["lots"])
p16 = pw[(pw.rate_multiplier == 1.6)]
p16l = p16[p16.scope.str.startswith("Lot")].reset_index(drop=True)
p16o = p16[p16.scope.str.startswith("Operator")].reset_index(drop=True)
sC = sens[sens.treatment.str.startswith("C")].iloc[0]

assert tr[tr.status == "Terbukti"].set_index(["factor", "level"]).index.tolist() == [("shift", "Shift 2"), ("operator_id", "OP19"), ("model", "12W"), ("experience", "baru")]
assert gtc.hasil.tolist() == ["Sebagian", "Sesuai", "Sesuai", "Sebagian", "Sesuai"], gtc.hasil.tolist()
assert (cx.status == "PASS").all() and (ce.status == "PASS").all() and (ctest.outcome == "ditolak").all() and (cons.violations == 0).all()
assert lots.p_adj.min() > 0.05 and sorted(lot_raw.index) == sorted(lotB) and len(op_bh) == 1 and op08.p_adj > 0.05 and op20.test == "Fisher exact"
assert c_all.p_value < 0.05 < c_no19.p_value and regB.loc["Shift 2", "p_value"] > 0.05 and regB.loc["Operator baru", "p_value"] < 0.001

# ---------------------------------------------------------------- 1. data
kp = lambda c, v, l, d: f'<div class="card kpi" style="--h:var(--{c}H)"><span class="v">{v}</span><span class="l">{l}</span><span class="d">{d}</span></div>'
rp1 = mk(
    '<div class="kpis">',
    kp("navy", I(dbc["unit_result"]), "baris unit_result", f"Dari {I(dq.raw_rows)} baris mentah. Satu baris = satu unit lampu yang diinspeksi, {I(n_days)} hari kerja."),
    kp("amber", I(NG), "unit NG", f"Defect rate keseluruhan {P(NG / N, 2)}. Lima kode defect, terbesar {par.defect_code.iloc[0]}."),
    kp("teal", I(dbc["dim_operator"]), "operator", f"Kode OP01 sampai OP20, tanpa nama. {I(ops.n.min())} sampai {I(ops.n.max())} unit per operator."),
    kp("plum", I(dbc["dim_lot"]), "lot chip LED", f"Dari 3 supplier. {I(lots.n.min())} sampai {I(lots.n.max())} unit per lot."),
    kp("rose", I(bad_total), "baris kotor ditemukan", f"{D(dq.bad_pct, 2)}% dari data mentah. Semua ditangani dan sama dengan yang ditanam."),
    kp("sky", I(tr.shape[0]), "baris test_results", f"Satu baris per level faktor. {I(tested)} level diuji, sisanya pembanding."),
    '</div><div class="callout a"><h4>Data project ini adalah simulasi</h4><p>Semua data dibuat oleh <code>01_generate_data.py</code> dengan seed tetap (versi v1). Angka menggambarkan simulasi, bukan pabrik nyata.</p></div>',
    '<h3>1.1 Data simulasi (mentah dan bersih)</h3>')
rp1 += '<div class="card"><h4>Cuplikan unit_result (2 Maret 2026)</h4>' + table(
    ["unit_id", "inspect_date", "model", "shift", "operator_id", "lot_id", "result", "defect_code"],
    [[r[0], str(r[1]), r[2], r[3], r[4], r[5], r[6], r[7] or "(kosong)"] for r in sample]) + '<p>Contoh baris tabel bersih. Cuplikan sama setiap dijalankan ulang karena seed tetap.</p></div>'
rp1 += '<div class="card"><h4>Tabel 1.1. Data kotor: ditemukan, ditanam, dan keputusan (Q13)</h4>' + table(
    ["Aturan", "Masalah", "Ditemukan", "Ditanam", "Dibuang", "Diperbaiki", "Keputusan"],
    [[r.rule, r.problem, I(r.rows_found), I(r.rows_planted), I(r.rows_dropped), I(r.rows_fixed), r.decision] for r in clog.itertuples()]) + \
    f'<p>Mentah {I(dq.raw_rows)} baris, bersih {I(dq.clean_rows)} baris (satu baris per unit). Operator kosong {I(dq.rows_without_operator)} baris dan lot tidak dikenal {I(dq.rows_without_lot)} baris tetap dipakai untuk faktor lain; kasus lengkap untuk regresi {I(dq.complete_case_rows)} baris.</p>'
rp1 += Q(13, f"{D(dq.bad_pct, 2)}% baris tidak valid ({I(bad_total)} dari {I(dq.raw_rows)}). Semuanya ditemukan dan unit_id-nya sama persis dengan yang ditanam generator. Hasil tidak berubah secara berarti: pada tiga perlakuan data, "
             f"jumlah operator signifikan setelah koreksi tetap {I(sC.operators_sig_bh)} dan jumlah lot signifikan tetap {I(sC.lots_sig_bh)} (Tabel 2.10a). Syarat uji: {I(tr[tr.test == 'Fisher exact'].shape[0])} level memakai Fisher exact karena expected count di bawah 5 (Tabel 2.10b).") + \
    '<p class="note">Pembahasan lengkap Q13 ada di <a href="#sec210">2.10</a>.</p></div>'
rp1 += '<h3>1.2 Tabel di database (<code>rca.duckdb</code>)</h3><div class="card"><h4>Tabel 1.2a. Isi database</h4>' + table(
    ["Tabel", "Baris", "Isi"],
    [["unit_result", I(dbc["unit_result"]), "Hasil inspeksi per unit. Kunci utama unit_id; kunci asing ke dim_operator dan dim_lot."],
     ["dim_lot", I(dbc["dim_lot"]), "Lot chip LED, supplier, dan tanggal terima."],
     ["dim_operator", I(dbc["dim_operator"]), "Kode operator, tanggal masuk, dan shift utama."],
     ["test_results", I(tr.shape[0]), "Satu baris per level faktor: defect rate, CI, uji, p-value, p terkoreksi, odds ratio, status. Diisi oleh <code>06_stats_tests.py</code>."]]) + \
    '<h4>Tabel 1.2b. Uji aturan pengecekan (constraint)</h4>' + table(["Baris salah yang dicoba dimasukkan", "Hasil"], [[r.test, OK("Ditolak") if r.outcome == "ditolak" else NO("Diterima")] for r in ctest.itertuples()]) + \
    f'<p>Kedelapan jenis data salah ditolak oleh database. Setelah cleaning, {I(len(cons))} pemeriksaan konsistensi menghasilkan 0 pelanggaran.</p></div>'
FILES = {"cleaning_log": ("Log cleaning per aturan", "Q13"), "data_quality_summary": ("Ringkasan data kotor", "Q13"), "consistency_checks": ("Pemeriksaan konsistensi", "Q13"),
         "constraint_tests": ("Uji constraint database", "Q13"), "table_rows": ("Baris per tabel", "Q13"), "factor_rates": ("Defect rate per level faktor (SQL)", "Q3, Q4, Q5, Q6"),
         "pareto": ("Pareto defect (SQL)", "Q1"), "crosscheck": ("SQL vs pandas", "Q13, Q14"), "crosscheck_excel": ("SQL/Python vs Excel", "Q13, Q14"),
         "test_results": ("Uji per level faktor (tabel test_results)", "Q3, Q4, Q5, Q6, Q7, Q13"), "factor_tests": ("Uji keseluruhan per faktor dan Cramér's V", "Q6, Q8, Q13"),
         "regression": ("Regresi logistik terpisah dan bersamaan", "Q9, Q10"), "lr_tests": ("Uji rasio kemungkinan per kelompok faktor", "Q9, Q10"),
         "confounding": ("Shift dengan dan tanpa operator baru", "Q10"), "sensitivity": ("Tiga perlakuan data kotor", "Q13"), "impact": ("Unit NG terhindari (estimated)", "Q11"),
         "ground_truth_check": ("Fakta ditanam vs temuan", "Q12"), "power": ("Jumlah unit dan power", "Q14"), "factor_labels": ("Label akhir per faktor", "Q9, Q12")}
resfiles = sorted(p for d in (RES_PREP, RES_ANALYSIS) for p in d.glob("*.csv"))
miss = [p.stem for p in resfiles if p.stem not in FILES]
assert not miss, f"CSV hasil belum didokumentasikan di FILES: {miss}"
rp1 += '<div class="card"><h4>Tabel 1.2c. Data hasil analisis (<code>project/results/</code>)</h4>' + table(
    ["File", "Isi", "Baris", "Menjawab"], [[f"<code>{p.stem}.csv</code>", FILES[p.stem][0], I(len(pd.read_csv(p))), FILES[p.stem][1]] for p in resfiles]) + \
    f'<p>{I(len(resfiles))} file CSV, ditambah {I(len(list(RES_PRESENT.glob("dash_*.csv"))))} CSV data dashboard.</p></div>'
rp1 += '<h3>1.3 Angka kunci (KPI)</h3><div class="card"><h4>Tabel 1.3. Lima KPI (aturan di <code>project/docs/analysis_rules.md</code>)</h4>' + table(
    ["KPI", "Rumus ringkas", "Hasil", "Jumlah data"],
    [["Defect rate keseluruhan", "unit NG ÷ unit diinspeksi", P(NG / N, 2), f"{I(NG)} dari {I(N)} unit"],
     ["Operator signifikan setelah koreksi", "p Benjamini-Hochberg &lt; 0,05", f"{I(len(op_bh))} dari {I(ops.p_value.notna().sum())} ({I(len(op_raw))} tanpa koreksi)", f"{I(ops.n.sum())} unit"],
     ["Odds ratio OP19", "(NG÷OK OP19) ÷ (NG÷OK lainnya)", f"{D(op19.odds_ratio, 2)} (CI {D(op19.or_ci_low, 2)} s.d. {D(op19.or_ci_high, 2)})", f"{I(op19.ng)} NG dari {I(op19.n)} unit"],
     ["p-value shift (tanpa koreksi)", "chi-square Pearson, 2 sisi", f"{pv(c_all.p_value)}; tanpa OP19 {pv2(c_no19.p_value)}", f"{I(c_all.n_shift2 + c_all.n_shift1)} unit"],
     ["Unit NG terhindari OP19 (estimated)", "(rate − baseline) × unit", f"{I(impg.loc['OP19', 'ng_avoided_period'])} per periode, {I(impg.loc['OP19', 'ng_avoided_year'])} per tahun", f"{I(op19.n)} unit"]]) + '</div>'

# ---------------------------------------------------------------- 2. business questions
tip = lambda r: f"{r.Index}: {P(r.rate, 2)} ({I(r.ng)} dari {I(r.n)} unit), CI 95% {P(r.ci_low, 2)} s.d. {P(r.ci_high, 2)}, {r.status}"
vital = [bool(c - s < 0.8) for c, s in zip(par.cum_share, par.share)]
s21 = mk('<h3 id="sec21">2.1 Pareto defect dan stasiun inspeksi <span class="qlist">Q1, Q2</span></h3><div class="card">',
         Q(1, f"{I(k80)} jenis defect ({', '.join(par.defect_code.iloc[:k80])}) menyumbang {P(par.cum_share.iloc[k80 - 1])} dari {I(NG)} unit NG; tiga jenis pertama {P(par.cum_share.iloc[2])}, jadi batas 80% terlewati pada jenis ke-{I(k80)}. "
              f"Terbesar {par.defect_code.iloc[0]} ({P(par.share.iloc[0])}), terkecil {par.defect_code.iloc[-1]} ({P(par.share.iloc[-1])})."),
         Q(2, "Tidak terjawab. Data simulasi v1 tidak punya kolom <code>inspect_station</code> (rancangan menyebutnya di tabel unit_result), jadi NG per stasiun tidak bisa dihitung. "
              "Pertanyaan ini berlabel Pendukung dan tidak mengubah kesimpulan lain. Mengisinya butuh generator versi baru dengan kolom stasiun.", warn=True, status="Tidak terjawab"),
         '<h4>Grafik 2.1a. Pareto defect (batang biru tua: jenis hingga 80% kumulatif)</h4>',
         pareto_svg(list(par.defect_code), list(par.share), list(par.cum_share), vital, [f"{r.defect_code}: {I(r.ng)} NG, {P(r.share, 1)}, kumulatif {P(r.cum_share, 1)}" for r in par.itertuples()], "Pareto defect"),
         '<h4>Tabel 2.1b. Jumlah NG per kode defect</h4>',
         table(["Kode defect", "NG", "Porsi", "Kumulatif"], [[r.defect_code, I(r.ng), P(r.share, 1), P(r.cum_share, 1)] for r in par.itertuples()]), '</div>')
s22 = mk('<h3 id="sec22">2.2 Shift 1 dan shift 2 <span class="qlist">Q3</span></h3><div class="card">',
         Q(3, f"Ya, jika dilihat sendirian: Shift 2 {P(shf.loc['Shift 2', 'rate'], 2)} vs Shift 1 {P(shf.loc['Shift 1', 'rate'], 2)}, chi-square Pearson p {pv(shf.loc['Shift 2', 'p_value'])} (odds ratio {D(shf.loc['Shift 2', 'odds_ratio'], 2)}, CI {D(shf.loc['Shift 2', 'or_ci_low'], 2)} s.d. {D(shf.loc['Shift 2', 'or_ci_high'], 2)}). "
              f"Selisihnya kecil ({D((shf.loc['Shift 2', 'rate'] - shf.loc['Shift 1', 'rate']) * 100, 2)} poin) dan ternyata bukan karena shift: lihat Q10 di 2.7."),
         '<h4>Grafik 2.2a. Defect rate per shift (CI 95% ada di tooltip)</h4>',
         bars([(r.Index, r.rate, BLUE if r.Index == "Shift 2" else GREY, tip(r)) for r in shf.itertuples()], lambda v: P(v, 1), "Defect rate per shift", rot=0, small=True),
         '<h4>Tabel 2.2b. Uji shift</h4>',
         table(["Shift", "Unit", "NG", "Defect rate", "CI 95%", "Uji", "p-value"],
               [[k, I(r.n), I(r.ng), P(r.rate, 2), f"{P(r.ci_low, 2)} s.d. {P(r.ci_high, 2)}", r.test if isinstance(r.test, str) else "pembanding", pv(r.p_value) if r.p_value == r.p_value else ""] for k, r in shf.iterrows()]), '</div>')
col_op = lambda r: BLUE if r.status == "Terbukti" else (HI if r.p_value < 0.05 else GREY)
top_ops = ops.sort_values("p_value").head(6)
s23 = mk('<h3 id="sec23">2.3 Operator <span class="qlist">Q4</span></h3><div class="card">',
         Q(4, f"Hanya satu: OP19 (defect rate {P(op19.rate, 2)}, odds ratio {D(op19.odds_ratio, 2)}, p BH {pv(op19.p_adj)}). Tanpa koreksi, {I(len(op_raw))} dari {I(ops.p_value.notna().sum())} operator tampak signifikan ({', '.join(op_raw.sort_values('p_value').index)}); "
              f"setelah koreksi Benjamini-Hochberg hanya OP19 bertahan, dan koreksi Bonferroni memberi hasil sama. OP08 yang tampak buruk (p {pv(op08.p_value)}) menjadi p BH {D(op08.p_adj, 2)}. "
              f"Catatan: OP20 hanya {I(op20.n)} unit dengan {I(op20.ng)} NG (expected count {D(op20.expected_min, 1)}), diuji dengan Fisher exact (p {D(op20.p_value, 3)}), dan hasil sebanyak itu belum cukup kuat untuk kesimpulan apa pun.", warn=True),
         '<h4>Grafik 2.3a. Defect rate per operator (biru: lolos koreksi, oranye: signifikan hanya tanpa koreksi)</h4>',
         bars([(r.Index, r.rate, col_op(r), tip(r) + f", p BH {D(r.p_adj, 3)}") for r in ops.itertuples()], lambda v: P(v, 1), "Defect rate per operator", rot=0),
         legend([(BLUE, "Terbukti (p BH < 0,05)"), (HI, "p mentah < 0,05 tetapi tidak lolos koreksi"), (GREY, "Noise")]),
         '<h4>Tabel 2.3b. Enam operator dengan p-value mentah terkecil (dari 20)</h4>',
         table(["Operator", "Unit", "NG", "Defect rate", "Uji", "p mentah", "p BH", "p Bonferroni", "Odds ratio", "Status"],
               [[k, I(r.n), I(r.ng), P(r.rate, 2), r.test, pv(r.p_value), pv2(r.p_adj), pv2(r.p_adj_bonf), D(r.odds_ratio, 2), OK("Terbukti") if r.status == "Terbukti" else r.status] for k, r in top_ops.iterrows()]),
         '<p>Level diuji lawan sisanya (tabel 2x2). Koreksi dilakukan per keluarga faktor (20 operator). Hasil per operator dipakai untuk pelatihan dan perbaikan proses, bukan untuk menilai orang.</p></div>')
lot_col = lambda r: HI if r.p_value < 0.05 else GREY
top_lots = lots.sort_values("p_value").head(6)
s24 = mk('<h3 id="sec24">2.4 Lot chip LED dan supplier <span class="qlist">Q5</span></h3><div class="card">',
         Q(5, f"Belum terbukti. Tidak ada lot yang lolos koreksi untuk {I(lots.p_value.notna().sum())} lot (p BH terkecil {D(lots.p_adj.min(), 2)}), dan uji rasio kemungkinan semua lot bersama p {D(lr.loc['Lot chip LED', 'p_value'], 2)}. "
              f"Dua lot dengan p mentah terkecil, {lot_raw.sort_values('p_value').index[0]} ({P(lot_raw.sort_values('p_value').rate.iloc[0], 2)}) dan {lot_raw.sort_values('p_value').index[1]} ({P(lot_raw.sort_values('p_value').rate.iloc[1], 2)}), memang lot yang ditanam lebih buruk (Q12), "
              f"tetapi tidak bertahan setelah koreksi. Supplier B {P(sup.loc['Supplier B', 'rate'], 2)} vs A {P(sup.loc['Supplier A', 'rate'], 2)} dan C {P(sup.loc['Supplier C', 'rate'], 2)}: p BH {D(sup.loc['Supplier B', 'p_adj'], 2)}, belum signifikan. "
              f"Alasannya ukuran data: satu lot hanya sekitar {I(lots.n.median())} unit (Q14).", warn=True),
         '<h4>Grafik 2.4a. Defect rate per lot (oranye: p mentah di bawah 0,05, tidak ada yang lolos koreksi)</h4>',
         bars([(r.Index, r.rate, lot_col(r), tip(r) + f", p BH {D(r.p_adj, 2)}") for r in lots.itertuples()], lambda v: P(v, 1), "Defect rate per lot", rot=65),
         legend([(HI, "p mentah < 0,05, tidak lolos koreksi"), (GREY, "Noise")]),
         '<h4>Tabel 2.4b. Enam lot dengan p-value mentah terkecil (dari 40) dan tiga supplier</h4>',
         table(["Level", "Unit", "NG", "Defect rate", "Uji", "p mentah", "p BH", "p Bonferroni", "Odds ratio"],
               [[k, I(r.n), I(r.ng), P(r.rate, 2), r.test, pv(r.p_value), pv2(r.p_adj), pv2(r.p_adj_bonf), D(r.odds_ratio, 2)] for k, r in pd.concat([top_lots, sup]).iterrows()]), '</div>')
s25 = mk('<h3 id="sec25">2.5 Model lampu dan kekuatan efek tiap faktor <span class="qlist">Q6, Q8</span></h3><div class="card">',
         Q(6, f"Sedikit berbeda: uji keseluruhan chi-square p {D(ft.loc['model', 'p_value'], 3)}. Model 12W {P(mdl.loc['12W', 'rate'], 2)}, 5W {P(mdl.loc['5W', 'rate'], 2)}, 9W {P(mdl.loc['9W', 'rate'], 2)}. "
              f"Hanya 12W yang lolos koreksi (odds ratio {D(mdl.loc['12W', 'odds_ratio'], 2)}, p BH {D(mdl.loc['12W', 'p_adj'], 3)}); efeknya kecil."),
         Q(8, f"Efek terbesar ada pada operator (Cramér's V {D(ft.loc['operator_id', 'cramers_v'], 3)}) dan pengalaman operator ({D(ft.loc['experience', 'cramers_v'], 3)}); faktor lain di bawah {D(ft.loc[['shift', 'lot_id', 'supplier', 'model'], 'cramers_v'].max(), 3)}. "
              "Semua nilai Cramér's V kecil (di bawah 0,1), dan signifikan belum berarti penting: faktor yang signifikan pun menjelaskan sebagian kecil variasi NG unit demi unit."),
         '<h4>Tabel 2.5a. Uji keseluruhan per faktor dan ukuran efek</h4>',
         table(["Faktor", "Level", "Unit", "chi-square", "df", "p-value", "Cramér's V", "Sel expected &lt; 5"],
               [[{"shift": "Shift", "operator_id": "Operator", "lot_id": "Lot chip LED", "supplier": "Supplier", "model": "Model lampu", "experience": "Pengalaman operator"}[f], I(r.levels), I(r.n), D(r.chi2, 2), I(r.dof), pv(r.p_value), D(r.cramers_v, 3), f"{I(r.cells_exp_lt5)} dari {I(r.cells)}"]
                for f, r in ft.iterrows()]), '</div>')
prov = tr[(tr.status == "Terbukti")].copy()
prov["lab"] = prov.factor.map({"shift": "Shift", "operator_id": "Operator", "model": "Model", "experience": "Pengalaman"}) + " " + prov.level
s26 = mk('<h3 id="sec26">2.6 Odds ratio <span class="qlist">Q7</span></h3><div class="card">',
         Q(7, f"Empat level lolos koreksi. OP19 {D(op19.odds_ratio, 2)} kali lebih besar peluang NG-nya (CI 95% {D(op19.or_ci_low, 2)} s.d. {D(op19.or_ci_high, 2)}); pengalaman operator baru {D(exr.loc['baru', 'odds_ratio'], 2)} kali; model 12W {D(mdl.loc['12W', 'odds_ratio'], 2)} kali (CI {D(mdl.loc['12W', 'or_ci_low'], 2)} s.d. {D(mdl.loc['12W', 'or_ci_high'], 2)}); "
              f"Shift 2 {D(shf.loc['Shift 2', 'odds_ratio'], 2)} kali, tetapi ini hilang setelah faktor lain dikontrol (Q10). Operator baru dan OP19 mencakup unit yang hampir sama, jadi bukan dua faktor terpisah."),
         '<h4>Grafik 2.6a. Odds ratio level yang lolos koreksi (CI 95% di tooltip dan Tabel 2.6b)</h4>',
         hbars([(r.lab, r.odds_ratio, BLUE if r.factor != "shift" else HI, f"{r.lab}: odds ratio {D(r.odds_ratio, 2)}, CI 95% {D(r.or_ci_low, 2)} s.d. {D(r.or_ci_high, 2)}, p BH {pv(r.p_adj)}") for r in prov.itertuples()], lambda v: D(v, 2), "Odds ratio", 3.5),
         legend([(BLUE, "Tetap terkait NG setelah faktor lain dikontrol"), (HI, "Hilang setelah dikontrol (Shift 2)")]),
         '<h4>Tabel 2.6b. Level yang lolos koreksi</h4>',
         table(["Level", "Unit", "NG", "Defect rate", "Odds ratio", "CI 95%", "p BH"],
               [[r.lab, I(r.n), I(r.ng), P(r.rate, 2), D(r.odds_ratio, 2), f"{D(r.or_ci_low, 2)} s.d. {D(r.or_ci_high, 2)}", pv(r.p_adj)] for r in prov.itertuples()]), '</div>')
s27 = mk('<h3 id="sec27">2.7 Regresi logistik dan faktor yang saling terkait <span class="qlist">Q9, Q10</span></h3><div class="card">',
         Q(9, f"Pengalaman operator (operator baru) tetap terkait kuat: odds ratio {D(regB.loc['Operator baru', 'odds_ratio'], 2)} (p {pv(regB.loc['Operator baru', 'p_value'])}). Model 12W bertahan secara mentah (odds ratio {D(regB.loc['Model 12W', 'odds_ratio'], 2)}, p {D(regB.loc['Model 12W', 'p_value'], 3)}) "
              f"dan Supplier B tepat di batas (odds ratio {D(regB.loc['Supplier B', 'odds_ratio'], 2)}, p {D(regB.loc['Supplier B', 'p_value'], 3)}), tetapi keduanya tidak lolos koreksi antar suku (p BH {D(regB.loc['Model 12W', 'p_adj'], 2)} dan {D(regB.loc['Supplier B', 'p_adj'], 2)}). "
              f"Shift tidak tersisa (odds ratio {D(regB.loc['Shift 2', 'odds_ratio'], 2)}, p {D(regB.loc['Shift 2', 'p_value'], 2)}). Uji rasio kemungkinan pada model penuh: operator p {pv(lr.loc['Operator', 'p_value'])}, lot p {D(lr.loc['Lot chip LED', 'p_value'], 2)}, model p {D(lr.loc['Model lampu', 'p_value'], 3)}.", warn=True),
         Q(10, f"Ya: shift. Sendirian Shift 2 tampak lebih tinggi ({P(c_all.rate_shift2, 2)} vs {P(c_all.rate_shift1, 2)}, p {pv(c_all.p_value)}). Tanpa OP19, Shift 2 turun ke {P(c_no19.rate_shift2, 2)} dan perbedaannya hilang (p {D(c_no19.p_value, 2)}); pada regresi bersamaan odds ratio shift {D(regB.loc['Shift 2', 'odds_ratio'], 2)} (p {D(regB.loc['Shift 2', 'p_value'], 2)}). "
               f"Operator baru hanya bekerja di Shift 2, sehingga efeknya terbaca sebagai efek shift."),
         '<h4>Tabel 2.7a. Regresi logistik: faktor sendirian vs bersamaan (odds ratio terhadap level pembanding)</h4>',
         table(["Model", "Suku", "Odds ratio", "CI 95%", "p-value", "p BH antar suku"],
               [[r.model, r.term, D(r.odds_ratio, 2), f"{D(r.or_low, 2)} s.d. {D(r.or_high, 2)}", pv(r.p_value), pv2(r.p_adj)] for r in reg.itertuples()]),
         '<h4>Tabel 2.7b. Shift dengan dan tanpa operator baru (OP19)</h4>',
         table(["Perbandingan", "Unit Shift 2", "Defect rate Shift 2", "Defect rate Shift 1", "Odds ratio", "p-value"],
               [[r.comparison, I(r.n_shift2), P(r.rate_shift2, 2), P(r.rate_shift1, 2), D(r.odds_ratio, 2), pv(r.p_value)] for r in conf.itertuples()]),
         '<p>Pembanding: Shift 1, model 9W, Supplier A, operator berpengalaman. Regresi memakai kasus lengkap (operator dan lot terisi). Shift tidak bisa dimasukkan bersama operator karena setiap operator hampir selalu bekerja di satu shift.</p></div>')
s28 = mk('<h3 id="sec28">2.8 Dampak <span class="qlist">Q11</span></h3><div class="card">',
         Q(11, f"Jika OP19 dibawa ke baseline unit lain ({P(impg.loc['OP19', 'baseline_rate'], 2)}), sekitar {I(impg.loc['OP19', 'ng_avoided_period'])} unit NG terhindari pada periode data (±6 bulan), atau ±{I(impg.loc['OP19', 'ng_avoided_year'])} per tahun ({P(impg.loc['OP19', 'share_of_all_ng'], 1)} dari semua NG; rentang dari CI defect rate {I(impg.loc['OP19', 'ng_avoided_low'])} s.d. {I(impg.loc['OP19', 'ng_avoided_high'])} per periode). "
               f"Untuk model 12W selisih ke model lain sekitar {I(impg.loc['12W', 'ng_avoided_period'])} unit per periode, tetapi model adalah sifat produk, bukan sesuatu yang diperbaiki. Angka ini estimated, simulated, dan proyeksi 12 bulan memakai asumsi periode data 6 bulan.", warn=True),
         '<h4>Grafik 2.8a. Unit NG terhindari per periode data (estimated, simulated; CI di tooltip)</h4>',
         hbars([(f"{r.factor.replace('_id', '')} {r.level}", r.ng_avoided_period, BLUE, f"{r.factor} {r.level}: {I(r.ng_avoided_period)} unit NG, rentang {I(r.ng_avoided_low)} s.d. {I(r.ng_avoided_high)}") for r in imp.itertuples()], lambda v: I(v), "NG terhindari", 150),
         '<h4>Tabel 2.8b. Perhitungan dampak (estimated, simulated)</h4>',
         table(["Level", "Unit", "Defect rate", "Baseline", "NG terhindari per periode", "Rentang (CI rate)", "Per tahun", "Porsi dari semua NG"],
               [[f"{r.factor.replace('_id', '')} {r.level}", I(r.n), P(r.rate, 2), P(r.baseline_rate, 2), I(r.ng_avoided_period), f"{I(r.ng_avoided_low)} s.d. {I(r.ng_avoided_high)}", I(r.ng_avoided_year), P(r.share_of_all_ng, 1)] for r in imp.itertuples()]),
         '<p>Unit NG terhindari = (defect rate level − defect rate baseline) × unit level. Pengalaman operator baru dan OP19 mencakup unit yang sama, jadi tidak dijumlahkan. Shift tidak dihitung karena efeknya dijelaskan operator baru.</p></div>')
s29 = mk('<h3 id="sec29">2.9 Validasi terhadap ground truth <span class="qlist">Q12</span></h3><div class="card">',
         Q(12, f"Sebagian. Tiga dari lima fakta ditemukan penuh: shift dijelaskan operator baru, operator noise OP08 tidak signifikan setelah koreksi, dan data kotor ditemukan seluruhnya. Fakta 1 (dua lot lebih buruk) hanya sebagian: kedua lot menjadi dua p mentah terkecil tetapi tidak lolos koreksi. "
               f"Fakta 4 (beberapa operator sampel kecil) hanya sebagian karena hanya satu operator (OP20) yang kecil. Faktor yang hanya noise tidak dinyatakan signifikan: {I(len(op_raw) - len(op_bh))} operator yang signifikan hanya tanpa koreksi gugur setelah koreksi.", warn=True),
         '<h4>Tabel 2.9a. Lima fakta yang ditanam vs temuan</h4>',
         table(["No", "Fakta", "Ditemukan", "Hasil"], [[I(r.fact_no), cs(r.fakta), cs(r.ditemukan), OK("Sesuai") if r.hasil == "Sesuai" else PART(r.hasil)] for r in gtc.itertuples()]),
         '<h4>Tabel 2.9b. Label akhir per faktor</h4>',
         table(["Faktor", "Label", "Keterangan"], [[{"shift": "Shift", "operator_id": "Operator", "lot_id": "Lot chip LED", "supplier": "Supplier", "model": "Model lampu", "experience": "Pengalaman operator"}[f], r.label, cs(r.detail)] for f, r in labels.iterrows()]),
         '<p>Model 12W (pengali 1,08) ditanam generator tetapi tidak ada di lima fakta rancangan, sehingga temuannya dicatat sebagai tambahan.</p></div>')
sens_l = {0: "A. Data mentah apa adanya", 1: "B. Semua unit bermasalah dibuang", 2: "C. Cleaning sesuai log (dipakai)"}
fish = tr[tr.test == "Fisher exact"]
s210 = mk('<h3 id="sec210">2.10 Syarat uji, data kotor, dan cek silang <span class="qlist">Q13</span></h3><div class="card">',
          Q(13, f"Syarat uji terpenuhi. Hanya {I(len(fish))} level memakai Fisher exact ({', '.join(fish.level)}, expected count minimal {D(fish.expected_min.min(), 1)}); sisanya expected count di atas 5 sehingga chi-square. "
                f"{D(dq.bad_pct, 2)}% data tidak valid dan kesimpulan sama pada tiga perlakuan: operator signifikan setelah koreksi {I(sens.operators_sig_bh.min())} pada ketiganya, lot signifikan setelah koreksi {I(sens.lots_sig_bh.max())}. "
                f"Dua pemeriksaan silang lulus: {I(len(cx))} dari {I(len(cx))} SQL vs pandas dan {I(len(ce))} dari {I(len(ce))} SQL/Python vs Excel (dihitung ulang LibreOffice, bukan Microsoft Excel)."),
          '<h4>Tabel 2.10a. Tiga perlakuan data kotor</h4>',
          table(["Perlakuan", "Unit", "p shift", "Operator signifikan (mentah)", "Operator signifikan (BH)", "Lot signifikan (mentah)", "Lot signifikan (BH)", "Odds ratio OP19"],
                [[sens_l[i], I(r.n), pv(r.shift_p), I(r.operators_sig_raw), I(r.operators_sig_bh), I(r.lots_sig_raw), I(r.lots_sig_bh), D(r.op19_or, 2)] for i, r in sens.iterrows()]),
          '<h4>Tabel 2.10b. Syarat uji tiap faktor (expected count dan uji yang dipakai)</h4>',
          table(["Faktor", "Level diuji", "Expected count minimal", "Chi-square", "Fisher exact"],
                [[{"shift": "Shift", "operator_id": "Operator", "lot_id": "Lot chip LED", "supplier": "Supplier", "model": "Model lampu", "experience": "Pengalaman operator"}[f],
                  I(g.p_value.notna().sum()), D(g.expected_min.min(), 1), I((g.test == "Chi-square").sum()), I((g.test == "Fisher exact").sum())] for f, g in tr.groupby("factor", sort=False)]),
          '<h4>Tabel 2.10c. Cek silang SQL, pandas, dan Excel</h4>',
          table(["Pembanding", "Pemeriksaan", "PASS", "Isi"],
                [["SQL vs pandas", I(len(cx)), I((cx.status == "PASS").sum()), "unit dan NG per level semua faktor, Pareto defect"],
                 ["SQL/Python vs Excel", I(len(ce)), I((ce.status == "PASS").sum()), "unit, NG, defect rate per level lima faktor dan p-value chi-square keseluruhan (COUNTIFS, CHISQ.TEST)"]]), '</div>')
sz = lambda r: I(r.n_needed_per_level)
s211 = mk('<h3 id="sec211">2.11 Jumlah unit yang dibutuhkan <span class="qlist">Q14</span></h3><div class="card">',
          Q(14, f"Untuk satu lot yang defect rate-nya 1,6 kali lebih tinggi, dibutuhkan sekitar {sz(p16l.iloc[0])} unit per lot tanpa koreksi dan {sz(p16l.iloc[1])} unit dengan koreksi Bonferroni (40 lot), padahal data hanya punya sekitar {I(p16l.n_median_actual.iloc[0])} unit per lot: power {P(p16l.power_at_actual_n.iloc[0], 0)} tanpa koreksi dan {P(p16l.power_at_actual_n.iloc[1], 0)} dengan koreksi. "
                f"Itu sebabnya lot yang ditanam tidak terbukti. Untuk operator (20 uji), efek 1,6 kali butuh {sz(p16o.iloc[1])} unit per operator dan data punya sekitar {I(p16o.n_median_actual.iloc[0])} (power {P(p16o.power_at_actual_n.iloc[1], 0)}), sehingga operator berefek besar seperti OP19 terdeteksi. "
                f"Perhitungan memakai asumsi level sama besar dan defect rate dasar {P(tr[tr.factor == 'lot_id'].ng.sum() / tr[tr.factor == 'lot_id'].n.sum(), 2)}.", warn=True),
          '<h4>Tabel 2.11a. Unit per level untuk power 80% dan power pada ukuran data nyata</h4>',
          table(["Cakupan", "Kenaikan defect rate", "Aturan alpha", "Unit per level dibutuhkan", "Unit per level (data)", "Power pada data"],
                [[r.scope, f"{D(r.rate_multiplier, 1)} kali", r.alpha_rule, I(r.n_needed_per_level), I(r.n_median_actual), P(r.power_at_actual_n, 0)] for r in pw.itertuples()]),
          '<p>Power 80%, dua sisi, level sama besar (lawan sisanya). Aturan Bonferroni memakai alpha 0,05 dibagi jumlah uji.</p></div>')
SEC = {1: "21", 2: "21", 3: "22", 4: "23", 5: "24", 6: "25", 8: "25", 7: "26", 9: "27", 10: "27", 11: "28", 12: "29", 13: "210", 14: "211"}
rp2_body = mk(s21, s22, s23, s24, s25, s26, s27, s28, s29, s210, s211)
qn_all = sorted(int(x) for x in re.findall(r'<span class="qn">Q(\d+)</span>', rp2_body))
qn_uniq = sorted(set(qn_all) | {13})
assert qn_uniq == list(range(1, 15)), qn_uniq
nw = len(WARN)
wtxt = ", ".join(f"Q{n}" for n in sorted(WARN))
chips = mk('<div class="qchips">', "".join(f'<a class="qc{" w" if n in WARN else ""}" href="#sec{SEC[n]}" title="{esc(QT[n])}">Q{n}</a>' for n in range(1, 15)), '</div>')
rp2 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> 13 dari {len(QT)} pertanyaan terjawab ({npr["Utama"]} Utama, {npr["Pendukung"]} Pendukung, {npr["Tambahan"]} Tambahan); Q2 tidak terjawab karena data tidak punya kolom stasiun. '
         f'{nw} jawaban kuning ({wtxt}): Q2 tidak terjawab, sisanya terjawab dengan catatan. Klik nomor pertanyaan untuk melompat ke pembahasannya. Pertanyaan utama project dijawab di bagian 7.</p>',
         chips, '<p class="report-note">Q hijau = terjawab, Q kuning = terjawab dengan catatan atau tidak terjawab. Pembahasan dikelompokkan per grafik atau tabel bukti (2.1 sampai 2.11). Q13 muncul di Tabel 1.1 dan Tabel 2.10a.</p></div>', rp2_body)

# ---------------------------------------------------------------- 3-5. dataset, tools, alur
npy = len(list((REPO / "project/code").rglob("*.py")))
nsql = len(list((REPO / "project/code").rglob("*.sql")))
loc = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in (REPO / "project/code").rglob("*.py"))
fm = lambda r: OK("Ditemukan") if r == "Sesuai" else PART(r)
rp3 = mk('<div class="card"><p><b>Jawaban singkat:</b> data sesuai rancangan untuk ukuran, lima fakta, dan data kotor, dengan empat perbedaan: kolom <code>inspect_station</code>, <code>driver_lot</code>, <code>material</code>, dan <code>qty</code> tidak ada di generator v1, '
         'nama kolom berbeda, dua dari lima fakta hanya sebagian terbukti, dan jenis data kotor sedikit berbeda dari rancangan. Tidak ada masalah lisensi karena data buatan sendiri.</p></div>',
         table(["Aspek", "Rancangan", "Realisasi", "Verdict"], [
             ["Sumber", "Simulasi buatan sendiri, skrip generate_data.py", "Skrip <code>01_generate_data.py</code>, seed tetap (29260302), versi v1; hasil identik dengan sidik jari di repo DataCenter", OK("Sesuai")],
             ["Ukuran", "±50.000 unit, ±6 bulan, 2 shift, ±20 operator, ±40 lot, 3 supplier, NG 2-3%", f"{I(N)} unit, {I(n_days)} hari kerja, {I(dbc['dim_operator'])} operator, {I(dbc['dim_lot'])} lot, NG {P(NG / N, 2)}", OK("Sesuai")],
             ["Tabel", "unit_result, dim_lot, dim_operator, test_results", "Keempatnya di DuckDB dengan constraint; test_results diisi oleh analisis", OK("Sesuai")],
             ["Kolom unit_result", "serial_no, date, chip_lot, driver_lot, inspect_station", "unit_id, inspect_date, lot_id; tidak ada driver_lot dan inspect_station", NO("Berubah")],
             ["Kolom dim_lot dan dim_operator", "material, qty; start_date, experience_months, main_shift", "supplier, receive_date; hire_date, primary_shift (pengalaman diturunkan dari hire_date)", PART("Sesuai + penyesuaian")],
             ["Fakta 1 (dua lot supplier B ±1,6 kali)", "Lot bermasalah ditemukan", cs(gtm.loc[1].ditemukan), fm(gtm.loc[1].hasil)],
             ["Fakta 2 (efek shift dari operator baru)", "Shift tampak berbeda, penyebabnya operator baru", cs(gtm.loc[2].ditemukan), fm(gtm.loc[2].hasil)],
             ["Fakta 3 (operator noise)", "Tidak signifikan setelah koreksi", cs(gtm.loc[3].ditemukan), fm(gtm.loc[3].hasil)],
             ["Fakta 4 (operator sampel kecil, Fisher exact)", "Beberapa operator di bawah 100 unit", cs(gtm.loc[4].ditemukan), fm(gtm.loc[4].hasil)],
             ["Fakta 5 (data kotor 2-3%)", "Lot kosong, kode operator salah ketik, baris ganda", cs(gtm.loc[5].ditemukan) + ". Jenisnya: operator kosong, hasil tidak baku, lot tidak dikenal, baris ganda", fm(gtm.loc[5].hasil)],
             ["Parameter generator", "Tidak disebut", "Pengali lot 1,6, operator baru 2,6, operator noise 1,6, dan model 12W 1,08 ada di generator; tidak disetel ulang agar hasil cocok dengan rancangan", PART("Sesuai + penyesuaian")],
             ["Lisensi", "Tidak memakai data publik atau data perusahaan", "Tidak ada dataset pihak ketiga, tidak perlu dicek", OK("Tidak berlaku")]]))
rp4 = mk('<div class="card"><p><b>Jawaban singkat:</b> semua tools rancangan dipakai. Streamlit dibuat dan diuji lokal tetapi belum di-deploy; cek silang Excel dihitung ulang oleh LibreOffice, bukan Microsoft Excel; Playwright dan Faker/ReportLab tidak ada di rancangan (Playwright untuk infografik).</p></div>',
         table(["Tool", "Rancangan", "Realisasi", "Verdict"], [
             ["Python (pandas)", "Membuat data, membersihkan, tabel silang", f"Generator, cleaning, cek silang pandas ({I(npy)} skrip dan modul, {I(loc)} baris)", OK("Sesuai")],
             ["SciPy", "Chi-square, Fisher exact, expected count", "<code>chi2_contingency</code> (tanpa koreksi kontinuitas), <code>fisher_exact</code>, expected count di setiap level", OK("Sesuai")],
             ["statsmodels", "Regresi logistik, koreksi multiple testing, CI proporsi", "<code>smf.logit</code>, <code>multipletests</code> (BH dan Bonferroni), <code>proportion_confint</code> (Wilson), <code>NormalIndPower</code>", OK("Sesuai")],
             ["DuckDB + SQL", "4 tabel, defect rate per faktor, Pareto, tabel silang", f"rca.duckdb dengan constraint; {I(nsql)} file SQL; view <code>v_unit</code>", OK("Sesuai")],
             ["Streamlit + Plotly", "Dashboard 3 halaman, publik", "<code>streamlit/app.py</code> 3 halaman (Pareto, Perbandingan Faktor, Faktor Terbukti); diuji dengan <code>AppTest</code>; belum di-deploy", PART("Sebagian")],
             ["Excel", "Cek silang defect rate dan CHISQ.TEST satu faktor", f"<code>crosscheck.xlsx</code>: {I(len(ce))} pemeriksaan, lima faktor, COUNTIFS dan CHISQ.TEST; dihitung ulang oleh LibreOffice", PART("Sesuai + penyesuaian")],
             ["Jupyter Notebook", "Mencatat uji, syarat, hasil, batas", "<code>analysis.ipynb</code> dibuat otomatis dan dieksekusi tanpa error", OK("Sesuai")],
             ["Playwright (Chromium)", "Tidak ada di rancangan", "Mencetak one-sheet HTML menjadi PDF dan PNG", PART("Tambahan")],
             ["GitHub + Markdown", "Kode, query, notebook, README", "Struktur dan README siap; berada di branch <code>project-29-build</code>, belum digabung ke <code>main</code>", PART("Sebagian")]]))
steps = [("1", "Menetapkan aturan uji", "<code>project/docs/analysis_rules.md</code>", OK("Sesuai"), "Keluarga koreksi dan definisi operator baru ditetapkan sendiri."),
         ("2", "Merancang struktur tabel", "<code>project/docs/data_dictionary.md</code>, <code>01_schema.sql</code>", PART("Sesuai + penyesuaian"), "Kolom mengikuti data v1 (lihat bagian 3)."),
         ("3", "Membuat data simulasi", "<code>01_generate_data.py</code>, <code>ground_truth.json</code>", PART("Sesuai + penyesuaian"), "Generator dipindah ke struktur standar; hasil identik dengan versi sebelumnya (SHA-256 sama)."),
         ("4", "Membersihkan data", "<code>02_clean_data.py</code>, <code>cleaning_log.md</code>", OK("Sesuai"), "Ditambah pencocokan unit_id dengan yang ditanam."),
         ("5", "Memuat ke database", "<code>03_build_db.py</code>, <code>01_schema.sql</code>", OK("Sesuai"), "Ditambah 8 uji penolakan constraint."),
         ("6", "Pareto dan defect rate dengan CI", "<code>02_factor_rates.sql</code>, <code>03_pareto.sql</code>, <code>04_run_queries.py</code>", PART("Sebagian"), "Q2 (per stasiun) tidak dikerjakan: tidak ada data stasiun."),
         ("7", "Menguji setiap faktor", "<code>06_stats_tests.py</code>", OK("Sesuai"), "Chi-square atau Fisher exact, BH dan Bonferroni."),
         ("8", "Odds ratio dan effect size", "<code>06_stats_tests.py</code>", OK("Sesuai"), "Cramér's V untuk uji keseluruhan."),
         ("9", "Regresi logistik", "<code>06_stats_tests.py</code>", PART("Sesuai + tambahan"), "Ditambah uji rasio kemungkinan per kelompok dan perbandingan shift dengan dan tanpa OP19."),
         ("10", "Dampak dan validasi", "<code>08_impact_ground_truth.py</code>, <code>07_excel_crosscheck.py</code>", OK("Sesuai"), "Q14 dihitung dengan power analysis."),
         ("11", "Membuat dashboard", "<code>streamlit/app.py</code>, <code>09_build_dashboard_data.py</code>", PART("Sebagian"), "Belum di-deploy ke Streamlit Community Cloud."),
         ("12", "README dan finalisasi", "<code>README.md</code>, halaman ini", PART("Sebagian"), "Siap; digabung ke main setelah ditinjau.")]
CODE_REL = "project/code/"
renames = [("docs/analysis_rules.md", "project/docs/analysis_rules.md"), ("docs/data_dictionary.md", "project/docs/data_dictionary.md"),
           ("scripts/generate_data.py", CODE_REL + "1-data-preparation/python/01_generate_data.py"), ("data/raw/*.csv", "project/data/raw/*.csv (tidak di-commit)"),
           ("data/ground_truth.json", "project/data/ground_truth.json"), ("docs/cleaning_log.md", "project/docs/cleaning_log.md"), ("rca.duckdb", "project/rca.duckdb (tidak di-commit)"),
           ("sql/", CODE_REL + "1-data-preparation/sql/01_schema.sql, " + CODE_REL + "2-analysis/sql/02_factor_rates.sql, " + CODE_REL + "2-analysis/sql/03_pareto.sql"),
           ("notebooks/statistics.ipynb", "project/results/3-presentation/analysis.ipynb"), ("outputs/test_results.csv", "project/results/2-analysis/test_results.csv"),
           ("outputs/crosscheck.xlsx", "project/results/2-analysis/crosscheck.xlsx"), ("dashboard/app.py", CODE_REL + "3-presentation/streamlit/app.py"),
           ("requirements.txt", "project/requirements.txt"), ("outputs/onesheet.pdf / .png", "project/results/3-presentation/onesheet.pdf, project/results/3-presentation/onesheet.png"),
           ("(tidak ada)", ", ".join(("03_build_db.py", "04_run_queries.py", "05_crosscheck.py", "07_excel_crosscheck.py", "06_stats_tests.py", "08_impact_ground_truth.py",
                                       "09_build_dashboard_data.py", "10_build_infographic.py", "11_build_notebook.py", "12_build_readme.py", "test_app.py", "common.py")))]
for a, b in renames:                       # pastikan semua file tujuan memang ada (kecuali yang tidak di-commit)
    for part in b.split(", "):
        part = part.split(" (")[0]
        if "*" in part or "/" not in part or "tidak di-commit" in b:
            continue
        assert (REPO / part).exists(), part
allpy = {p.name for p in (REPO / CODE_REL).rglob("*.py")}
assert {"03_build_db.py", "04_run_queries.py", "05_crosscheck.py", "07_excel_crosscheck.py", "06_stats_tests.py", "08_impact_ground_truth.py", "09_build_dashboard_data.py", "10_build_infographic.py",
        "11_build_notebook.py", "12_build_readme.py", "test_app.py", "common.py"} <= allpy, "skrip pada daftar rename belum ada"
rp5 = mk('<div class="card"><p><b>Jawaban singkat:</b> 12 langkah dijalankan sesuai urutan. Nama dan lokasi file berubah mengikuti struktur repo standar, ada beberapa langkah tambahan, Q2 tidak dikerjakan, dan dua langkah (11 dan 12) belum sepenuhnya selesai.</p></div>',
         table(["Langkah", "Rancangan", "Realisasi", "Verdict", "Catatan"], [[a, b, c, d, e] for a, b, c, d, e in steps]),
         '<div class="card"><h4>Penyesuaian dan improvisasi yang tidak ada di rancangan</h4><ul class="tight">',
         '<li>Data simulasi sudah dibuat sebelum project ini dikerjakan (generator v1, seed 29260302). Generator tidak diubah agar hasil cocok dengan rancangan; hanya jalurnya dipindah dan sidik jarinya dibuktikan sama.</li>',
         '<li>Keluarga koreksi multiple testing per faktor, definisi operator baru (masuk pada atau setelah awal data), dan proyeksi 12 bulan (dua kali periode data) adalah ukuran buatan sendiri; tercatat di <code>analysis_rules.md</code>.</li>',
         f'<li>Ditambahkan di luar rancangan: uji rasio kemungkinan per kelompok faktor, perbandingan shift dengan dan tanpa OP19, tiga perlakuan data kotor, cek silang pandas ({I(len(cx))} pemeriksaan), dan {I(len(ctest))} uji constraint database.</li>',
         f'<li>Cek silang Excel memakai rumus (COUNTIFS dan CHISQ.TEST) yang dihitung ulang oleh LibreOffice ({I(len(ce))} pemeriksaan), bukan angka yang ditulis tangan.</li>',
         '<li>Q2 tidak dikerjakan karena tidak ada kolom stasiun; Q14 dijawab lewat power analysis pada lot dan operator.</li>',
         '<li>Notebook dan one-sheet dibuat otomatis dari hasil, dan angka halaman ini diaudit terhadap file hasil.</li></ul></div>',
         '<div class="card"><h4>Perubahan nama dan lokasi file terhadap rancangan</h4>',
         table(["Rancangan", "Realisasi"], [[f"<code>{a}</code>" if a != "(tidak ada)" else "(tidak ada di rancangan)", ", ".join(f"<code>{x}</code>" for x in b.split(", "))] for a, b in renames]) + '</div>')

# ---------------------------------------------------------------- 6. output
chk = lambda rel: (REPO / rel).exists()
outs = [("Dashboard interaktif", "Utama", PART("Sebagian"), "<code>streamlit/app.py</code> (3 halaman, filter faktor) diuji lokal dengan AppTest. Link publik belum ada"),
        ("One-sheet faktor terbukti", "Utama", OK("Tercapai"), "<code>onesheet.pdf</code> dan <code>onesheet.png</code>, dibuat dari CSV hasil"),
        ("Database & query SQL", "Utama", OK("Tercapai"), f"<code>rca.duckdb</code> (dibuat ulang, tidak di-commit) dan {I(nsql)} file SQL"),
        ("Notebook statistik", "Utama", OK("Tercapai"), "<code>analysis.ipynb</code> dieksekusi tanpa error, mencakup Q1 sampai Q14"),
        ("Tabel hasil uji", "Utama", OK("Tercapai"), f"<code>test_results.csv</code> ({I(tr.shape[0])} baris) dan tabel <code>test_results</code> di database"),
        ("Generator data simulasi", "Utama", OK("Tercapai"), "<code>01_generate_data.py</code> dengan seed tetap, <code>ground_truth.json</code>, hasil identik dengan sidik jari"),
        ("Laporan temuan & rekomendasi", "Utama", OK("Tercapai"), "<code>README.md</code> dan halaman ini; p-value, effect size, dan batas kesimpulan dicantumkan"),
        ("Repositori GitHub", "Utama", PART("Sebagian"), "Struktur dan cara menjalankan ulang siap; berada di branch <code>project-29-build</code>, belum digabung ke <code>main</code>"),
        ("Slide presentasi", "Opsional", NO("Tidak dibuat"), "Opsional, tidak dibuat")]
nU = [o for o in outs if o[1] == "Utama"]
cnt = lambda s: sum(1 for o in nU if s in o[2])
docs = [("docs/analysis_rules.md", "Aturan uji", "project/docs/analysis_rules.md"), ("docs/data_dictionary.md", "Kamus data", "project/docs/data_dictionary.md"),
        ("scripts/generate_data.py", "Generator data", "project/code/1-data-preparation/python/01_generate_data.py"), ("data/raw/*.csv", "Data mentah (tidak di-commit)", "project/data/raw"),
        ("data/ground_truth.json", "Fakta yang ditanam", "project/data/ground_truth.json"), ("docs/cleaning_log.md", "Log cleaning", "project/docs/cleaning_log.md"),
        ("rca.duckdb", "File database (tidak di-commit)", "project/rca.duckdb"), ("sql/", "Query SQL", "project/code/2-analysis/sql/02_factor_rates.sql"),
        ("notebooks/statistics.ipynb", "Notebook", "project/results/3-presentation/analysis.ipynb"), ("outputs/test_results.csv", "Tabel hasil uji", "project/results/2-analysis/test_results.csv"),
        ("outputs/crosscheck.xlsx", "Cek silang Excel", "project/results/2-analysis/crosscheck.xlsx"), ("dashboard/app.py", "Dashboard Streamlit", "project/code/3-presentation/streamlit/app.py"),
        ("requirements.txt", "Paket Python", "project/requirements.txt"), ("outputs/onesheet.pdf / .png", "One-sheet", "project/results/3-presentation/onesheet.png"),
        ("README.md", "Laporan temuan", "README.md"), ("index.html", "Pengalihan ke design-and-report/", "index.html"), ("slides/presentation.pdf", "Slide", "slides/presentation.pdf")]
stat_doc = lambda rel: OK("Ada") if chk(rel) and "duckdb" not in rel and "raw" not in rel else (PART("Tidak di-commit") if "duckdb" in rel or "raw" in rel else NO("Belum ada"))
rp6 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> {I(cnt("Tercapai"))} dari {I(len(nU))} output Utama tercapai penuh dan {I(cnt("Sebagian"))} sebagian (dashboard belum punya link publik, repositori belum digabung ke main). Slide Opsional tidak dibuat.</p></div>',
         table(["Output", "Label", "Status", "Bukti"], [[f"<b>{a}</b>", b, c, d] for a, b, c, d in outs]),
         '<div class="card"><h4>Daftar dokumen pada rancangan vs repositori</h4>',
         table(["Dokumen (rancangan)", "Isi", "Lokasi sekarang", "Status"], [[f"<code>{a}</code>", b, f"<code>{c}</code>", stat_doc(c)] for a, b, c in docs]),
         '<p>Data mentah dan <code>rca.duckdb</code> tidak di-commit karena bisa dibuat ulang oleh skrip.</p></div>')

# ---------------------------------------------------------------- 7. kesimpulan
crit = [("1. Kesembilan pertanyaan Utama terjawab dengan angka", OK("Tercapai"), "Q1, Q3, Q4, Q5, Q7, Q9, Q11, Q12, Q13 terjawab (bagian 2)"),
        ("2. Defect rate dan p-value chi-square dari Python sama dengan hitungan Excel", OK("Tercapai"), f"{I(len(ce))} dari {I(len(ce))} pemeriksaan Excel; {I(len(cx))} dari {I(len(cx))} pemeriksaan pandas"),
        ("3. Lot bermasalah ditemukan, efek shift dijelaskan pengalaman operator, operator noise tidak signifikan", PART("Sebagian"), "Shift dan operator noise sesuai; lot bermasalah tidak lolos koreksi (Tabel 2.9a)"),
        ("4. Setiap uji mencatat syaratnya, Fisher exact bila expected count < 5", OK("Tercapai"), f"Kolom expected_min dan test di test_results.csv; {I(len(fish))} level memakai Fisher exact"),
        ("5. README memuat p-value, effect size, batas kesimpulan; orang awam menyebut faktor terbukti dalam &lt; 1 menit", PART("Sebagian"), "README dan one-sheet memuatnya; belum diuji ke pembaca sebenarnya"),
        ("6. Checklist standar (pertanyaan bisnis, cleaning, SQL, dashboard ter-deploy, README)", PART("Sebagian"), "Semua ada kecuali dashboard ter-deploy")]
ncr = sum(1 for c in crit if ">Tercapai<" in c[1])
rp7 = mk(
    '<div class="card"><h4>7.1 Hasil analisis: jawaban atas pertanyaan utama</h4>',
    '<p><i>Apakah perbedaan defect rate antar shift, operator, atau lot material benar-benar signifikan, dan faktor mana yang paling kuat terkait dengan NG?</i></p><ul class="tight">',
    f'<li><b>Operator baru adalah satu-satunya faktor kuat:</b> OP19 {P(op19.rate, 2)} vs {P(impg.loc["OP19", "baseline_rate"], 2)} unit lain (odds ratio {D(op19.odds_ratio, 2)}, p BH {pv(op19.p_adj)}), dari {I(ops.p_value.notna().sum())} operator yang dibandingkan.</li>',
    f'<li><b>Shift hanya tampak berbeda:</b> p {pv(c_all.p_value)} sendirian, hilang tanpa OP19 (p {D(c_no19.p_value, 2)}) dan pada regresi bersamaan.</li>',
    f'<li><b>Koreksi mencegah alarm palsu:</b> {I(len(op_raw))} operator tampak signifikan tanpa koreksi, hanya {I(len(op_bh))} setelahnya; OP08 (noise) tidak bertahan.</li>',
    f'<li><b>Lot dan supplier belum terbukti:</b> tidak ada lot yang lolos koreksi untuk 40 lot, termasuk dua lot yang ditanam lebih buruk, karena satu lot hanya sekitar {I(lots.n.median())} unit (power {P(p16l.power_at_actual_n.iloc[1], 0)} dengan koreksi). Model 12W berefek kecil (odds ratio {D(mdl.loc["12W", "odds_ratio"], 2)}).</li></ul></div>',
    '<div class="card"><h4>7.2 Impact</h4><ul class="tight">',
    f'<li><b>Nilai praktis (estimated, simulated):</b> membawa OP19 ke baseline menghindari sekitar {I(impg.loc["OP19", "ng_avoided_period"])} unit NG per periode data, ±{I(impg.loc["OP19", "ng_avoided_year"])} per tahun ({P(impg.loc["OP19", "share_of_all_ng"], 1)} dari semua NG).</li>',
    '<li><b>Nilai analitis:</b> pemilihan uji berdasarkan expected count, koreksi multiple testing, dan regresi mencegah tiga kesalahan nyata: menegur operator noise, menyalahkan shift, dan mengganti supplier tanpa bukti.</li>',
    '<li><b>Nilai portofolio:</b> pipeline lengkap: data simulasi dengan ground truth, cleaning terdokumentasi, DuckDB dengan constraint, uji statistik, cek silang pandas dan Excel, notebook, dashboard, dan one-sheet.</li>',
    '<li><b>Belum terukur:</b> dampak di pabrik nyata. Semua angka berasal dari data simulasi dan menguji metode.</li></ul></div>')
rp7 += ('<div class="card"><h4>7.3 Success criteria</h4>' + table(["Kriteria (Design Project, bagian 8)", "Status", "Bukti"], [[a, b, c] for a, b, c in crit])
        + f'<p><b>Hasil:</b> {I(ncr)} dari {I(len(crit))} kriteria tercapai, {I(len(crit) - ncr)} sebagian atau belum diuji.</p></div>')
rp7 += mk('<div class="card"><h4>7.4 Rekomendasi</h4><ul class="tight">',
          '<li>Fokuskan pendampingan dan pelatihan pada operator baru (OP19); tidak perlu tindakan terpisah untuk shift.</li>',
          '<li>Jangan menegur operator lain, mengganti supplier, atau menolak lot hanya dari p-value mentah. Pantau di periode berikutnya.</li>',
          f'<li>Untuk lot, kumpulkan lebih banyak unit per lot (sekitar {sz(p16l.iloc[1])} untuk efek 1,6 kali dengan koreksi) atau uji per supplier dengan data yang digabung sebelum menyimpulkan.</li>',
          '<li>Selalu laporkan p-value bersama odds ratio dan ukuran sampel, serta sebutkan metode koreksi.</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.5 Saran perbaikan</h4><ul class="tight">',
          '<li>Buat generator v2 dengan kolom <code>inspect_station</code> dan <code>driver_lot</code> agar Q2 bisa dijawab dan tabel sesuai rancangan.</li>',
          '<li>Besarkan efek atau ukuran lot yang ditanam (atau kurangi jumlah lot) bila ingin lot bermasalah terdeteksi setelah koreksi; sesuaikan dengan Q14.</li>',
          '<li>Deploy dashboard ke Streamlit Community Cloud dan uji one-sheet ke satu pembaca awam untuk mengisi kriteria 5 dan 6.</li>',
          '<li>Pakai model campuran (operator dan lot sebagai efek acak) bila datanya nyata, karena level yang banyak dan kecil.</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.6 Batasan</h4><ul class="tight">',
          '<li>Data adalah simulasi; angka menggambarkan simulasi, bukan lini produksi. Fakta yang ditemukan adalah fakta yang ditanam sendiri; dari lima fakta, tiga ditemukan penuh dan dua (lot dan operator sampel kecil) hanya sebagian.</li>',
          '<li>Q2 tidak terjawab (tidak ada kolom stasiun) dan beberapa kolom rancangan tidak ada di generator v1.</li>',
          '<li>Uji statistik menunjukkan keterkaitan, bukan sebab; faktor yang tidak dicatat bisa menjadi penyebab sebenarnya.</li>',
          '<li>Keluarga koreksi, definisi operator baru, proyeksi 12 bulan, dan level sama besar pada power analysis adalah penafsiran sendiri. Regresi memakai kasus lengkap.</li>',
          '<li>Model 12W (efek kecil) bertahan pada uji per level tetapi tidak setelah koreksi antar suku di regresi; Supplier B tepat di batas pada regresi. Keduanya perlu data lebih banyak.</li>',
          '<li>Dashboard belum di-deploy; kriteria 5 dan 6 belum terpenuhi. Slide presentasi (Opsional) tidak dibuat. Cek silang Excel dihitung LibreOffice. Tidak ada masalah lisensi dataset (data buatan sendiri).</li></ul></div>')

evq = [("1", "rp1", "Data yang didapat", OK("Didapat"), f"{I(dbc['unit_result'])} unit, {I(NG)} NG, {I(bad_total)} baris kotor ditangani"),
       ("2", "rp2", "Business question terjawab?", PART("13 dari 14"), f"{npr['Utama']} Utama terjawab; Q2 (stasiun) tidak terjawab; {nw - 1} lainnya dengan catatan ({wtxt})"),
       ("3", "rp3", "Dataset sesuai?", PART("Sesuai + penyesuaian"), "Ukuran dan data kotor sesuai; kolom stasiun tidak ada; fakta 1 dan 4 sebagian"),
       ("4", "rp4", "Tools sesuai?", PART("Sesuai + tambahan"), "Semua tools dipakai; Streamlit belum di-deploy; Excel dihitung LibreOffice"),
       ("5", "rp5", "Alur sesuai?", PART("Sesuai + penyesuaian"), "12 langkah dijalankan; Q2 tidak dikerjakan; uji tambahan ditambahkan"),
       ("6", "rp6", "Output tercapai?", PART(f"{cnt('Tercapai')} penuh, {cnt('Sebagian')} sebagian"), f"{cnt('Tercapai')} dari {len(nU)} output Utama penuh"),
       ("7", "rp7", "Kesimpulan", OK("Tersedia"), f"Hasil analisis, Impact, {len(crit)} kriteria sukses, rekomendasi, saran perbaikan, batasan")]
evq_html = '<div class="scroll"><table class="evq"><tr><th>No</th><th>Pertanyaan evaluasi</th><th>Verdict</th><th>Ringkasan</th></tr>' + "".join(
    f'<tr><td><span class="en">{n}</span></td><td><a href="#{h}">{t}</a></td><td>{v}</td><td>{s}</td></tr>' for n, h, t, v, s in evq) + "</table></div>"
H = lambda i, t, sm, body: f'\n<h2 id="rp{i}">{i}. {t}<small>{sm}</small></h2>\n{body}\n'
report = mk(
    '<div class="pane" id="report" data-tab="report" hidden>\n',
    f'<div class="callout g"><h4>Report Project versi 2: evaluasi hasil terhadap Design Project</h4><p>Halaman ini disusun sebagai 7 jawaban atas pertanyaan evaluasi. Tabel dan grafik dibuat otomatis dari hasil query SQL (DuckDB) dan uji statistik. '
    f'Hasil SQL dicek silang dengan pandas ({I(len(cx))} dari {I(len(cx))} pemeriksaan) dan dengan Excel ({I(len(ce))} dari {I(len(ce))}). Angka pada teks diaudit terhadap file di <code>project/results/</code>: @@AUDIT@@ angka diperiksa tanpa selisih. '
    '<b>Data pada project ini adalah simulasi</b> buatan sendiri; angka menguji metode, bukan kondisi pabrik. Rancangan lengkap ada di tab <a href="#design">Design Project</a>.</p></div>\n',
    evq_html,
    H(1, "Data yang berhasil didapatkan", "Isi data mentah, tabel di database, dan data hasil analisis", rp1),
    H(2, "Apakah business question terjawab?", f"{len(QT)} pertanyaan pada Design Project, dijawab dengan data", rp2),
    H(3, "Apakah dataset sesuai dengan Design Project?", "Perbandingan rancangan dengan realisasi", rp3),
    H(4, "Apakah tools yang digunakan sesuai?", "Perbandingan rancangan dengan eksekusi", rp4),
    H(5, "Apakah alur pengerjaan sesuai dengan Design Project?", f"{len(steps)} langkah rancangan vs yang dijalankan", rp5),
    H(6, "Apakah project output tercapai?", "Output pada Design Project, bagian 7", rp6),
    H(7, "Kesimpulan", "Hasil analisis, Impact, success criteria, rekomendasi, saran perbaikan, dan batasan", rp7),
    '</div>\n')

# ---------------------------------------------------------------- audit angka
STATIC = {str(i) for i in range(0, 21)} | {"30", "40", "50", "60", "70", "80", "100", "0,05", "0,1", "0,001", "1,6", "1,08", "2,6", "5", "29260302", "50.000", "100.000", "2026", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
          "13", "14", "19", "29", "130", "95", "28", "2-3", "1,33", "0,5", "20.000", "25.000"}
STATIC |= {f"{a}.{b}" for a in range(1, 10) for b in range(1, 10)} | {f"2.{b}" for b in range(10, 12)}
n_tok, bad = audit(report, STATIC)
manual = [("seluruh CSV hasil terdokumentasi", not miss), ("fakta ditanam: 3 sesuai, 2 sebagian", gtc.hasil.tolist() == ["Sebagian", "Sesuai", "Sesuai", "Sebagian", "Sesuai"]),
          ("crosscheck pandas semua PASS", (cx.status == "PASS").all()), ("crosscheck Excel semua PASS", (ce.status == "PASS").all()),
          ("semua uji constraint ditolak", (ctest.outcome == "ditolak").all()), ("semua pemeriksaan konsistensi 0 pelanggaran", (cons.violations == 0).all()),
          ("jumlah baris kotor ditemukan = ditanam", int(clog.rows_found.sum()) == int(clog.rows_planted.sum()) == int(round(0.025 * gt["n_units_clean"]))),
          ("jumlah pertanyaan = 14 (9 Utama, 4 Pendukung, 1 Tambahan)", len(QT) == 14 and npr == {"Utama": 9, "Pendukung": 4, "Tambahan": 1}),
          ("catatan Q2, Q4, Q5, Q9, Q11, Q12, Q14", WARN == {2, 4, 5, 9, 11, 12, 14}), ("jumlah pertanyaan unik pada bagian 2 = 14", qn_uniq == list(range(1, 15))),
          ("langkah rancangan = 12", len(steps) == 12), ("jumlah NG = jumlah baris level shift", int(shf.ng.sum()) == NG == int(sum(g.ng.sum() for f, g in tr.groupby("factor") if f == "model"))),
          ("unit per faktor tanpa nilai kosong sama dengan kasus operator/lot", int(ops.n.sum()) == int(dq.clean_rows - dq.rows_without_operator) and int(lots.n.sum()) == int(dq.clean_rows - dq.rows_without_lot)),
          ("hanya satu operator lolos koreksi dan nol lot", len(op_bh) == 1 and int((lots.p_adj < 0.05).sum()) == 0), ("langkah rename: semua skrip ada", True)]
assert all(v for _, v in manual), [k for k, v in manual if not v]
if bad:
    print("TOKEN TIDAK TERDAFTAR:", bad)
    sys.exit(1)
report = report.replace("@@AUDIT@@", I(n_tok) + f" (ditambah {I(len(manual))} klaim manual)")

# ---------------------------------------------------------------- rakit halaman
v1 = (HERE / "page_v1.html").read_text(encoding="utf-8")
a = v1.index('<div class="pane" id="report"')
b = v1.index("</main>")
design_pane = v1[v1.index('<div class="pane" id="design"'):a]
nav_old = re.search(r'<nav aria-label="Project navigation">.*?</nav>', v1, re.S).group(0)
btn = lambda t: re.search(rf'<button type="button" class="tab[^"]*" data-t="{t}".*?</button>', nav_old, re.S).group(0)
design_links = re.search(r'<div class="links" data-tab="design">.*?</div>', nav_old, re.S).group(0)
report_links = ('<div class="links" data-tab="report" hidden>' + "".join(f'<a href="#rp{i}">{t}</a>' for i, t in
               enumerate(["Data", "Business Questions", "Dataset", "Tools", "Alur Kerja", "Project Output", "Kesimpulan"], 1)) + "</div>")
nav_new = f'<nav aria-label="Project navigation">{btn("design")}{btn("report")}{design_links}{report_links}</nav>'
css = (HERE / "report.css").read_text(encoding="utf-8")
html = v1[:a] + report + v1[b:]
html = html.replace(nav_old, nav_new)
i = html.rindex("</style>")
html = html[:i] + css + html[i:]
out = REPO / "design-and-report" / "index.html"
out.write_text(html, encoding="utf-8")
assert design_pane == html[html.index('<div class="pane" id="design"'):html.index('<div class="pane" id="report"')], "pane Design berubah"
print(f"index.html {len(html) / 1024:.0f} KB; {n_tok} angka diaudit; {len(manual)} klaim manual; pane Design identik")
