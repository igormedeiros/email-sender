-- Parameterized event update by sympla_id
-- $1: sympla_id text
-- $2: event_name text
-- $3: event_start_date text
-- $4: event_end_date text
-- $5: city text
-- $6: state text
-- $7: place_name text
-- $8: event_link text
-- $9: detail text
UPDATE tbl_events
SET
    is_active = TRUE,
    event_name = $2,
    event_start_date = $3,
    event_end_date = $4,
    city = $5,
    state = $6,
    place_name = $7,
    event_link = $8,
    detail = $9
WHERE sympla_id = $1;
