"""Menguji dashboard dengan Streamlit AppTest: tiap halaman dan tiap faktor harus tampil tanpa error."""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "streamlit" / "app.py")
n = 0
for page in ("Pareto Defect", "Perbandingan Faktor", "Faktor Terbukti"):
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.radio[0].set_value(page).run()
    assert not at.exception, (page, at.exception)
    n += 1
    if page == "Perbandingan Faktor":
        for opt in at.selectbox[0].options:
            at.selectbox[0].set_value(opt).run()
            assert not at.exception, (opt, at.exception)
            n += 1
print("AppTest lulus:", n, "tampilan tanpa error")
