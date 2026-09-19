-- Модификация структуры: дата фактической выдачи инструмента.
-- Только для закрытого заказа и не раньше даты приёма.
BEGIN;

ALTER TABLE restoration_order
    ADD COLUMN closed_on date,
    ADD CONSTRAINT order_closed_on_check CHECK (
        (status = 'closed' AND closed_on IS NOT NULL
                           AND closed_on >= accepted_on)
        OR (status <> 'closed' AND closed_on IS NULL)
    );

COMMENT ON COLUMN restoration_order.closed_on
    IS 'Дата выдачи инструмента заказчику';

COMMIT;
