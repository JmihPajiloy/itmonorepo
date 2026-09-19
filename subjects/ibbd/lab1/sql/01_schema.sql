PRAGMA foreign_keys = ON;
BEGIN;
CREATE TABLE customer (
 customer_id INTEGER PRIMARY KEY, full_name TEXT NOT NULL CHECK(length(trim(full_name))>0),
 phone TEXT NOT NULL, email TEXT
) STRICT;
CREATE TABLE instrument_type (
 type_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, description TEXT NOT NULL
) STRICT;
CREATE TABLE instrument (
 instrument_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customer ON DELETE RESTRICT,
 type_id INTEGER NOT NULL REFERENCES instrument_type ON DELETE RESTRICT,
 inventory_no TEXT NOT NULL UNIQUE, name TEXT NOT NULL, maker TEXT, serial_no TEXT
) STRICT;
CREATE TABLE employee (
 employee_id INTEGER PRIMARY KEY, full_name TEXT NOT NULL, specialization TEXT NOT NULL, work_email TEXT NOT NULL UNIQUE
) STRICT;
CREATE TABLE restoration_order (
 order_id INTEGER PRIMARY KEY, instrument_id INTEGER NOT NULL REFERENCES instrument ON DELETE RESTRICT,
 accepted_on TEXT NOT NULL CHECK(date(accepted_on) IS NOT NULL AND date(accepted_on)=accepted_on),
 due_on TEXT NOT NULL CHECK(date(due_on) IS NOT NULL AND date(due_on)=due_on AND due_on>=accepted_on),
 status TEXT NOT NULL CHECK(status IN ('accepted','in_progress','ready','closed','cancelled')),
 complaint TEXT NOT NULL
) STRICT;
CREATE UNIQUE INDEX one_active_order_per_instrument ON restoration_order(instrument_id)
 WHERE status IN ('accepted','in_progress','ready');
CREATE TABLE service (
 service_id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
 description TEXT NOT NULL, base_price_kopecks INTEGER NOT NULL CHECK(base_price_kopecks>=0)
) STRICT;
CREATE TABLE order_work (
 order_id INTEGER NOT NULL REFERENCES restoration_order ON DELETE RESTRICT,
 line_no INTEGER NOT NULL CHECK(line_no>0),
 service_id INTEGER NOT NULL REFERENCES service ON DELETE RESTRICT,
 employee_id INTEGER NOT NULL REFERENCES employee ON DELETE RESTRICT,
 agreed_price_kopecks INTEGER NOT NULL CHECK(agreed_price_kopecks>=0),
 status TEXT NOT NULL CHECK(status IN ('planned','in_progress','done','cancelled')),
 PRIMARY KEY(order_id,line_no)
) STRICT;
CREATE TABLE inspection (
 inspection_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES restoration_order ON DELETE RESTRICT,
 employee_id INTEGER NOT NULL REFERENCES employee ON DELETE RESTRICT,
 inspected_on TEXT NOT NULL CHECK(date(inspected_on) IS NOT NULL AND date(inspected_on)=inspected_on),
 conclusion TEXT NOT NULL CHECK(length(trim(conclusion))>0)
) STRICT;
CREATE TABLE payment (
 payment_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL REFERENCES restoration_order ON DELETE RESTRICT,
 paid_on TEXT NOT NULL CHECK(date(paid_on) IS NOT NULL AND date(paid_on)=paid_on),
 amount_kopecks INTEGER NOT NULL CHECK(amount_kopecks>0),
 method TEXT NOT NULL CHECK(method IN ('cash','card','transfer')),
 receipt_no TEXT NOT NULL UNIQUE
) STRICT;
CREATE INDEX order_instrument_idx ON restoration_order(instrument_id);
CREATE INDEX instrument_customer_idx ON instrument(customer_id);
CREATE INDEX instrument_type_idx ON instrument(type_id);
CREATE INDEX work_service_idx ON order_work(service_id);
CREATE INDEX work_employee_idx ON order_work(employee_id);
CREATE INDEX inspection_order_idx ON inspection(order_id);
CREATE INDEX inspection_employee_idx ON inspection(employee_id);
CREATE INDEX payment_order_idx ON payment(order_id);
COMMIT;
