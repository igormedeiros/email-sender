-- Get last successful contact id for a state key
-- $1: state_key text
SELECT state_value
FROM tbl_send_state
WHERE state_key = $1
LIMIT 1;
