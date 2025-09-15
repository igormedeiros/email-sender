-- Select event by internal ID
-- $1: event_id (int)
SELECT id, sympla_id, event_name, event_start_date, event_end_date,
       city, state, place_name, event_link, detail, is_active
FROM tbl_events
WHERE id = $1
LIMIT 1;