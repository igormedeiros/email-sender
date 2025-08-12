from email_sender.utils import ui


def test_ui_functions_smoke():
    ui.print_banner("TREINEINSITE", subtitle="sub")
    ui.section("Sec")
    ui.info("info")
    ui.success("ok")
    ui.warn("warn")
    ui.error("err")
    prog = ui.progress("Working", total=10)
    task = prog.add_task("t", total=1)
    prog.update(task, advance=1)
    prog.stop()
