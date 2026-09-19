-- Представления из п. 5 ЛР1, перенесённые в PostgreSQL.
BEGIN;

-- Приёмщик: карточки заказов и контакты для уведомлений.
CREATE VIEW v_reception_orders AS
SELECT o.order_id, c.full_name AS customer_name, c.phone,
       i.inventory_no, i.name AS instrument_name,
       t.name AS instrument_type,
       o.accepted_on, o.due_on, o.status
FROM restoration_order o
JOIN instrument i      ON i.instrument_id = o.instrument_id
JOIN customer c        ON c.customer_id = i.customer_id
JOIN instrument_type t ON t.type_id = i.type_id;

-- Приёмщик: стоимость, оплаты и остаток. Суммы считаются
-- до соединения, чтобы работы и оплаты не перемножались.
CREATE VIEW v_reception_balances AS
WITH costs AS (
    SELECT order_id, sum(agreed_price_kopecks) AS total
    FROM order_work
    WHERE status <> 'cancelled'
    GROUP BY order_id
), paid AS (
    SELECT order_id, sum(amount_kopecks) AS total
    FROM payment
    GROUP BY order_id
)
SELECT o.order_id, c.full_name AS customer_name,
       coalesce(costs.total, 0) AS agreed_kopecks,
       coalesce(paid.total, 0) AS paid_kopecks,
       coalesce(costs.total, 0) - coalesce(paid.total, 0)
           AS balance_kopecks
FROM restoration_order o
JOIN instrument i ON i.instrument_id = o.instrument_id
JOIN customer c   ON c.customer_id = i.customer_id
LEFT JOIN costs   ON costs.order_id = o.order_id
LEFT JOIN paid    ON paid.order_id = o.order_id;

-- Реставратор: очередь работ без контактов и финансов.
CREATE VIEW v_restorer_tasks AS
SELECT w.employee_id, e.full_name AS restorer_name,
       w.order_id, w.line_no, i.inventory_no,
       i.name AS instrument_name, s.name AS service_name,
       o.due_on, w.status AS work_status
FROM order_work w
JOIN employee e          ON e.employee_id = w.employee_id
JOIN restoration_order o ON o.order_id = w.order_id
JOIN instrument i        ON i.instrument_id = o.instrument_id
JOIN service s           ON s.service_id = w.service_id
WHERE w.status IN ('planned', 'in_progress')
  AND o.status IN ('accepted', 'in_progress');

-- Реставратор: история осмотров с авторством заключений.
CREATE VIEW v_restorer_inspections AS
SELECT x.inspection_id, x.order_id, i.inventory_no,
       i.name AS instrument_name, x.inspected_on,
       e.employee_id, e.full_name AS inspector_name,
       x.conclusion
FROM inspection x
JOIN employee e          ON e.employee_id = x.employee_id
JOIN restoration_order o ON o.order_id = x.order_id
JOIN instrument i        ON i.instrument_id = o.instrument_id;

COMMIT;
