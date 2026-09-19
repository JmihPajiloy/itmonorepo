-- Сеанс суперпользователя: удаление и просмотр журнала.
DELETE FROM payment WHERE receipt_no = 'DEMO-009';
SELECT log_id AS id,
       to_char(changed_at, 'HH24:MI:SS') AS changed_at,
       db_role, operation AS op, table_name
FROM change_log ORDER BY log_id;
SELECT log_id AS id, tx_id, client, row_key
FROM change_log ORDER BY log_id;
