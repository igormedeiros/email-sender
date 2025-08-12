-- Parameterized event insert (activates new)
-- $1: sympla_id text
-- $2: event_name text
-- $3: event_start_date text
-- $4: event_end_date text
-- $5: city text
-- $6: state text
-- $7: place_name text
-- $8: event_link text
-- $9: detail text
INSERT INTO tbl_events (
    sympla_id, event_name, event_start_date, event_end_date,
    city, state, place_name, is_active, event_link, detail
) VALUES (
    $1, $2, $3, $4,
    $5, $6, $7, TRUE, $8, $9
);
