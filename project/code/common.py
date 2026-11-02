"""Pengaturan bersama untuk semua skrip. Semua jalur relatif terhadap folder project/."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # folder project/
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"                                 # data simulasi mentah (tidak di-commit)
CLEAN_DIR = DATA / "clean"                             # data bersih (tidak di-commit)
GROUND_TRUTH = DATA / "ground_truth.json"
GROUND_TRUTH_DIRTY = DATA / "ground_truth_dirty.csv"
DB_PATH = ROOT / "rca.duckdb"
CODE = ROOT / "code"
SQL_PREP = CODE / "1-data-preparation" / "sql"
SQL_ANALYSIS = CODE / "2-analysis" / "sql"
RES_PREP = ROOT / "results" / "1-data-preparation"
RES_ANALYSIS = ROOT / "results" / "2-analysis"
RES_PRESENT = ROOT / "results" / "3-presentation"
DOCS_DIR = ROOT / "docs"
for _d in (RAW_DIR, CLEAN_DIR, RES_PREP, RES_ANALYSIS, RES_PRESENT, DOCS_DIR):
    _d.mkdir(parents=True, exist_ok=True)              # folder kosong tidak ikut di-commit

SEED = 29260302
ALPHA = 0.05                                           # tingkat signifikansi
MIN_N = 30                                             # level dengan n < 30 tidak diuji ("data belum cukup")
MIN_EXPECTED = 5                                       # expected count minimum chi-square; di bawahnya Fisher exact
STUDY_START = "2026-03-02"                             # operator dengan hire_date >= ini disebut "baru"
FACTORS = ["shift", "operator_id", "lot_id", "supplier", "model", "experience"]
FACTOR_LABEL = {"shift": "Shift", "operator_id": "Operator", "lot_id": "Lot chip LED", "supplier": "Supplier",
                "model": "Model lampu", "experience": "Pengalaman operator"}
REFERENCE = {"shift": "Shift 1", "experience": "berpengalaman"}   # level pembanding pada faktor dua level
UNITS_PER_YEAR_FACTOR = 12 / 6                         # data mencakup sekitar 6 bulan (130 hari kerja); dipakai untuk proyeksi tahunan


def result(name):
    """Cari CSV hasil di folder hasil per tahap."""
    for d in (RES_PREP, RES_ANALYSIS, RES_PRESENT):
        p = d / name
        if p.exists():
            return p
    raise FileNotFoundError(name)


def chdir_root():
    os.chdir(ROOT)
