-- Администратор: выработка сотрудников.
SELECT e.full_name AS employee, e.specialization,
       count(DISTINCT w.order_id) AS orders,
       count(DISTINCT i.customer_id) AS customers,
       count(w.line_no) AS works,
       count(*) FILTER (WHERE w.status = 'done') AS done,
       round(coalesce(sum(w.agreed_price_kopecks)
             FILTER (WHERE w.status <> 'cancelled'), 0)
             / 100.0, 2) AS agreed_rub
FROM employee e
LEFT JOIN order_work w ON w.employee_id = e.employee_id
LEFT JOIN restoration_order o ON o.order_id = w.order_id
LEFT JOIN instrument i
       ON i.instrument_id = o.instrument_id
WHERE %(ostatus)s = '' OR o.status = %(ostatus)s
GROUP BY e.employee_id, e.full_name, e.specialization
