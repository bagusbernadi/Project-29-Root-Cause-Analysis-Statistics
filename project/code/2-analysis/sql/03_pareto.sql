-- Pareto defect (Q1): kode defect, jumlah NG, porsi, dan porsi kumulatif.
WITH d AS (SELECT defect_code, CAST(count(*) AS INTEGER) AS ng FROM unit_result WHERE result = 'NG' GROUP BY defect_code)
SELECT defect_code, ng, ng * 1.0 / sum(ng) OVER () AS share,
       sum(ng) OVER (ORDER BY ng DESC, defect_code) * 1.0 / sum(ng) OVER () AS cum_share
FROM d ORDER BY ng DESC, defect_code;
