"""Test the actual _prepare_sql function to see what it produces."""

import sys
sys.path.insert(0, '/home/igormedeiros/projects/treineinsite/treineinsite/src')

from email_sender.db import _prepare_sql

sql_text = "SELECT * FROM test_table WHERE id = $1 AND email = {{ $json.query.email }} AND name = $2;"
params = ["123", "test_name", "test@example.com"]

prepared_sql, expanded_params = _prepare_sql(sql_text, params)

print(f"Prepared SQL: {prepared_sql}")
print(f"Expanded params: {expanded_params}")

# What we expect based on the order of %s in the SQL:
# First %s -> $1 -> params[0] = "123"
# Second %s -> {{ $json.query.email }} -> params[2] = "test@example.com"  
# Third %s -> $2 -> params[1] = "test_name"
# Expected: ("123", "test@example.com", "test_name")

print(f"Expected: ('123', 'test@example.com', 'test_name')")
print(f"Match: {expanded_params == ('123', 'test@example.com', 'test_name')}")