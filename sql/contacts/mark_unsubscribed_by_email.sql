-- Parameterized: $1 is the contact email
UPDATE tbl_contacts
SET
    unsubscribed = TRUE,
    updated_at = NOW()
WHERE LOWER(TRIM(email)) = LOWER(TRIM($1));
