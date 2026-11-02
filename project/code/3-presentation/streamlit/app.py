"""Dashboard Streamlit 3 halaman: Pareto Defect, Perbandingan Faktor, Faktor Terbukti. Data: results/3-presentation/dash_*.csv (simulasi)."""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

RES = Path(__file__).resolve().parents[3] / "results" / "3-presentation"
COL = {"Terbukti": "#1A73E8", "Noise": "#9AA0A6", "Data belum cukup": "#F9AB00", "Pembanding": "#AECBFA"}
st.set_page_config(page_title="Root Cause Analysis Statistics", layout="wide")
st.title("Project 29: Root Cause Analysis Statistics")
st.caption("Data simulasi pabrik lampu LED. Angka menguji metode, bukan kondisi pabrik nyata.")

lev, par, lab = pd.read_csv(RES / "dash_levels.csv"), pd.read_csv(RES / "dash_pareto.csv"), pd.read_csv(RES / "dash_labels.csv")
reg, imp, conf = pd.read_csv(RES / "dash_regression.csv"), pd.read_csv(RES / "dash_impact.csv"), pd.read_csv(RES / "dash_confounding.csv")
page = st.sidebar.radio("Halaman", ["Pareto Defect", "Perbandingan Faktor", "Faktor Terbukti"])
pv = lambda p: "< 0,001" if p < 0.001 else f"{p:.3f}".replace(".", ",")

if page == "Pareto Defect":
    st.header("Pareto defect")
    fig = go.Figure()
    fig.add_bar(x=par.defect_code, y=par.share * 100, name="Porsi NG (%)", marker_color="#1A73E8")
    fig.add_scatter(x=par.defect_code, y=par.cum_share * 100, name="Kumulatif (%)", yaxis="y2", line=dict(color="#3C4043"))
    fig.update_layout(yaxis=dict(title="Porsi NG (%)"), yaxis2=dict(title="Kumulatif (%)", overlaying="y", side="right", range=[0, 100]), height=380, legend=dict(orientation="h"))
    st.plotly_chart(fig, width="stretch")
    k = int((par.cum_share < 0.8).sum() + 1)
    st.info(f"{k} jenis defect pertama menyumbang {par.cum_share.iloc[k - 1] * 100:.1f}% dari {int(par.ng.sum())} unit NG.".replace(".", ","))
    st.dataframe(par.rename(columns={"defect_code": "Kode defect", "ng": "NG", "share": "Porsi", "cum_share": "Kumulatif"}), hide_index=True)

elif page == "Perbandingan Faktor":
    st.header("Defect rate per faktor dengan confidence interval 95%")
    names = dict(zip(lev.factor, lev.factor_label))
    f = st.selectbox("Faktor", list(names), format_func=lambda x: names[x])
    d = lev[lev.factor == f].copy()
    only = st.checkbox("Tampilkan hanya level berstatus Terbukti", value=False)
    if only:
        d = d[d.status == "Terbukti"]
    fig = go.Figure(go.Bar(x=d.level, y=d.rate * 100, marker_color=[COL.get(s, "#9AA0A6") for s in d.status],
                           error_y=dict(type="data", symmetric=False, array=(d.ci_high - d.rate) * 100, arrayminus=(d.rate - d.ci_low) * 100),
                           hovertext=[f"{s}, n = {n}" for s, n in zip(d.status, d.n)]))
    fig.add_hline(y=lev[lev.factor == f].ng.sum() / lev[lev.factor == f].n.sum() * 100, line_dash="dash", line_color="#D93025", annotation_text="rata-rata")
    fig.update_layout(yaxis_title="Defect rate (%)", height=380)
    st.plotly_chart(fig, width="stretch")
    st.caption("Biru = terbukti (p terkoreksi < 0,05), abu-abu = noise, kuning = data belum cukup (n < 30). Garis merah = rata-rata faktor.")
    t = d[["level", "n", "ng", "rate", "test", "p_value", "p_adj", "p_adj_bonf", "odds_ratio", "status"]].copy()
    for c in ("p_value", "p_adj", "p_adj_bonf"):
        t[c] = t[c].map(lambda p: "" if pd.isna(p) else pv(p))
    t["rate"] = (t.rate * 100).round(2).astype(str) + "%"
    t["odds_ratio"] = t.odds_ratio.round(2)
    st.dataframe(t.rename(columns={"level": "Level", "ng": "NG", "rate": "Defect rate", "test": "Uji", "p_value": "p-value", "p_adj": "p BH", "p_adj_bonf": "p Bonferroni", "odds_ratio": "Odds ratio", "status": "Status"}), hide_index=True)

else:
    st.header("Faktor yang terbukti")
    st.dataframe(lab[["factor_label", "label", "detail"]].rename(columns={"factor_label": "Faktor", "label": "Label", "detail": "Keterangan"}), hide_index=True)
    r = reg[reg.model.str.startswith("Bersamaan")]
    fig = go.Figure(go.Scatter(x=r.odds_ratio, y=r.term, mode="markers", marker=dict(color="#1A73E8", size=10),
                               error_x=dict(type="data", symmetric=False, array=r.or_high - r.odds_ratio, arrayminus=r.odds_ratio - r.or_low)))
    fig.add_vline(x=1, line_dash="dash", line_color="#5F6368")
    fig.update_layout(title="Forest plot odds ratio (regresi logistik, semua faktor bersamaan)", xaxis_title="Odds ratio (CI 95%)", xaxis_type="log", height=360)
    st.plotly_chart(fig, width="stretch")
    st.subheader("Shift: tampak berbeda, tetapi karena operator baru")
    c = conf.copy()
    c["Defect rate Shift 2"] = (c.rate_shift2 * 100).round(2).astype(str) + "%"
    c["Defect rate Shift 1"] = (c.rate_shift1 * 100).round(2).astype(str) + "%"
    c["p-value"] = c.p_value.map(pv)
    st.dataframe(c[["comparison", "Defect rate Shift 2", "Defect rate Shift 1", "p-value"]].rename(columns={"comparison": "Perbandingan"}), hide_index=True)
    st.subheader("Estimasi unit NG terhindari (estimated, simulated)")
    i = imp.copy()
    i["Defect rate"], i["Baseline"] = (i.rate * 100).round(2).astype(str) + "%", (i.baseline_rate * 100).round(2).astype(str) + "%"
    i["NG terhindari (periode data)"], i["Per tahun"] = i.ng_avoided_period.round(0).astype(int), i.ng_avoided_year.round(0).astype(int)
    st.dataframe(i[["factor", "level", "Defect rate", "Baseline", "NG terhindari (periode data)", "Per tahun"]].rename(columns={"factor": "Faktor", "level": "Level"}), hide_index=True)
    st.caption("Pengalaman operator 'baru' dan OP19 mencakup unit yang sama, jadi angkanya tidak dijumlahkan. Pola bukan bukti sebab; tindakan perlu dicek di lapangan dan dipakai untuk pelatihan, bukan menilai orang.")
