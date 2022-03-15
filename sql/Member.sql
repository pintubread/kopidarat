DELETE FROM member;

INSERT INTO member
SELECT u.email
FROM users u
WHERE u.type = 'member';