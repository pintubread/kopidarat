DELETE FROM administrator;

INSERT INTO administrator
SELECT u.email
FROM users u
WHERE u.type = 'administrator';
