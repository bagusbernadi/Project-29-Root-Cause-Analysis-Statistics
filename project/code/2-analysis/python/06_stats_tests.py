"""Uji statistik per faktor (Q3-Q10, Q13). Aturan uji ada di project/docs/analysis_rules.md.

Alur tiap level faktor (level lawan sisanya, tabel 2x2):
  n < 30                      -> "Data belum cukup", tidak diuji
  expected count minimal >= 5 -> chi-square Pearson (tanpa koreksi kontinuitas, sama dengan CHISQ.TEST Excel)
  expected count minimal < 5  -> Fisher exact
  p-value dikoreksi per keluarga faktor: Benjamini-Hochberg (utama) dan Bonferroni (pembanding), alpha 5%
Hasil: test_results.csv (dan tabel test_results di rca.duckdb), factor_tests.csv, regression.csv, lr_tests.csv, confounding.csv, sensitivity.csv
"""
import sys
import warnings
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.multitest import multipletests
from statsmodels.stats.proportion import proportion_confint

warnings.filterwarnings("ignore")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import ALPHA, DB_PATH, FACTORS, GROUND_TRUTH_DIRTY, MIN_EXPECTED, MIN_N, RAW_DIR, REFERENCE, RES_ANALYSIS, STUDY_START  # noqa: E402

con = duckdb.connect(str(DB_PATH))
df = con.execute("SELECT * FROM v_unit").df()


def two_by_two(a, b, c, d):
    t = np.array([[a, b], [c, d]], dtype=float)
    exp = t.sum(1)[:, None] * t.sum(0)[None, :] / t.sum()
    return t, float(exp.min())


def odds_ratio(a, b, c, d):
    z = 0.5 if min(a, b, c, d) == 0 else 0.0          # koreksi Haldane bila ada sel nol
    a, b, c, d = a + z, b + z, c + z, d + z
    o = (a * d) / (b * c)
    se = np.sqrt(1 / a + 1 / b + 1 / c + 1 / d)
    return o, o * np.exp(-1.96 * se), o * np.exp(1.96 * se)


def level_tests(d, factor):
    """Satu baris per level: defect rate + CI Wilson, uji level vs sisanya, odds ratio + CI (Woolf)."""
    d = d.dropna(subset=[factor])
    N, NG = len(d), int(d.ng.sum())
    rows = []
    for lvl, g in d.groupby(factor, sort=True):
        n, x = len(g), int(g.ng.sum())
        lo, hi = proportion_confint(x, n, alpha=ALPHA, method="wilson")
        r = dict(factor=factor, level=str(lvl), n=n, ng=x, rate=x / n, ci_low=lo, ci_high=hi, expected_min=np.nan, test=None, p_value=np.nan, p_adj=np.nan,
                 p_adj_bonf=np.nan, odds_ratio=np.nan, or_ci_low=np.nan, or_ci_high=np.nan, family_size=0, status="", direction="")
        if factor in REFERENCE and str(lvl) == REFERENCE[factor]:
            r["status"] = "Pembanding"
        elif n < MIN_N:
            r["status"] = "Data belum cukup"
        else:
            t, emin = two_by_two(x, n - x, NG - x, (N - n) - (NG - x))
            fisher = emin < MIN_EXPECTED
            r["expected_min"], r["test"] = emin, "Fisher exact" if fisher else "Chi-square"
            r["p_value"] = stats.fisher_exact(t)[1] if fisher else stats.chi2_contingency(t, correction=False)[1]
            r["odds_ratio"], r["or_ci_low"], r["or_ci_high"] = odds_ratio(*t.ravel())
        rows.append(r)
    out = pd.DataFrame(rows)
    m = out.p_value.notna()
    k = int(m.sum())
    if k:
        out.loc[m, "p_adj"] = multipletests(out.loc[m, "p_value"], method="fdr_bh")[1]
        out.loc[m, "p_adj_bonf"] = np.minimum(out.loc[m, "p_value"] * k, 1.0)
        out.loc[m, "family_size"] = k
        sig = m & (out.p_adj < ALPHA)
        out.loc[m, "status"] = np.where(sig[m], "Terbukti", "Noise")
        out.loc[sig, "direction"] = np.where(out.loc[sig, "odds_ratio"] > 1, "lebih tinggi", "lebih rendah")
    return out


