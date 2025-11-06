-- Normalize existing tag names
UPDATE tbl_tags SET tag_name = LOWER(TRIM(tag_name));

-- Add a check constraint to ensure new tags are normalized
ALTER TABLE tbl_tags ADD CONSTRAINT tag_name_is_lowercase_and_trimmed CHECK (tag_name = LOWER(TRIM(tag_name)));

-- Create an index on the normalized tag_name column
CREATE INDEX IF NOT EXISTS idx_tag_name ON tbl_tags (tag_name);
