-- Связи 1:M из ЛР1: внешний ключ на стороне «многие».
-- Удаление используемой родительской записи запрещено.
BEGIN;

ALTER TABLE instrument
    ADD CONSTRAINT instrument_customer_fk
        FOREIGN KEY (customer_id) REFERENCES customer
        ON DELETE RESTRICT,
    ADD CONSTRAINT instrument_type_fk
        FOREIGN KEY (type_id) REFERENCES instrument_type
        ON DELETE RESTRICT;

ALTER TABLE restoration_order
    ADD CONSTRAINT order_instrument_fk
        FOREIGN KEY (instrument_id) REFERENCES instrument
        ON DELETE RESTRICT;

ALTER TABLE order_work
    ADD CONSTRAINT work_order_fk
        FOREIGN KEY (order_id) REFERENCES restoration_order
        ON DELETE RESTRICT,
    ADD CONSTRAINT work_service_fk
        FOREIGN KEY (service_id) REFERENCES service
        ON DELETE RESTRICT,
    ADD CONSTRAINT work_employee_fk
        FOREIGN KEY (employee_id) REFERENCES employee
        ON DELETE RESTRICT;

ALTER TABLE inspection
    ADD CONSTRAINT inspection_order_fk
        FOREIGN KEY (order_id) REFERENCES restoration_order
        ON DELETE RESTRICT,
    ADD CONSTRAINT inspection_employee_fk
        FOREIGN KEY (employee_id) REFERENCES employee
        ON DELETE RESTRICT;

ALTER TABLE payment
    ADD CONSTRAINT payment_order_fk
        FOREIGN KEY (order_id) REFERENCES restoration_order
        ON DELETE RESTRICT;

COMMIT;