def analyze(d):
    """Ringkasan kunci satu perlakuan data (dipakai uji sensitivitas Q13)."""
    s = level_tests(d, "shift").set_index("level")
    o = level_tests(d, "operator_id").set_index("level")
    l = level_tests(d, "lot_id")
    p19 = o.loc["OP19"] if "OP19" in o.index else None
    return dict(n=len(d), ng_rate=d.ng.mean(), shift_p=s.loc["Shift 2", "p_value"], shift_rate1=s.loc["Shift 1", "rate"], shift_rate2=s.loc["Shift 2", "rate"],
                operators_tested=int(o.p_value.notna().sum()), operators_sig_raw=int((o.p_value < ALPHA).sum()), operators_sig_bh=int((o.p_adj < ALPHA).sum()),
                op19_or=p19.odds_ratio if p19 is not None else np.nan, lots_tested=int(l.p_value.notna().sum()), lots_sig_raw=int((l.p_value < ALPHA).sum()),
                lots_sig_bh=int((l.p_adj < ALPHA).sum()), op08_p_adj=o.loc["OP08", "p_adj"])


# ---- 1. uji per level, semua faktor
tr = pd.concat([level_tests(df, f) for f in FACTORS], ignore_index=True)
tr.to_csv(RES_ANALYSIS / "test_results.csv", index=False, float_format="%.10g")
con.execute("DELETE FROM test_results")
ins = tr.copy()
ins["n"], ins["ng"], ins["family_size"] = ins.n.astype(int), ins.ng.astype(int), ins.family_size.astype(int)
con.register("tr_df", ins)
con.execute("INSERT INTO test_results SELECT factor, level, n, ng, rate, ci_low, ci_high, expected_min, test, p_value, p_adj, p_adj_bonf, odds_ratio, or_ci_low, or_ci_high, "
            "family_size, status, direction FROM tr_df")
assert con.execute("SELECT count(*) FROM test_results").fetchone()[0] == len(tr)

# ---- 2. uji keseluruhan per faktor + Cramer's V (Q6, Q8)
ft = []
for f in FACTORS:
    d = df.dropna(subset=[f])
    tab = pd.crosstab(d[f], d.ng).values
    chi2, p, dof, exp = stats.chi2_contingency(tab, correction=False)
    ft.append(dict(factor=f, levels=tab.shape[0], n=int(tab.sum()), chi2=chi2, dof=dof, p_value=p, cramers_v=float(np.sqrt(chi2 / tab.sum())),
                   cells_exp_lt5=int((exp < MIN_EXPECTED).sum()), cells=int(exp.size), expected_min=float(exp.min())))
pd.DataFrame(ft).to_csv(RES_ANALYSIS / "factor_tests.csv", index=False, float_format="%.10g")

# ---- 3. regresi logistik (Q9, Q10): kasus lengkap, level pembanding tetap
cc = df.dropna(subset=["operator_id", "lot_id"]).copy()
cc["op_baru"] = (cc.experience == "baru").astype(int)
cc["shift2"] = (cc["shift"] == "Shift 2").astype(int)
TERMS = {"shift2": "Shift 2", "C(model, Treatment('9W'))[T.5W]": "Model 5W", "C(model, Treatment('9W'))[T.12W]": "Model 12W",
         "C(supplier, Treatment('Supplier A'))[T.Supplier B]": "Supplier B", "C(supplier, Treatment('Supplier A'))[T.Supplier C]": "Supplier C", "op_baru": "Operator baru"}
F_ALL = "shift2 + C(model, Treatment('9W')) + C(supplier, Treatment('Supplier A')) + op_baru"
reg = []


def collect(res, model_name):
    ci = res.conf_int()
    for k, lab in TERMS.items():
        if k in res.params.index:
            reg.append(dict(model=model_name, term=lab, odds_ratio=np.exp(res.params[k]), or_low=np.exp(ci.loc[k, 0]), or_high=np.exp(ci.loc[k, 1]), p_value=res.pvalues[k]))


for name, rhs in (("Terpisah: shift", "shift2"), ("Terpisah: model", "C(model, Treatment('9W'))"), ("Terpisah: supplier", "C(supplier, Treatment('Supplier A'))"),
                  ("Terpisah: pengalaman operator", "op_baru")):
    collect(smf.logit(f"ng ~ {rhs}", cc).fit(disp=0), name)
m_all = smf.logit(f"ng ~ {F_ALL}", cc).fit(disp=0)
collect(m_all, "Bersamaan: shift + model + supplier + pengalaman")
regdf = pd.DataFrame(reg)
regdf["p_adj"] = regdf.groupby("model").p_value.transform(lambda s: multipletests(s, method="fdr_bh")[1] if len(s) > 1 else s)   # BH antar suku dalam satu model
reg = regdf.to_dict("records")
regdf.to_csv(RES_ANALYSIS / "regression.csv", index=False, float_format="%.10g")

