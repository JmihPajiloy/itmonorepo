-- Администратор: журнал изменений по ролям.
SELECT coalesce(g.rolname, '-') AS app_group,
       l.db_role, l.table_name,
       count(*) FILTER (WHERE l.operation = 'I') AS ins,
       count(*) FILTER (WHERE l.operation = 'U') AS upd,
       count(*) FILTER (WHERE l.operation = 'D') AS del,
       count(*) AS total,
       to_char(max(l.changed_at), 'YYYY-MM-DD HH24:MI:SS')
           AS last_change
FROM change_log l
LEFT JOIN pg_roles r ON r.rolname = l.db_role
LEFT JOIN pg_auth_members m ON m.member = r.oid
LEFT JOIN pg_roles g ON g.oid = m.roleid
WHERE %(op)s = '' OR l.operation = %(op)s
GROUP BY g.rolname, l.db_role, l.table_name
