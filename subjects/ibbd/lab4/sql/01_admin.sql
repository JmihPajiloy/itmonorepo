-- Роль администратора приложения и регистрация
-- пользователей. Пароль передаётся переменной psql
-- admin_password; сервер хранит только хэш SCRAM-SHA-256.
BEGIN;

-- 1. Администратор: все таблицы и представления,
--    чтение журнала и шифртекста секретов. Не
--    суперпользователь: RLS и права по-прежнему действуют.
CREATE ROLE admin_role NOLOGIN NOSUPERUSER NOCREATEDB
    NOCREATEROLE NOINHERIT;
GRANT CONNECT ON DATABASE workshop TO admin_role;
GRANT USAGE ON SCHEMA public TO admin_role;
GRANT SELECT, INSERT, UPDATE, DELETE
    ON customer, instrument_type, instrument, employee,
       restoration_order, service, order_work,
       inspection, payment
    TO admin_role;
GRANT SELECT ON v_reception_orders, v_reception_balances,
    v_restorer_tasks, v_restorer_inspections
    TO admin_role;
-- Журнал и секреты — только чтение: подделать журнал
-- или заменить шифртекст администратор не может.
GRANT SELECT ON change_log, access_secret TO admin_role;

-- На order_work и inspection включён RLS из ЛР3;
-- без политики администратор не увидит ни одной строки.
CREATE POLICY admin_all ON order_work TO admin_role
    USING (true) WITH CHECK (true);
CREATE POLICY admin_all ON inspection TO admin_role
    USING (true) WITH CHECK (true);

-- 2. Регистрация новых пользователей существующих
--    ролей. Приложение передаёт готовый SCRAM-верификатор,
--    поэтому пароль не попадает на сервер в открытом виде.
CREATE FUNCTION app_register_user(
    p_login text, p_group text, p_verifier text,
    p_employee_id integer DEFAULT NULL)
RETURNS void
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    IF p_login !~ '^[a-z][a-z0-9_]{2,39}$'
       OR p_login LIKE 'pg\_%' THEN
        RAISE EXCEPTION 'недопустимое имя: %', p_login;
    END IF;
    IF p_group NOT IN ('reception_role',
                       'restorer_role') THEN
        RAISE EXCEPTION 'недопустимая роль: %', p_group;
    END IF;
    IF p_verifier !~ '^SCRAM-SHA-256\$4096:' THEN
        RAISE EXCEPTION 'ожидается SCRAM-верификатор';
    END IF;
    IF EXISTS (SELECT FROM pg_roles
               WHERE rolname = p_login) THEN
        RAISE EXCEPTION 'роль % уже существует', p_login;
    END IF;
    EXECUTE format(
        'CREATE ROLE %I LOGIN INHERIT NOSUPERUSER '
        'NOCREATEDB NOCREATEROLE PASSWORD %L IN ROLE %I',
        p_login, p_verifier, p_group);
    EXECUTE format('COMMENT ON ROLE %I IS %L',
        p_login, 'ibbd-lab4: registered');
    IF p_group = 'restorer_role'
       AND p_employee_id IS NOT NULL THEN
        UPDATE employee SET db_login = p_login
        WHERE employee_id = p_employee_id
          AND db_login IS NULL;
        IF NOT FOUND THEN
            RAISE EXCEPTION 'сотрудник % не найден '
                'или уже связан', p_employee_id;
        END IF;
    END IF;
END;
$$;
REVOKE ALL ON FUNCTION
    app_register_user(text, text, text, integer) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION
    app_register_user(text, text, text, integer)
    TO admin_role;

-- 3. Учётная запись администратора.
CREATE ROLE workshop_admin LOGIN
    PASSWORD :'admin_password'
    INHERIT IN ROLE admin_role;
COMMENT ON ROLE workshop_admin IS 'ibbd-lab4: admin';

COMMIT;
