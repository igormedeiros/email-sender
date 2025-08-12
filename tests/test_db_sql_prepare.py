from email_sender.db import _prepare_sql


def test_prepare_sql_rewrites_placeholders_and_expands_params():
    sql = """
    -- comment $9
    SELECT * FROM tbl WHERE id=$1 AND status=$2 OR owner=$1;
    /* block $3 */
    """.strip()
    text, params = _prepare_sql(sql, (10, 'A'))
    assert text.count('%s') == 3
    assert params == (10, 'A', 10)


def test_prepare_sql_handles_n8n_inline_placeholders():
    sql = "SELECT * FROM tbl WHERE email={{ $json.query.email }} OR other=$1"
    # Provide param for $1, then inline email param
    text, params = _prepare_sql(sql, (123, "foo@bar"))
    assert text == "SELECT * FROM tbl WHERE email=%s OR other=%s"
    assert params == (123, "foo@bar")
