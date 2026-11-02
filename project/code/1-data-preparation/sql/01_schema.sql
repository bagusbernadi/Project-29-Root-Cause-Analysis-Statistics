-- Skema database rca.duckdb: 4 tabel + 1 view. Kunci utama, kunci asing, dan CHECK menolak data salah.
CREATE TABLE dim_lot (
    lot_id       VARCHAR PRIMARY KEY,
    supplier     VARCHAR NOT NULL CHECK (supplier IN ('Supplier A', 'Supplier B', 'Supplier C')),
    receive_date DATE NOT NULL
);

CREATE TABLE dim_operator (
    operator_id   VARCHAR PRIMARY KEY,
    hire_date     DATE NOT NULL,
    primary_shift VARCHAR NOT NULL CHECK (primary_shift IN ('Shift 1', 'Shift 2'))
);

CREATE TABLE unit_result (
    unit_id      VARCHAR PRIMARY KEY,
    inspect_date DATE NOT NULL,
    model        VARCHAR NOT NULL CHECK (model IN ('5W', '9W', '12W')),
    shift        VARCHAR NOT NULL CHECK (shift IN ('Shift 1', 'Shift 2')),
    operator_id  VARCHAR REFERENCES dim_operator (operator_id),   -- boleh kosong (lihat cleaning_log R3)
    lot_id       VARCHAR REFERENCES dim_lot (lot_id),              -- boleh kosong (lihat cleaning_log R4)
    result       VARCHAR NOT NULL CHECK (result IN ('OK', 'NG')),
    defect_code  VARCHAR,
    CHECK ((result = 'NG') = (defect_code IS NOT NULL))
);

CREATE TABLE test_results (
    factor       VARCHAR NOT NULL,
    level        VARCHAR NOT NULL,
    n            INTEGER NOT NULL,
    ng           INTEGER NOT NULL,
    rate         DOUBLE NOT NULL,
    ci_low       DOUBLE,
    ci_high      DOUBLE,
    expected_min DOUBLE,
    test         VARCHAR,
    p_value      DOUBLE,
    p_adj        DOUBLE,          -- Benjamini-Hochberg dalam satu keluarga faktor
    p_adj_bonf   DOUBLE,          -- Bonferroni sebagai pembanding
    odds_ratio   DOUBLE,
    or_ci_low    DOUBLE,
    or_ci_high   DOUBLE,
    family_size  INTEGER,
    status       VARCHAR NOT NULL,
    direction    VARCHAR,
    PRIMARY KEY (factor, level)
);

CREATE VIEW v_unit AS
SELECT u.unit_id, u.inspect_date, u.model, u.shift, u.operator_id, u.lot_id, l.supplier,
       CASE WHEN u.operator_id IS NULL THEN NULL
            WHEN o.hire_date >= DATE '2026-03-02' THEN 'baru' ELSE 'berpengalaman' END AS experience,
       u.result, CASE WHEN u.result = 'NG' THEN 1 ELSE 0 END AS ng, u.defect_code
FROM unit_result u
LEFT JOIN dim_lot l ON l.lot_id = u.lot_id
LEFT JOIN dim_operator o ON o.operator_id = u.operator_id;
