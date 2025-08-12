-- Source: n8n/_sympla_____Set_Event_Info.json -> "Set All Events as Inative"
UPDATE tbl_events
SET is_active = FALSE
WHERE is_active = TRUE;
