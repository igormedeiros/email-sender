-- Source: n8n/_email______Clicou_no_Link_Webhook_Evento_Atual.json -> "atualiza o lead score"
-- Variables: $('Webhook').item.json.query.contact_id
INSERT INTO tbl_lead_scores (contact_id, score, last_updated_at)
VALUES (
    '{{ $('Webhook').item.json.query.contact_id }}',
    3,
    NOW()
)
ON CONFLICT (contact_id) DO UPDATE SET
    score = tbl_lead_scores.score + EXCLUDED.score,
    last_updated_at = NOW();
