-- ==============================================================================
-- CORREÇÃO: Marcar contatos com bounce que receberam email
-- ==============================================================================
-- Estes 205 contatos tiveram um bug e receberam emails apesar de terem bounce
-- Vamos registrar isso com uma tag 'alert_sent_with_bounce'

-- Passo 1: Criar a tag se não existir
INSERT INTO tbl_tags (tag_name)
VALUES ('alert_sent_with_bounce')
ON CONFLICT (tag_name) DO NOTHING;

-- Passo 2: Obter ID da tag
SELECT id INTO tag_id FROM tbl_tags WHERE tag_name = 'alert_sent_with_bounce';

-- Passo 3: Adicionar a tag aos contatos que receberam emails com bounce
INSERT INTO tbl_contact_tags (contact_id, tag_id)
SELECT DISTINCT ml.contact_id, (SELECT id FROM tbl_tags WHERE tag_name = 'alert_sent_with_bounce')
FROM tbl_message_logs ml
INNER JOIN tbl_contacts tc ON ml.contact_id = tc.id
INNER JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
WHERE ml.event_type = 'sent' AND LOWER(tg.tag_name) IN ('bounce', 'bouncy')
ON CONFLICT (contact_id, tag_id) DO NOTHING;

-- Passo 4: Verificar resultado
SELECT 
    '✅ Contatos marcados com alert_sent_with_bounce' as status,
    COUNT(*) as count
FROM tbl_contact_tags ctg
INNER JOIN tbl_tags tg ON ctg.tag_id = tg.id
WHERE tg.tag_name = 'alert_sent_with_bounce';

-- ==============================================================================
-- INFORMAÇÕES PARA O LOG
-- ==============================================================================

SELECT 
    'RESUMO DA CORREÇÃO' as item,
    '205 contatos com bounce receberam emails por engano' as description,
    'Estes contatos foram marcados com tag: alert_sent_with_bounce' as action;
