-- Число строк и MD5 упорядоченного содержимого таблиц.
SELECT tab AS table_name, count(*) AS rows,
       md5(string_agg(r, '|' ORDER BY r)) AS md5
FROM (
  SELECT 'customer' tab, x::text r FROM customer x
  UNION ALL SELECT 'instrument_type', x::text
    FROM instrument_type x
  UNION ALL SELECT 'instrument', x::text FROM instrument x
  UNION ALL SELECT 'employee', x::text FROM employee x
  UNION ALL SELECT 'restoration_order', x::text
    FROM restoration_order x
  UNION ALL SELECT 'service', x::text FROM service x
  UNION ALL SELECT 'order_work', x::text FROM order_work x
  UNION ALL SELECT 'inspection', x::text FROM inspection x
  UNION ALL SELECT 'payment', x::text FROM payment x
  UNION ALL SELECT 'change_log', x::text FROM change_log x
) s
GROUP BY tab ORDER BY tab;
