-- Приёмщик: оплаты по типам инструментов.
SELECT t.name AS instrument_type,
       count(DISTINCT i.customer_id) AS customers,
       count(DISTINCT o.order_id) AS orders,
       count(p.payment_id) AS payments,
       round(coalesce(sum(p.amount_kopecks), 0) / 100.0, 2)
           AS paid_rub,
       max(p.paid_on) AS last_paid_on
FROM instrument_type t
JOIN instrument i ON i.type_id = t.type_id
JOIN restoration_order o
     ON o.instrument_id = i.instrument_id
LEFT JOIN payment p ON p.order_id = o.order_id
     AND (%(method)s = '' OR p.method = %(method)s)
WHERE %(ostatus)s = '' OR o.status = %(ostatus)s
GROUP BY t.name
