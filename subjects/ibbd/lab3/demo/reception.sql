-- Сеанс приёмщика reception_orlova.
SELECT current_user, session_user;
-- Разрешено: приём нового заказа и оплата.
INSERT INTO customer (full_name, phone)
VALUES ('Белова Ксения Олеговна', '+7 900 000-00-09')
RETURNING customer_id AS cust \gset
INSERT INTO instrument (customer_id, type_id,
                        inventory_no, name)
VALUES (:cust, 2, 'INS-009', 'Гитара концертная')
RETURNING instrument_id AS inst \gset
INSERT INTO restoration_order (instrument_id, accepted_on,
                               due_on, status, complaint)
VALUES (:inst, '2026-09-19', '2026-10-03', 'accepted',
        'Отклеилась подставка')
RETURNING order_id AS ord \gset
INSERT INTO payment (order_id, paid_on, amount_kopecks,
                     method, receipt_no)
VALUES (:ord, '2026-09-19', 100000, 'card', 'DEMO-009');
UPDATE customer SET email = 'belova@example.test'
WHERE customer_id = :cust;
UPDATE restoration_order SET due_on = '2026-10-01'
WHERE order_id = :ord;
SELECT order_id, customer_name, due_on, status
FROM v_reception_orders WHERE order_id = :ord;
-- Запрещено: данные сотрудников, работы, журнал, секреты,
-- удаление записей.
SELECT full_name, work_email FROM employee;
SELECT * FROM order_work;
SELECT * FROM v_restorer_tasks;
SELECT count(*) FROM change_log;
SELECT count(*) FROM access_secret;
DELETE FROM payment WHERE order_id = :ord;
