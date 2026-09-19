-- Случайные изменения от имени администратора postgres.
-- setseed делает выбор строк воспроизводимым.
SELECT setseed(0.2026);
BEGIN;
UPDATE customer
SET phone = '+7 999 ' || lpad((random() * 9999999)::int::text,
                              7, '0')
WHERE customer_id = (SELECT customer_id FROM customer
                     ORDER BY random() LIMIT 1)
RETURNING customer_id, phone;

UPDATE service
SET base_price_kopecks = (base_price_kopecks
                          * (1 + random()))::int
WHERE service_id IN (SELECT service_id FROM service
                     ORDER BY random() LIMIT 2)
RETURNING service_id, base_price_kopecks;

UPDATE order_work SET status = 'cancelled'
WHERE (order_id, line_no) = (
  SELECT order_id, line_no FROM order_work
  WHERE status IN ('planned', 'in_progress')
  ORDER BY random() LIMIT 1)
RETURNING order_id, line_no, status;

DELETE FROM inspection
WHERE inspection_id = (SELECT inspection_id FROM inspection
                       ORDER BY random() LIMIT 1)
RETURNING inspection_id, order_id, inspected_on;
COMMIT;
