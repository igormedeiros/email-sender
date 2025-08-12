-- Source: n8n/_sympla_____Set_Event_Info.json -> "update event info"
-- Variables: $('Set Event').item.json.eventId and fields from Complete Event Details / HTTP Request
UPDATE tbl_events
SET
    is_active = TRUE, 
    event_name = '{{ $('Complete Event Details').item.json.eventName }}',
    detail = '{{ $('Complete Event Details').item.json.detail }}',
    event_start_date = '{{ $('HTTP Request GET Event Info').item.json.data.start_date }}',
    event_end_date = '{{ $('HTTP Request GET Event Info').item.json.data.end_date }}',
    city = '{{ $('Complete Event Details').item.json.city }}',
    state = '{{ $('Complete Event Details').item.json.state }}',
    place_name = '{{ $('Complete Event Details').item.json.placeName }}',
    event_link = '{{ $('Complete Event Details').item.json.event_link }}'
WHERE sympla_id = '{{ $('Set Event').item.json.eventId }}';
