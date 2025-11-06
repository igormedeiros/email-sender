-- Check if contact has exclusion tags or unsubscribed status
-- $1: integer contact_id
SELECT 
    tc.id, 
    tc.unsubscribed, 
    tc.is_buyer,
    array_agg(DISTINCT tg.tag_name) as excluded_tags
FROM tbl_contacts tc
LEFT JOIN tbl_contact_tags ctg ON tc.id = ctg.contact_id
LEFT JOIN tbl_tags tg ON ctg.tag_id = tg.id
WHERE tc.id = $1
GROUP BY tc.id, tc.unsubscribed, tc.is_buyer
