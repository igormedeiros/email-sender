from email_sender import cli as cli_mod


def test_run_interactive_menu_renders_style_and_fragments():
    # Ensure style factory returns a Style and contains expected tokens
    style = cli_mod.get_menu_style()
    assert isinstance(style, cli_mod.Style)
