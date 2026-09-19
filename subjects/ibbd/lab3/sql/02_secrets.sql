-- Таблица секретов классов пользователей, шифрование AES-256.
-- Запуск: psql -v master_password=... -f 02_secrets.sql
-- Ключ = SHA-256 от индивидуального пароля; в БД ни пароль,
-- ни ключ не сохраняются.
BEGIN;

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE access_secret (
    secret_id      integer
        GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    consumer_class text NOT NULL,
    secret_name    bytea NOT NULL,
    secret_value   bytea NOT NULL
);

REVOKE ALL ON access_secret FROM PUBLIC;

-- Ключ вычисляется только на время выполнения этого скрипта.
SELECT encode(digest(:'master_password', 'sha256'), 'hex')
    AS k \gset

INSERT INTO access_secret (consumer_class, secret_name,
                           secret_value)
SELECT class,
       pgp_sym_encrypt(name, :'k', 'cipher-algo=aes256'),
       pgp_sym_encrypt(value, :'k', 'cipher-algo=aes256')
FROM (VALUES
    ('reception', 'Токен платёжного терминала',
     'term_7Qm2-demo-4hXv9Lp'),
    ('reception', 'Ключ SMS-шлюза уведомлений',
     'sms_K3fd8-demo-Wq1zR0'),
    ('restorer', 'Доступ к каталогу поставщика',
     'cat_P9sd1-demo-Yt6uB2'),
    ('restorer', 'Учётная запись станка ЧПУ',
     'cnc_H5gn4-demo-Ze7kM3')
) AS v(class, name, value);

\unset k
COMMIT;
