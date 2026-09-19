-- PostgreSQL не индексирует внешние ключи автоматически.
BEGIN;

-- Атрибуты соединений (внешние ключи).
CREATE INDEX instrument_customer_idx
    ON instrument (customer_id);
CREATE INDEX instrument_type_idx ON instrument (type_id);
CREATE INDEX order_instrument_idx
    ON restoration_order (instrument_id);
CREATE INDEX work_service_idx ON order_work (service_id);
CREATE INDEX work_employee_idx ON order_work (employee_id);
CREATE INDEX inspection_order_idx ON inspection (order_id);
CREATE INDEX inspection_employee_idx
    ON inspection (employee_id);
CREATE INDEX payment_order_idx ON payment (order_id);

-- Атрибуты поиска и фильтрации.
CREATE INDEX customer_full_name_idx ON customer (full_name);
CREATE INDEX customer_phone_idx ON customer (phone);
CREATE INDEX order_status_due_idx
    ON restoration_order (status, due_on);
CREATE INDEX work_status_idx ON order_work (status);
CREATE INDEX inspection_date_idx ON inspection (inspected_on);
CREATE INDEX payment_paid_on_idx ON payment (paid_on);

-- Правило ЛР1: не более одного активного заказа инструмента.
CREATE UNIQUE INDEX order_one_active_uq
    ON restoration_order (instrument_id)
    WHERE status IN ('accepted', 'in_progress', 'ready');

COMMIT;