# ---- 4. uji rasio kemungkinan per kelompok faktor (operator, lot, model) pada model penuh tanpa shift (shift tepat kolinear dengan operator)
cc["operator_id"], cc["lot_id"] = cc.operator_id.astype(str), cc.lot_id.astype(str)
full = smf.logit("ng ~ C(model) + C(operator_id) + C(lot_id)", cc).fit(disp=0, maxiter=200)
lr = []
for lab, rhs in (("Operator", "C(model) + C(lot_id)"), ("Lot chip LED", "C(model) + C(operator_id)"), ("Model lampu", "C(operator_id) + C(lot_id)")):
    red = smf.logit(f"ng ~ {rhs}", cc).fit(disp=0, maxiter=200)
    stat = 2 * (full.llf - red.llf)
    dof = int(full.df_model - red.df_model)
    lr.append(dict(factor=lab, lr_chi2=stat, dof=dof, p_value=stats.chi2.sf(stat, dof)))
pd.DataFrame(lr).to_csv(RES_ANALYSIS / "lr_tests.csv", index=False, float_format="%.10g")

# ---- 5. faktor yang saling terkait: shift dengan dan tanpa operator baru (Q10)
conf = []
s1, s2 = df[df["shift"] == "Shift 1"], df[df["shift"] == "Shift 2"]
for lab, a, b in (("Shift 2 vs Shift 1, semua unit", s2, s1), ("Shift 2 tanpa OP19 vs Shift 1", s2[s2.operator_id != "OP19"], s1)):
    x1, n1, x0, n0 = int(a.ng.sum()), len(a), int(b.ng.sum()), len(b)
    t, _ = two_by_two(x1, n1 - x1, x0, n0 - x0)
    o, lo, hi = odds_ratio(*t.ravel())
    conf.append(dict(comparison=lab, rate_shift2=x1 / n1, rate_shift1=x0 / n0, n_shift2=n1, n_shift1=n0, p_value=stats.chi2_contingency(t, correction=False)[1], odds_ratio=o, or_low=lo, or_high=hi))
pd.DataFrame(conf).to_csv(RES_ANALYSIS / "confounding.csv", index=False, float_format="%.10g")

# ---- 6. uji sensitivitas data kotor (Q13): tiga perlakuan
raw = pd.read_csv(RAW_DIR / "unit_result.csv", dtype=str, keep_default_na=False, na_values=[""])
lots = pd.read_csv(RAW_DIR / "dim_lot.csv")
ops = pd.read_csv(RAW_DIR / "dim_operator.csv")


def enrich(x):
    x = x.merge(lots[["lot_id", "supplier"]], on="lot_id", how="left").merge(ops[["operator_id", "hire_date"]], on="operator_id", how="left")
    x["experience"] = np.where(x.hire_date.isna(), None, np.where(x.hire_date >= STUDY_START, "baru", "berpengalaman"))
    return x


A = raw.copy()                                                                      # A. mentah apa adanya
A["ng"] = (A.result == "NG").astype(int)
bad_ids = set(raw[raw.duplicated(keep="first")].unit_id) | set(raw[~raw.result.isin(["OK", "NG"])].unit_id) | set(raw[raw.operator_id.isna()].unit_id) | set(raw[~raw.lot_id.isin(lots.lot_id)].unit_id)
B = raw[~raw.unit_id.isin(bad_ids)].copy()                                          # B. semua unit bermasalah dibuang
B["ng"] = (B.result == "NG").astype(int)
C = df.copy()                                                                       # C. cleaning sesuai log (dipakai)
sens = []
for lab, x in (("A. Data mentah apa adanya", A), ("B. Semua unit bermasalah dibuang", B), ("C. Cleaning sesuai log (dipakai)", None)):
    sens.append(dict(treatment=lab, **analyze(enrich(x) if x is not None else C)))
pd.DataFrame(sens).to_csv(RES_ANALYSIS / "sensitivity.csv", index=False, float_format="%.10g")
con.close()

t = tr[tr.status == "Terbukti"]
print("Terbukti:", [(r.factor, r.level, round(r.p_adj, 5)) for r in t.itertuples()])
print("sensitivitas:", pd.DataFrame(sens)[["treatment", "n", "shift_p", "operators_sig_raw", "operators_sig_bh", "lots_sig_raw", "lots_sig_bh"]].round(4).to_string(index=False))
print(pd.DataFrame(reg)[["model", "term", "odds_ratio", "p_value"]].round(4).to_string(index=False))
print(pd.DataFrame(lr).round(4).to_string(index=False)); print(pd.DataFrame(conf).round(4).to_string(index=False)); print(pd.DataFrame(ft).round(4).to_string(index=False))
