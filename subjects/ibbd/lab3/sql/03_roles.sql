-- Разграничение доступа: групповые роли классов потребителей
-- из ЛР1 и индивидуальные учётные записи.
-- Пароли передаются переменными psql: reception_password,
-- restorer_password; сервер хранит только хэш SCRAM-SHA-256.
BEGIN;

-- 1. Убрать права, выдаваемые PUBLIC по умолчанию.
REVOKE CONNECT, TEMPORARY ON DATABASE workshop FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;

-- 2. Групповые роли (без входа).
CREATE ROLE reception_role NOLOGIN NOSUPERUSER NOCREATEDB
    NOCREATEROLE NOINHERIT;
CREATE ROLE restorer_role NOLOGIN NOSUPERUSER NOCREATEDB
    NOCREATEROLE NOINHERIT;
GRANT CONNECT ON DATABASE workshop
    TO reception_role, restorer_role;
GRANT USAGE ON SCHEMA public TO reception_role, restorer_role;

-- 3. Приёмщик: заказчики, инструменты, заказы, оплаты.
--    Удаление не разрешено: ошибочные записи исправляются.
GRANT SELECT, INSERT, UPDATE
    ON customer, instrument, restoration_order, payment
    TO reception_role;
GRANT SELECT ON instrument_type, service TO reception_role;
GRANT SELECT ON v_reception_orders, v_reception_balances
    TO reception_role;

-- 4. Реставратор: без контактов заказчика и денежных сумм.
GRANT SELECT ON v_restorer_tasks, v_restorer_inspections,
    instrument_type TO restorer_role;
GRANT SELECT (service_id, name, description)
    ON service TO restorer_role;
GRANT SELECT (employee_id, full_name, specialization)
    ON employee TO restorer_role;
GRANT SELECT (instrument_id, type_id, inventory_no, name,
              maker, serial_no)
    ON instrument TO restorer_role;
GRANT SELECT (order_id, instrument_id, accepted_on, due_on,
              status, complaint)
    ON restoration_order TO restorer_role;
GRANT SELECT (order_id, line_no, service_id, employee_id,
              status),
      UPDATE (status)
    ON order_work TO restorer_role;
GRANT SELECT, INSERT (order_id, employee_id, inspected_on,
                      conclusion)
    ON inspection TO restorer_role;

-- 5. Сопоставление учётной записи и сотрудника. Внутри
--    SECURITY DEFINER current_user равен владельцу функции,
--    поэтому используется session_user — роль входа.
ALTER TABLE employee ADD COLUMN db_login text UNIQUE;

CREATE FUNCTION current_employee_id() RETURNS integer
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$ SELECT employee_id FROM employee
      WHERE db_login = session_user $$;
REVOKE ALL ON FUNCTION current_employee_id() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION current_employee_id()
    TO restorer_role;

-- 6. Реставратор меняет статус только своих работ и
--    регистрирует осмотры только от своего имени.
ALTER TABLE order_work ENABLE ROW LEVEL SECURITY;
CREATE POLICY work_read ON order_work FOR SELECT
    TO restorer_role USING (true);
CREATE POLICY work_own_update ON order_work FOR UPDATE
    TO restorer_role
    USING (employee_id = current_employee_id())
    WITH CHECK (employee_id = current_employee_id());

ALTER TABLE inspection ENABLE ROW LEVEL SECURITY;
CREATE POLICY inspection_read ON inspection FOR SELECT
    TO restorer_role USING (true);
CREATE POLICY inspection_own_insert ON inspection FOR INSERT
    TO restorer_role
    WITH CHECK (employee_id = current_employee_id());

-- 7. Индивидуальные учётные записи.
CREATE ROLE reception_orlova LOGIN
    PASSWORD :'reception_password'
    INHERIT IN ROLE reception_role;
CREATE ROLE restorer_smirnov LOGIN
    PASSWORD :'restorer_password'
    INHERIT IN ROLE restorer_role;
CREATE ROLE restorer_volkova LOGIN
    PASSWORD :'restorer_password'
    INHERIT IN ROLE restorer_role;

UPDATE employee SET db_login = 'restorer_smirnov'
WHERE employee_id = 1;
UPDATE employee SET db_login = 'restorer_volkova'
WHERE employee_id = 2;

COMMIT;
