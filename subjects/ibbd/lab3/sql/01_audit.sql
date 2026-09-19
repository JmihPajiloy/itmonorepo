-- Журнал изменений основных таблиц.
BEGIN;

CREATE TABLE change_log (
    log_id     bigint
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    changed_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    db_role    text NOT NULL,
    client     inet,
    tx_id      bigint NOT NULL,
    operation  char(1) NOT NULL
        CHECK (operation IN ('I', 'U', 'D')),
    table_name text NOT NULL,
    row_key    jsonb NOT NULL,
    old_row    jsonb,
    new_row    jsonb
);

CREATE INDEX change_log_table_key_idx
    ON change_log (table_name, row_key);
CREATE INDEX change_log_changed_at_idx
    ON change_log (changed_at);

-- SECURITY DEFINER: запись в журнал выполняется от владельца,
-- поэтому прикладным ролям не нужны права на change_log.
-- session_user — роль, под которой вошёл клиент; current_user
-- внутри функции равен владельцу и для журнала не подходит.
CREATE FUNCTION log_change() RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    src   jsonb := to_jsonb(CASE WHEN TG_OP = 'DELETE'
                                 THEN OLD ELSE NEW END);
    k     jsonb := '{}';
    col   text;
BEGIN
    -- Аргументы триггера — столбцы первичного ключа.
    FOREACH col IN ARRAY TG_ARGV LOOP
        k := k || jsonb_build_object(col, src -> col);
    END LOOP;

    INSERT INTO change_log (db_role, client, tx_id,
        operation, table_name, row_key, old_row, new_row)
    VALUES (session_user, inet_client_addr(), txid_current(),
        left(TG_OP, 1), TG_TABLE_NAME, k,
        CASE WHEN TG_OP <> 'INSERT' THEN to_jsonb(OLD) END,
        CASE WHEN TG_OP <> 'DELETE' THEN to_jsonb(NEW) END);
    RETURN NULL;
END;
$$;

REVOKE ALL ON FUNCTION log_change() FROM PUBLIC;

DO $$
DECLARE
    t record;
BEGIN
    FOR t IN SELECT * FROM (VALUES
        ('customer', 'customer_id'),
        ('instrument_type', 'type_id'),
        ('instrument', 'instrument_id'),
        ('employee', 'employee_id'),
        ('restoration_order', 'order_id'),
        ('service', 'service_id'),
        ('order_work', 'order_id, line_no'),
        ('inspection', 'inspection_id'),
        ('payment', 'payment_id')
    ) AS v(tab, pk) LOOP
        EXECUTE format(
            'CREATE TRIGGER %I '
            'AFTER INSERT OR UPDATE OR DELETE ON %I '
            'FOR EACH ROW EXECUTE FUNCTION log_change(%s)',
            t.tab || '_log', t.tab,
            (SELECT string_agg(quote_literal(btrim(c)), ', ')
             FROM unnest(string_to_array(t.pk, ',')) AS c));
    END LOOP;
END $$;

-- Журнал доступен только суперпользователю.
REVOKE ALL ON change_log FROM PUBLIC;

COMMIT;
