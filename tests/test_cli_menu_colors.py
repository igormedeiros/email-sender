from email_sender.cli import get_menu_style, Style


def test_prompt_toolkit_style_uses_valid_tokens():
    # Style factory should return a valid style without errors
    style = get_menu_style()
    assert style is not None
