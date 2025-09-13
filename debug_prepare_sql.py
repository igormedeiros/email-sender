"""Debug script to understand the _prepare_sql function."""

import re

_DOLLAR_PARAM_PATTERN = re.compile(r"\$([1-9][0-9]*)")
_N8N_EMAIL_PATTERN = re.compile(r"\{\{\s*\$json\.query\.email\s*\}\}")

sql_text = "SELECT * FROM test_table WHERE id = $1 AND email = {{ $json.query.email }} AND name = $2;"

print("Original SQL:")
print(sql_text)

print("\nFinding $n placeholders:")
occurrences = [int(m.group(1)) for m in _DOLLAR_PARAM_PATTERN.finditer(sql_text)]
print(f"Occurrences: {occurrences}")

print("\nFinding n8n placeholders:")
n8n_matches = list(_N8N_EMAIL_PATTERN.finditer(sql_text))
n8n_count = len(n8n_matches)
print(f"N8n count: {n8n_count}")
for match in n8n_matches:
    print(f"  Match: {match.group()} at position {match.span()}")

print("\nReplacing with %s:")
sql_text_percent = _N8N_EMAIL_PATTERN.sub("%s", sql_text)
print("After replacing n8n:", sql_text_percent)

sql_text_percent = _DOLLAR_PARAM_PATTERN.sub("%s", sql_text_percent)
print("After replacing $n:", sql_text_percent)

params = ["123", "test@example.com", "test_name"]
print(f"\nParams: {params}")

# Expand parameters according to the occurrences
original_params = tuple(params)
expanded_params = []
if occurrences:
    for idx in occurrences:
        param_pos = idx - 1
        if param_pos < 0 or param_pos >= len(original_params):
            raise ValueError(
                f"SQL expects parameter ${idx} but only {len(original_params)} were provided"
            )
        expanded_params.append(original_params[param_pos])

print(f"Expanded params for $n placeholders: {expanded_params}")

# Append n8n inline parameters if present (assume they are provided at the end of the params list)
if n8n_count > 0:
    # For simplicity, take additional params from the tail beyond the max index in occurrences
    max_idx = max(occurrences) if occurrences else 0
    extra_params = original_params[max_idx: max_idx + n8n_count]
    print(f"Max idx: {max_idx}")
    print(f"Extra params: {extra_params}")
    if len(extra_params) != n8n_count:
        raise ValueError(
            f"SQL expects {n8n_count} inline parameters from n8n template but only {len(extra_params)} were provided"
        )
    expanded_params.extend(extra_params)

print(f"Final expanded params: {tuple(expanded_params)}")