-- Defect rate per level faktor (Q3-Q6). Baris tanpa nilai faktor (operator kosong, lot tidak dikenal) tidak ikut faktor itu.
SELECT 'shift' AS factor, shift AS level, CAST(count(*) AS INTEGER) AS n, CAST(sum(ng) AS INTEGER) AS ng FROM v_unit GROUP BY shift
UNION ALL SELECT 'operator_id', operator_id, CAST(count(*) AS INTEGER), CAST(sum(ng) AS INTEGER) FROM v_unit WHERE operator_id IS NOT NULL GROUP BY operator_id
UNION ALL SELECT 'lot_id', lot_id, CAST(count(*) AS INTEGER), CAST(sum(ng) AS INTEGER) FROM v_unit WHERE lot_id IS NOT NULL GROUP BY lot_id
UNION ALL SELECT 'supplier', supplier, CAST(count(*) AS INTEGER), CAST(sum(ng) AS INTEGER) FROM v_unit WHERE supplier IS NOT NULL GROUP BY supplier
UNION ALL SELECT 'model', model, CAST(count(*) AS INTEGER), CAST(sum(ng) AS INTEGER) FROM v_unit GROUP BY model
UNION ALL SELECT 'experience', experience, CAST(count(*) AS INTEGER), CAST(sum(ng) AS INTEGER) FROM v_unit WHERE experience IS NOT NULL GROUP BY experience
ORDER BY 1, 2;
