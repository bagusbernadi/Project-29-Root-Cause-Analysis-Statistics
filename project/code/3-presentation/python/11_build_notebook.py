"""Membuat dan mengeksekusi results/3-presentation/analysis.ipynb (Q1 sampai Q14) dari CSV hasil dan rca.duckdb."""
import sys
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import DB_PATH, RES_PRESENT, ROOT  # noqa: E402

md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
setup = f"""import duckdb, pandas as pd
from scipy.stats import chi2_contingency, fisher_exact
pd.options.display.float_format = '{{:.4f}}'.format
R = r'{(ROOT / 'results' / '2-analysis').as_posix()}'
con = duckdb.connect(r'{DB_PATH.as_posix()}', read_only=True)
tr = pd.read_csv(R + '/test_results.csv')"""
cells = [md("# Project 29: Root Cause Analysis Statistics\nNotebook ini mencatat setiap uji, syarat, hasil, dan batas kesimpulannya. Data simulasi; angka menguji metode, bukan kondisi pabrik. Aturan: `project/docs/analysis_rules.md`."),
         code(setup),
         md("## Q1. Pareto defect\nJenis defect yang menyumbang sekitar 80% NG."), code("pd.read_csv(R + '/pareto.csv')"),
         md("## Q2. NG per stasiun inspeksi\nTidak bisa dijawab: data simulasi v1 tidak punya kolom `inspect_station` (lihat Report bagian 3)."), code("con.execute('DESCRIBE unit_result').df()[['column_name']].T"),
         md("## Q3. Shift 1 vs Shift 2 (chi-square Pearson, tanpa koreksi kontinuitas)"),
         code("t = con.execute(\"SELECT shift, sum(ng) ng, count(*)-sum(ng) ok FROM v_unit GROUP BY shift ORDER BY shift\").df()\nprint(t)\nchi2, p, dof, exp = chi2_contingency(t[['ng','ok']].values, correction=False)\nprint('chi2 =', round(chi2, 3), 'p =', round(p, 4), 'expected minimal =', round(exp.min(), 1))"),
         md("## Q4 dan Q5. Operator dan lot: uji per level dengan koreksi Benjamini-Hochberg\np mentah bisa tampak signifikan; setelah koreksi karena banyak perbandingan hanya yang kuat yang bertahan."),
         code("o = tr[tr.factor=='operator_id'][['level','n','ng','rate','test','p_value','p_adj','p_adj_bonf','odds_ratio','status']]\no.sort_values('p_value').head(6)"),
         code("l = tr[tr.factor=='lot_id'][['level','n','ng','rate','test','p_value','p_adj','odds_ratio','status']]\nl.sort_values('p_value').head(6)"),
         code("tr[tr.factor=='supplier'][['level','n','ng','rate','p_value','p_adj','odds_ratio','status']]"),
         md("## Q6 dan Q8. Model lampu, uji keseluruhan, dan Cramér's V"), code("pd.read_csv(R + '/factor_tests.csv')"),
         md("## Q7. Odds ratio dan CI 95% untuk level yang terbukti"), code("tr[tr.status=='Terbukti'][['factor','level','n','rate','odds_ratio','or_ci_low','or_ci_high','p_adj']]"),
         md("## Q9 dan Q10. Regresi logistik dan faktor yang saling terkait"), code("pd.read_csv(R + '/regression.csv')"),
         code("pd.read_csv(R + '/confounding.csv')"), code("pd.read_csv(R + '/lr_tests.csv')"),
         md("## Q11. Dampak (estimated, simulated)"), code("pd.read_csv(R + '/impact.csv')"),
         md("## Q12. Validasi terhadap ground truth"), code("pd.read_csv(R + '/ground_truth_check.csv').style.hide(axis='index')"),
         md("## Q13. Syarat uji dan data tidak valid"), code("pd.read_csv(R.replace('2-analysis','1-data-preparation') + '/cleaning_log.csv')"), code("pd.read_csv(R + '/sensitivity.csv').T"),
         md("## Q14. Jumlah unit yang dibutuhkan (power 80%)"), code("pd.read_csv(R + '/power.csv')"),
         md("## Cek silang\nSQL vs pandas dan SQL/Python vs Excel (dihitung LibreOffice)."), code("pd.concat([pd.read_csv(R + '/crosscheck.csv').status.value_counts(), pd.read_csv(R + '/crosscheck_excel.csv').status.value_counts()], axis=1, keys=['pandas','Excel'])"),
         md("## Batas kesimpulan\nUji statistik menunjukkan keterkaitan, bukan sebab. Lot yang ditanam tidak terbukti pada ukuran data ini (Q14 menjelaskan alasannya). Hasil per operator dipakai untuk pelatihan, bukan menilai orang.")]
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
NotebookClient(nb, timeout=300, kernel_name="python3").execute()
nbf.write(nb, RES_PRESENT / "analysis.ipynb")
err = [o for c in nb.cells if c.cell_type == "code" for o in c.outputs if o.output_type == "error"]
assert not err, err
print("analysis.ipynb dieksekusi:", sum(c.cell_type == "code" for c in nb.cells), "sel kode, tanpa error")
