-- Ключ = SHA-256 от индивидуального пароля (переменная psql).
SELECT encode(digest(:'master_password', 'sha256'), 'hex')
    AS key \gset
-- Суперпользователь видит только шифртекст.
SELECT secret_id AS id, consumer_class,
       substr(encode(secret_value, 'hex'), 1, 32) || '…'
           AS secret_value_hex
FROM access_secret ORDER BY secret_id;
-- Расшифровка с неверным паролем.
SELECT pgp_sym_decrypt(secret_value,
           encode(digest(:'wrong_password', 'sha256'), 'hex'))
FROM access_secret WHERE secret_id = 1;
-- Расшифровка с индивидуальным паролем.
SELECT secret_id AS id,
       pgp_sym_decrypt(secret_name, :'key') AS name,
       pgp_sym_decrypt(secret_value, :'key') AS value
FROM access_secret ORDER BY secret_id;
