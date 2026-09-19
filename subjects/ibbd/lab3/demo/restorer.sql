-- Сеанс реставратора restorer_smirnov (сотрудник № 1).
SELECT current_user, current_employee_id();
-- Разрешено: своя очередь работ и осмотры.
SELECT order_id, line_no, service_name, work_status
FROM v_restorer_tasks WHERE employee_id = 1;
UPDATE order_work SET status = 'done'
WHERE order_id = 1 AND line_no = 1;
INSERT INTO inspection (order_id, employee_id, inspected_on,
                        conclusion)
VALUES (1, 1, '2026-09-19', 'Склейка завершена');
-- Чужая работа (сотрудник № 2) не изменяется: UPDATE 0.
UPDATE order_work SET status = 'done'
WHERE order_id = 2 AND line_no = 1;
-- Осмотр от имени другого сотрудника отклоняется.
INSERT INTO inspection (order_id, employee_id, inspected_on,
                        conclusion)
VALUES (2, 2, '2026-09-19', 'Попытка подписи чужим именем');
-- Запрещено: контакты, суммы, журнал, секреты.
SELECT full_name, phone FROM customer;
SELECT agreed_price_kopecks FROM order_work;
SELECT customer_id FROM instrument;
SELECT * FROM payment;
SELECT * FROM v_reception_balances;
SELECT count(*) FROM change_log;
SELECT count(*) FROM access_secret;
UPDATE order_work SET agreed_price_kopecks = 0
WHERE order_id = 1 AND line_no = 1;
