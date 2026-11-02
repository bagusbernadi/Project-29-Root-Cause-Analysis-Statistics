"""One-sheet faktor terbukti (PDF dan PNG) dari CSV hasil; HTML dicetak dengan Chromium (Playwright)."""
import sys
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import FACTOR_LABEL, RES_PRESENT, result  # noqa: E402

id_ = lambda x, d=1: f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
lev, par, lab = pd.read_csv(result("dash_levels.csv")), pd.read_csv(result("dash_pareto.csv")), pd.read_csv(result("dash_labels.csv"))
reg, imp, conf = pd.read_csv(result("dash_regression.csv")), pd.read_csv(result("dash_impact.csv")), pd.read_csv(result("dash_confounding.csv"))
ops = lev[(lev.factor == "operator_id")]
op19, op08 = ops[ops.level == "OP19"].iloc[0], ops[ops.level == "OP08"].iloc[0]
adj = reg[(reg.model.str.startswith("Bersamaan")) & (reg.term == "Operator baru")].iloc[0]
n_ng = int(par.ng.sum())
i19 = imp[imp.level == "OP19"].iloc[0]
bars = "".join(f'<div class="b"><span>{r.defect_code}</span><i style="width:{r.share * 100 * 2.2:.0f}px"></i><b>{id_(r.share * 100)}%</b></div>' for r in par.itertuples())
cards = "".join(f'<div class="c {"ok" if r.label == "Terbukti" else ("w" if r.label.startswith("Dijelaskan") else "n")}"><h3>{r.factor_label}</h3><p class="l">{r.label}</p><p>{r.detail.replace(".", ",")}</p></div>' for r in lab.itertuples())
html = f"""<!doctype html><html lang="id"><head><meta charset="utf-8"><style>
body{{font:15px/1.45 'Source Sans 3',Calibri,Arial,sans-serif;color:#202124;margin:0;padding:28px 34px;width:1000px;background:#fff}}
h1{{font-size:28px;margin:0 0 4px;color:#174EA6}}.sub{{color:#5F6368;margin:0 0 16px}}
.k{{display:flex;gap:14px;margin:12px 0}}.k div{{flex:1;border:1px solid #DADCE0;border-radius:14px;padding:12px 16px}}.k b{{display:block;font-size:30px;color:#1A73E8}}
.g{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:14px 0}}.c{{border-radius:14px;padding:10px 14px;border:1px solid #DADCE0}}.c h3{{margin:0;font-size:16px}}.c .l{{font-weight:800;margin:2px 0}}
.c.ok{{background:#E8F0FE;border-color:#1A73E8}}.c.w{{background:#FEF7E0;border-color:#FDD663}}.c.n{{background:#F1F3F4}}.c p{{margin:2px 0;font-size:13.5px}}
.b{{display:flex;align-items:center;gap:8px;margin:3px 0}}.b span{{width:90px}}.b i{{display:block;height:14px;background:#1A73E8;border-radius:3px}}
.n2{{background:#FEF7E0;border:1px solid #FDD663;border-radius:12px;padding:10px 14px;margin-top:12px;font-size:13.5px}}
</style></head><body>
<h1>Faktor penyebab NG yang terbukti secara statistik</h1><p class="sub">Project 29 · pabrik lampu LED · data simulasi ({id_(n_ng, 0)} unit NG dari 50.000 unit, ±6 bulan)</p>
<div class="k"><div><b>1 dari 20</b>operator lolos koreksi multiple testing (OP19, odds ratio {id_(op19.odds_ratio)})</div>
<div><b>{id_(op19.rate * 100)}%</b>defect rate OP19, dibanding {id_(i19.baseline_rate * 100)}% unit lain</div>
<div><b>±{id_(i19.ng_avoided_year, 0)}</b>unit NG per tahun bisa dihindari (estimated, simulated)</div></div>
<div class="g">{cards}</div>
<h3>Pareto defect</h3>{bars}
<div class="n2"><b>Cara membaca.</b> Operator OP08 tampak buruk jika diuji sendirian (p {id_(op08.p_value, 3)}), tetapi setelah koreksi karena 20 operator dibandingkan sekaligus p = {id_(op08.p_adj, 2)}, jadi dianggap noise. Shift 2 tampak lebih tinggi ({id_(conf.rate_shift2.iloc[0] * 100, 2)}% vs {id_(conf.rate_shift1.iloc[0] * 100, 2)}%), tetapi tanpa OP19 selisihnya hilang. Uji statistik menunjukkan keterkaitan, bukan sebab; hasil per operator dipakai untuk pelatihan, bukan menilai orang.</div>
</body></html>"""
(RES_PRESENT / "onesheet.html").write_text(html, encoding="utf-8")
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1070, "height": 900})
    pg.set_content(html)
    pg.screenshot(path=str(RES_PRESENT / "onesheet.png"), full_page=True)
    pg.pdf(path=str(RES_PRESENT / "onesheet.pdf"), width="1070px", height=f"{pg.evaluate('document.body.scrollHeight') + 40}px", print_background=True)
    b.close()
(RES_PRESENT / "onesheet.html").unlink()
print("onesheet.pdf dan onesheet.png dibuat")
