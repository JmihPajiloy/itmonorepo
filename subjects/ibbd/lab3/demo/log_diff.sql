-- Поля, изменённые операциями UPDATE: было и стало.
SELECT l.log_id AS id, e.key AS field,
       l.old_row -> e.key AS old_value, e.value AS new_value
FROM change_log l,
     jsonb_each(l.new_row) AS e
WHERE l.operation = 'U'
  AND l.old_row -> e.key IS DISTINCT FROM e.value
ORDER BY l.log_id, e.key;
-- Удалённая строка сохраняется целиком в old_row.
SELECT log_id AS id, jsonb_pretty(old_row) AS deleted_row
FROM change_log WHERE operation = 'D';
