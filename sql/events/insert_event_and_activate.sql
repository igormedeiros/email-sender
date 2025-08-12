-- Source: n8n/_sympla_____Set_Event_Info.json -> "Insert and Activate New Event"
-- Variables: $('Set Event').item.json.eventId, fields from Complete Event Details and HTTP Request
INSERT INTO tbl_events (
    sympla_id,
    event_name,
    event_start_date,
    event_end_date,
    city,
    state,
    place_name,
    is_active,
    detail
)
VALUES (
    '{{ $('Set Event').item.json.eventId }}',
    '{{ $('Complete Event Details').item.json.eventName }}',
    '{{ $('HTTP Request GET Event Info').item.json.data.start_date }}', 
    '{{ $('HTTP Request GET Event Info').item.json.data.end_date }}', 
    '{{ $('Complete Event Details').item.json.city }}',
    '{{ $('Complete Event Details').item.json.state }}',
    '{{ $('Complete Event Details').item.json.placeName }}',
    TRUE,
    '{{ $('Complete Event Details').item.json.detail }}'
);
