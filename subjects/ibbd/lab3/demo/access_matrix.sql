-- Доступные текущей роли отношения схемы public.
-- S* — чтение только части столбцов.
SELECT c.relname AS relation,
       CASE WHEN has_table_privilege(c.oid, 'SELECT') THEN 'S'
            WHEN has_any_column_privilege(c.oid, 'SELECT')
                THEN 'S*'
            ELSE '' END AS sel,
       CASE WHEN has_table_privilege(c.oid, 'INSERT') THEN 'I'
            WHEN has_any_column_privilege(c.oid, 'INSERT')
                THEN 'I*'
            ELSE '' END AS ins,
       CASE WHEN has_table_privilege(c.oid, 'UPDATE') THEN 'U'
            WHEN has_any_column_privilege(c.oid, 'UPDATE')
                THEN 'U*'
            ELSE '' END AS upd,
       CASE WHEN has_table_privilege(c.oid, 'DELETE')
            THEN 'D' ELSE '' END AS del
FROM pg_class c
WHERE c.relnamespace = 'public'::regnamespace
  AND c.relkind IN ('r', 'v')
  AND has_any_column_privilege(c.oid,
                               'SELECT, INSERT, UPDATE')
ORDER BY c.relkind, c.relname;
