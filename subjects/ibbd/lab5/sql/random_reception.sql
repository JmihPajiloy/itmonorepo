-- Случайные изменения от имени приёмщика reception_orlova.
SELECT setseed(0.5);
BEGIN;
INSERT INTO customer (full_name, phone, email)
VALUES ('Случайный Клиент ' || (random() * 100)::int,
        '+7 900 555-00-00', NULL)
RETURNING customer_id, full_name;

UPDATE restoration_order
SET due_on = due_on + (1 + random() * 30)::int
WHERE order_id = (SELECT order_id FROM restoration_order
                  WHERE status <> 'closed'
                  ORDER BY random() LIMIT 1)
RETURNING order_id, due_on;

INSERT INTO payment (order_id, paid_on, amount_kopecks,
                     method, receipt_no)
SELECT order_id, current_date,
       (1000 + random() * 9000)::int * 100, 'card',
       'RND-' || (random() * 1e6)::int
FROM restoration_order WHERE status <> 'closed'
ORDER BY random() LIMIT 1
RETURNING payment_id, order_id, amount_kopecks;
COMMIT;
