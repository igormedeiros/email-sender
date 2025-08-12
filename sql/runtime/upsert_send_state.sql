-- Upsert last successful contact id for a state key
-- $1: state_key text
-- $2: state_value text
INSERT INTO tbl_send_state (state_key, state_value)
VALUES ($1, $2)
ON CONFLICT (state_key) DO UPDATE SET state_value = EXCLUDED.state_value, updated_at = now();
