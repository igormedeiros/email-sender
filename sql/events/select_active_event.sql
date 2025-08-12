-- Source: n8n/_Sympla____Get_Event_Info.json -> "Load Event Info"
SELECT *
FROM tbl_events
WHERE is_active = TRUE;
