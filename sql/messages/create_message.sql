-- Source: n8n/_email_______Sending_Emails_PROD (1).json -> "Create New Message"
-- Variables: $json.output (subject), $('Get Actual Event Info').item.json.id (event_id)
INSERT INTO tbl_messages (subject, internal_name, event_id)
VALUES (
    '{{ $json.output }}',
    CONCAT(
        '[{{$node["Get Actual Event Info"].json.state}} ',
        '{{$node["MessageInfo"].json.formattedMonthNumber}}-',
        '{{$node["MessageInfo"].json.formattedFullYear}}]',
        ' Envio ',
        (SELECT COALESCE(MAX(id), 0) + 1 FROM tbl_messages)
    ),
    '{{ $('Get Actual Event Info').item.json.id }}'
)
RETURNING id, '{{ $json.output }}' AS subject;
