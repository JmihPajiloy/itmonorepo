-- Реставратор: работы по исполнителям и услугам.
SELECT e.full_name AS restorer, s.name AS service,
       count(*) AS works,
       count(*) FILTER (WHERE w.status = 'planned')
           AS planned,
       count(*) FILTER (WHERE w.status = 'in_progress')
           AS in_progress,
       count(*) FILTER (WHERE w.status = 'done') AS done,
       min(o.due_on) FILTER (WHERE w.status IN
           ('planned', 'in_progress')) AS nearest_due
FROM order_work w
JOIN employee e ON e.employee_id = w.employee_id
JOIN service s ON s.service_id = w.service_id
JOIN restoration_order o ON o.order_id = w.order_id
WHERE (%(mine)s = ''
       OR w.employee_id = current_employee_id())
  AND (%(ostatus)s = '' OR o.status = %(ostatus)s)
GROUP BY e.full_name, s.name
