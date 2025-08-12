-- Return single active event (if any)
SELECT sympla_id, event_name, event_start_date, event_end_date,
       city, state, place_name, event_link, detail
FROM tbl_events
WHERE is_active = TRUE
LIMIT 1;
