#!/bin/sh
# Пересоздаёт БД workshop в учебном кластере и сохраняет результаты проверок.
set -eu

LAB_DIR=$(cd "$(dirname "$0")" && pwd)
PG="$LAB_DIR/../tools/pg.sh"
DB="${IBBD_DB:-workshop}"
OUT="${IBBD_OUT:-$LAB_DIR/verification}"

"$PG" start
"$PG" reset-db "$DB"

for f in 01_tables 02_relations 03_indexes 04_alter 05_data 06_views; do
  "$PG" psql -d "$DB" -q -v ON_ERROR_STOP=1 -f "$LAB_DIR/sql/$f.sql" >/dev/null
done

mkdir -p "$OUT"
run() {
  "$PG" psql -d "$DB" -v ON_ERROR_STOP=1 -P pager=off -P footer=on "$@"
}

run -c "SELECT version();" -t -A >"$OUT/version.txt"

run >"$OUT/row-counts.txt" <<'SQL'
SELECT 'customer' AS table_name, count(*) AS rows FROM customer
UNION ALL SELECT 'instrument_type', count(*) FROM instrument_type
UNION ALL SELECT 'instrument', count(*) FROM instrument
UNION ALL SELECT 'employee', count(*) FROM employee
UNION ALL SELECT 'restoration_order', count(*) FROM restoration_order
UNION ALL SELECT 'service', count(*) FROM service
UNION ALL SELECT 'order_work', count(*) FROM order_work
UNION ALL SELECT 'inspection', count(*) FROM inspection
UNION ALL SELECT 'payment', count(*) FROM payment;
SQL

run >"$OUT/foreign-keys.txt" <<'SQL'
SELECT conname, confrelid::regclass AS parent,
       CASE confdeltype WHEN 'r' THEN 'RESTRICT'
            ELSE confdeltype::text END AS on_delete
FROM pg_constraint
WHERE contype = 'f' AND connamespace = 'public'::regnamespace
ORDER BY conrelid::regclass::text, conname;
SQL

run >"$OUT/indexes.txt" <<'SQL'
SELECT indexname,
       regexp_replace(indexdef, '^.* USING btree (\([^)]*\)).*$', '\1')
       AS columns
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
SQL

run >"$OUT/alter.txt" <<'SQL'
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'restoration_order' ORDER BY ordinal_position;
SELECT order_id, status, accepted_on, closed_on
FROM restoration_order ORDER BY order_id;
SQL

run >"$OUT/views.txt" <<'SQL'
SELECT order_id AS id, split_part(customer_name, ' ', 1) AS customer,
       inventory_no AS inv, due_on, status
FROM v_reception_orders
WHERE status IN ('accepted', 'in_progress', 'ready')
ORDER BY due_on, order_id;
SELECT order_id AS id, split_part(customer_name, ' ', 1) AS customer,
       agreed_kopecks AS agreed,
       paid_kopecks AS paid, balance_kopecks AS balance
FROM v_reception_balances ORDER BY order_id;
SELECT split_part(restorer_name, ' ', 1) AS restorer,
       order_id AS id, line_no AS ln, service_name,
       work_status AS status
FROM v_restorer_tasks ORDER BY employee_id, due_on, order_id, line_no;
SELECT inspection_id AS insp, order_id AS id, inventory_no AS inv,
       inspected_on, split_part(inspector_name, ' ', 1) AS inspector
FROM v_restorer_inspections ORDER BY inventory_no, inspected_on, inspection_id;
SQL

run -q >"$OUT/explain.txt" <<'SQL'
SET enable_seqscan = off;
EXPLAIN (COSTS OFF)
SELECT order_id FROM restoration_order
WHERE status = 'in_progress' ORDER BY due_on;
EXPLAIN (COSTS OFF)
SELECT * FROM payment WHERE order_id = 1;
EXPLAIN (COSTS OFF)
SELECT * FROM customer WHERE phone = '+7 900 000-00-04';
SQL

# Отрицательные пробы: каждая команда должна быть отклонена СУБД.
run -q >"$OUT/constraints.txt" <<'SQL'
CREATE TEMP TABLE probe(name text, result text);
DO $$
DECLARE
  probes text[][] := ARRAY[
    ['второй активный заказ',
     'INSERT INTO restoration_order(instrument_id, accepted_on, due_on, status, complaint) VALUES (1, ''2026-09-15'', ''2026-09-30'', ''accepted'', ''проба'')'],
    ['удаление заказчика',
     'DELETE FROM customer WHERE customer_id = 1'],
    ['несуществующий тип',
     'INSERT INTO instrument(customer_id, type_id, inventory_no, name) VALUES (1, 99, ''INS-999'', ''проба'')'],
    ['закрытие без даты',
     'UPDATE restoration_order SET status = ''closed'' WHERE order_id = 5'],
    ['срок раньше приёма',
     'UPDATE restoration_order SET due_on = ''2026-01-01'' WHERE order_id = 2'],
    ['отрицательная оплата',
     'INSERT INTO payment(order_id, paid_on, amount_kopecks, method, receipt_no) VALUES (2, ''2026-09-06'', -1, ''card'', ''DEMO-X'')']
  ];
  i int;
BEGIN
  FOR i IN 1 .. array_length(probes, 1) LOOP
    BEGIN
      EXECUTE probes[i][2];
      INSERT INTO probe VALUES (probes[i][1], 'ПРИНЯТО (ошибка)');
      RAISE EXCEPTION 'probe accepted: %', probes[i][1];
    EXCEPTION
      WHEN unique_violation OR foreign_key_violation OR check_violation THEN
        INSERT INTO probe VALUES (probes[i][1], SQLSTATE || ' '
          || (regexp_match(SQLERRM, 'constraint "([^"]+)"'))[1]);
    END;
  END LOOP;
END $$;
SELECT name AS probe, result AS rejected_by FROM probe;
SQL

echo "ok: $OUT"
