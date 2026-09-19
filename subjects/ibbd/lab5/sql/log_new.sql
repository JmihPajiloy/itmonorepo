-- Записи журнала ЛР3 после точки восстановления (:since).
SELECT log_id AS id, changed_at::time(0) AS at,
       tx_id AS tx, db_role,
       operation || ' ' || table_name AS change
FROM change_log WHERE log_id > :since ORDER BY log_id;
-- Значения: изменённые поля UPDATE, ключи INSERT и DELETE.
SELECT l.log_id AS id, e.key AS field,
       l.old_row ->> e.key AS old, e.value #>> '{}' AS new
FROM change_log l, jsonb_each(l.new_row) e
WHERE l.log_id > :since AND l.operation = 'U'
  AND l.old_row -> e.key IS DISTINCT FROM e.value
UNION ALL
SELECT l.log_id, k.key,
       CASE l.operation WHEN 'D' THEN k.value #>> '{}' END,
       CASE l.operation WHEN 'I' THEN k.value #>> '{}' END
FROM change_log l, jsonb_each(l.row_key) k
WHERE l.log_id > :since AND l.operation IN ('I', 'D')
ORDER BY 1, 2;
