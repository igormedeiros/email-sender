-- Source: n8n/_sympla_____Set_Event_Info.json -> "Search for Event"
-- Variables: $('Set Event').item.json.eventId
SELECT *
FROM tbl_events
WHERE sympla_id = '{{ $('Set Event').item.json.eventId }}';
