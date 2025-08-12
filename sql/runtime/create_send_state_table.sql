-- Create simple state table to track last successful contact
CREATE TABLE IF NOT EXISTS tbl_send_state (
    state_key text PRIMARY KEY,
    state_value text,
    updated_at timestamptz DEFAULT now()
);
