SELECT id 
FROM tbl_messages 
WHERE id = $1 
LIMIT 1;