import os
from pathlib import Path
import shutil
from typing import Optional, List, Tuple
import socket
import psycopg
import yaml
import requests
import re
from urllib.parse import urlparse
import json

import typer
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style

from .controller_cli import app
from .utils.ui import (
    print_banner,
    build_treineinsite_ascii_art,
    info as ui_info,
    success as ui_success,
    warn as ui_warn,
    error as ui_error,
    section as ui_section,
    get_console,
)
from .config import Config
from .email_templating import TemplateProcessor
from datetime import datetime
from rich.table import Table
from rich.panel import Panel
from rich.text import Text


def main(
    env: Optional[str] = typer.Option(None, "--env", help="Ambiente de execução: test | production"),
):
    # Banner
    print_banner(build_treineinsite_ascii_art(), subtitle="Treineinsite • Email Sender CLI")

    # Estado inicial do ENVIRONMENT
    initial_env = (
        "production" if env in {"prod", "production"} else "test" if env in {"test"} else os.environ.get("ENVIRONMENT", "test")
    )

    selected_env = initial_env
    while True:
        selected_env, choice = _run_interactive_menu(selected_env)

        # Aplicar ENVIRONMENT conforme escolha final do menu
        os.environ["ENVIRONMENT"] = "prod" if selected_env == "production" else "test"

        if choice == "Enviar emails (toda a base)":
            from .controller_cli import send_emails
            config_file, content_file = _ensure_or_create_default_config()

            # Garantir remetente válido
            _ensure_valid_sender(config_file)

            # Verificação rápida de SMTP para evitar erro de DNS
            cfg = Config(str(config_file), str(content_file))
            smtp_host = (cfg.smtp_config.get("host") or "").strip()
            smtp_port = int(cfg.smtp_config.get("port", 587))
            if not smtp_host:
                typer.echo("\nℹ SMTP não configurado (sem host definido). Configure o SMTP em config/config.yaml antes de enviar.")
                continue
            try:
                socket.getaddrinfo(smtp_host, smtp_port)
            except socket.gaierror:
                typer.echo("\n❌ Não foi possível resolver o host SMTP configurado. Revise 'smtp.host' em config/config.yaml ou rode 'Auto-teste (diagnóstico geral)'.")
                continue

            try:
                # Chamada programática: passar valores primitivos (não OptionInfo)
                send_emails(
                    csv_file=None,
                    subject=None,
                    titulo=None,
                    config_file=str(config_file),
                    content_file=str(content_file),
                    skip_unsubscribed_sync=False,
                    mode=None,
                )
            except Exception as e:
                msg = str(e)
                if "Temporary failure in name resolution" in msg or "gaierror" in msg:
                    typer.echo("\n❌ Erro de DNS ao resolver o servidor SMTP. Configure 'smtp.host' em config/config.yaml com um host válido ou rode 'Auto-teste (diagnóstico geral)'.")
                else:
                    typer.echo(f"\n❌ Erro: {msg}")
            continue
        
        elif choice == "Auto-teste (diagnóstico geral)":
            _self_test()
            continue
        elif choice == "Gerar massa de teste (contatos: válido/unsub/bounce)":
            try:
                # Executar SQL de seed para criar 3 contatos com tags
                cfg_path, _ = _ensure_or_create_default_config()
                cfg = Config(str(cfg_path))
                from .db import Database
                with Database(cfg) as db:
                    db.execute("sql/fixtures/seed_contacts_exclusions.sql")
                ui_success("Massa de teste criada: igor.medeiros@gmail.com (test), unsub@test.com (unsubscribed), bounce@test.com (bounce)")
            except Exception as e:
                ui_error(f"Falha ao gerar massa de teste: {e}")
            continue
        elif choice == "Atualizar dados do evento Sympla":
            try:
                _update_event_from_sympla()
            except Exception as e:
                typer.echo(f"\n❌ Falha ao atualizar evento: {e}")
            continue
        elif choice == "Limpar base de emails (legado/local)":
            typer.echo("Limpeza de base (legado) não disponível em Postgres-first. Use rotinas SQL dedicadas.")
            continue
        elif choice == "Sair":
            break
        else:
            typer.echo("Opção inválida.")
            continue

    return 0


def get_menu_style() -> Style:
    """Returns a consistent style for selection menus using prompt_toolkit.

    This palette mirrors the Rich-based look used elsewhere (light blues/greys).
    """
    return Style.from_dict(
        {
            # Title and hints
            "title": "bold",
            "hint": "fg:#9aa0a6",  # dark grey

            # Environment line
            "env": "fg:#9aa0a6",  # dark grey
            "env_value": "bold ansibrightcyan",  # vibrant cyan

            # Frame/border
            "frame": "fg:#9aa0a6",

            # List items
            "item": "fg:#5f6368",  # grey
            "selected": "bold fg:#0b253a bg:#8ab4f8",  # dark text on light blue
        }
    )


def _run_interactive_menu(initial_env: str) -> Tuple[str, str]:
    """Renderiza um menu interativo com TAB para alternar ENVIRONMENT.

    - Up/Down: navega nas opções
    - Enter: seleciona
    - Tab: alterna test <-> production
    - Cinza escuro para itens; item selecionado em azul claro
    """
    menu_items: List[str] = [
        "Enviar emails (toda a base)",
        "Auto-teste (diagnóstico geral)",
        "Gerar massa de teste (contatos: válido/unsub/bounce)",
        "Atualizar dados do evento Sympla",
        "Limpar base de emails (legado/local)",
        "Sair",
    ]

    state = {
        "selected_index": 0,
        "environment": "production" if initial_env in {"prod", "production"} else "test",
        "result": None,  # type: ignore
    }

    style = get_menu_style()

    def _get_title_text():
        return [("class:title", "Selecione uma opção  "), ("class:hint", "(TAB alterna ENVIRONMENT)")]

    def _get_env_text():
        env = state["environment"]
        return [
            ("class:env", "ENVIRONMENT: "),
            ("class:env_value", env),
            ("class:env", "  (pressione TAB para alternar)")
        ]

    max_label_len = max(len(label) for label in menu_items)
    pad_left, pad_right = 2, 2

    def _get_menu_text():
        # Build a framed menu with unicode box drawing
        fragments = []
        inner_width = pad_left + 2 + max_label_len + pad_right  # 2 for selector + space
        top = "┌" + ("─" * inner_width) + "┐\n"
        bottom = "└" + ("─" * inner_width) + "┘\n"
        fragments.append(("class:frame", top))
        for idx, label in enumerate(menu_items):
            is_sel = idx == state["selected_index"]
            pointer = "❯" if is_sel else " "
            text = f"{' ' * pad_left}{pointer} {label.ljust(max_label_len)}{' ' * pad_right}"
            fragments.append(("class:frame", "│"))
            fragments.append((" ", ""))
            fragments.append((("class:selected" if is_sel else "class:item"), text))
            fragments.append(("class:frame", "│\n"))
        fragments.append(("class:frame", bottom))
        # Controls hint line
        hint = "↑/↓ Navega  •  Enter Seleciona  •  TAB Alterna ENV"
        hint_line = "  " + hint + "\n"
        fragments.append(("class:hint", hint_line))
        return fragments

    body_control = FormattedTextControl(_get_menu_text, focusable=True)
    body_window = Window(content=body_control, dont_extend_height=True)

    title_control = FormattedTextControl(_get_title_text)
    title_window = Window(height=1, content=title_control)

    env_control = FormattedTextControl(_get_env_text)
    env_window = Window(height=1, content=env_control)

    kb = KeyBindings()

    @kb.add("up")
    def _(event):  # type: ignore
        state["selected_index"] = (state["selected_index"] - 1) % len(menu_items)

    @kb.add("down")
    def _(event):  # type: ignore
        state["selected_index"] = (state["selected_index"] + 1) % len(menu_items)

    @kb.add("tab")
    def _(event):  # type: ignore
        state["environment"] = "production" if state["environment"] == "test" else "test"

    @kb.add("enter")
    def _(event):  # type: ignore
        state["result"] = (state["environment"], menu_items[state["selected_index"]])
        event.app.exit()

    @kb.add("escape")
    def _(event):  # type: ignore
        state["result"] = (state["environment"], "Sair")
        event.app.exit()

    root_container = HSplit([title_window, env_window, body_window])
    layout = Layout(root_container, focused_element=body_window)

    app_pt = Application(layout=layout, key_bindings=kb, mouse_support=False, style=style, full_screen=False)
    app_pt.run()

    env_value, selection = state["result"]  # type: ignore
    return env_value, selection


def _ensure_or_create_default_config() -> Tuple[Path, Path]:
    """Garante que arquivos config/config.yaml e config/email.yaml existam.

    Se não existirem, cria uma configuração mínima funcional e um template HTML de exemplo.
    Retorna as Paths absolutas dos dois arquivos.
    """
    cwd = Path.cwd()
    config_dir = cwd / "config"
    templates_dir = config_dir / "templates"
    data_dir = cwd / "data"
    config_dir.mkdir(parents=True, exist_ok=True)
    templates_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    config_path = config_dir / "config.yaml"
    email_content_path = config_dir / "email.yaml"

    if not config_path.exists():
        config_yaml = (
            "smtp:\n"
            "  host: \"\"\n"
            "  port: 587\n"
            "  username: \"\"\n"
            "  password: \"\"\n"
            "  use_tls: true\n"
            "  retry_attempts: 3\n"
            "  retry_delay: 5\n"
            "  send_timeout: 10\n"
            "email:\n"
            "  sender: \"\"\n"
            "  batch_size: 200\n"  # número de emails por lote antes de pausar
            "  csv_file: \"data/emails_geral.csv\"\n"
            "  test_recipient: \"\"\n"
            "  batch_delay: 5\n"  # pausa (segundos) entre lotes
            "  public_domain: \"mkt.treineinsite.com.br\"\n"
            "  unsubscribe_file: \"data/descadastros.csv\"\n"
            "  test_emails_file: \"data/test_emails.csv\"\n"
        )
        config_path.write_text(config_yaml, encoding="utf-8")

    target_template = templates_dir / "email.html"
    example_template = cwd / "config" / "templates" / "email.html.example"
    if not target_template.exists():
        try:
            if example_template.exists():
                shutil.copyfile(example_template, target_template)
            else:
                target_template.write_text(
                    """<!doctype html>\n<html><body><h1>{title}</h1><p>Olá {name},</p><p>Conteúdo de exemplo.</p></body></html>\n""",
                    encoding="utf-8",
                )
        except Exception:
            # Em último caso, garante um arquivo simples
            target_template.write_text(
                """<!doctype html>\n<html><body><h1>{title}</h1><p>Olá {name},</p></body></html>\n""",
                encoding="utf-8",
            )

    if not email_content_path.exists():
        email_yaml = (
            "email:\n"
            f"  template_path: \"{target_template.as_posix()}\"\n"
            "  subject: \"\"\n"
            "  variables:\n"
            "    title: \"\"\n"
            "    name: \"\"\n"
        )
        email_content_path.write_text(email_yaml, encoding="utf-8")

    # Criar .env com variáveis de Postgres se não existir
    env_path = cwd / ".env"
    if not env_path.exists():
        env_text = (
            "# Postgres connection settings\n"
            "PGHOST=\n"
            "PGPORT=5432\n"
            "PGUSER=\n"
            "PGPASSWORD=\n"
            "PGDATABASE=\n"
            "\n# Sympla\n"
            "SYMPLA_TOKEN=\n"
            "SYMPLA_BASE_URL=https://api.sympla.com.br/public/v4\n"
            "\n# SMTP\n"
            "SMTP_TEST_TIMEOUT=5\n"
            "\n# Outros\n"
            "ENVIRONMENT=test\n"
            "TEST_RECIPIENT=\n"
        )
        env_path.write_text(env_text, encoding="utf-8")

    return config_path.resolve(), email_content_path.resolve()



def _update_event_from_sympla() -> None:
    """Busca os 3 últimos eventos do Sympla, permite selecionar um e sincroniza YAML + Postgres.

    - Requer token da API do Sympla no header `S_token`
    - Token lido de `SYMPLA_TOKEN` no ambiente (.env) ou solicitado ao usuário
    - Atualiza `config/email.yaml` na seção `evento`
    - Desativa eventos antigos em `tbl_events` e ativa/insere o selecionado
    """
    # Carregar/config preparar caminhos
    config_file, content_file = _ensure_or_create_default_config()
    cfg = Config(str(config_file), str(content_file))

    token = os.environ.get("SYMPLA_TOKEN", "").strip()
    if not token:
        typer.echo("SYMPLA_TOKEN não encontrado no ambiente. Informe o token da API do Sympla.")
        token = typer.prompt("SYMPLA_TOKEN")
        token = token.strip()
        if not token:
            raise ValueError("Token do Sympla é obrigatório")

    # 1) Buscar eventos mais recentes
    headers = {"S_token": token}
    base_url = os.environ.get("SYMPLA_BASE_URL", "https://api.sympla.com.br/public/v4").rstrip("/")
    url = f"{base_url}/events"
    params = {"sort_by": "start_date", "sort_order": "desc", "per_page": 3}
    resp = requests.get(url, headers=headers, params=params, timeout=20)
    try:
        resp.raise_for_status()
    except Exception:
        raise RuntimeError(f"Sympla API retornou {resp.status_code}: {resp.text[:200]}")
    payload = resp.json() or {}
    events = payload.get("data") or payload.get("events") or []
    if not isinstance(events, list) or not events:
        raise RuntimeError("Nenhum evento retornado pela API do Sympla")
    # Ordenar por data de início desc (mais recentes primeiro)
    def _parse_date(ev: dict):
        return (ev.get("start_date") or ev.get("startDate") or "")
    events.sort(key=_parse_date, reverse=True)
    events = events[:3]

    # 2) Escolha interativa (Rich)
    console = get_console()
    ui_section("Selecione o evento a ativar")
    def _infer_sympla_code(ev: dict) -> str | None:
        url_val = ev.get("url") or ev.get("event_link") or ""
        if not url_val:
            return None
        try:
            path = urlparse(url_val).path or ""
            last = ""
            if path:
                parts = [p for p in path.split("/") if p]
                last = parts[-1] if parts else ""
            candidate = last
            # pick first alnum token length>=5
            m = re.search(r"[A-Za-z0-9]{5,}", candidate)
            return m.group(0) if m else None
        except Exception:
            return None

    def _format_short_title(ev: dict) -> str:
        name_raw = (ev.get("name") or ev.get("eventName") or "").strip()
        addr = ev.get("address") if isinstance(ev.get("address"), dict) else {}
        uf = (addr.get("state") if isinstance(addr, dict) else None) or ev.get("state") or ""
        base_upper = (name_raw.split("-")[0].strip() or name_raw).upper()
        if uf:
            return f"{base_upper} ({uf})..."
        return f"{base_upper}..."

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="bold", justify="right", width=3)
    table.add_column("Evento", style="white")
    table.add_column("Início", style="magenta")
    table.add_column("ID", style="cyan")

    for idx, ev in enumerate(events):
        ev_id = _infer_sympla_code(ev) or ev.get("id") or ev.get("eventId")
        short_title = _format_short_title(ev)
        ev_start = ev.get("start_date") or ev.get("startDate")
        table.add_row(str(idx + 1), short_title, str(ev_start), str(ev_id))

    console.print(table)
    raw_choice = typer.prompt("Número do evento", default="1")
    try:
        choice_idx = max(1, min(len(events), int(str(raw_choice).strip()))) - 1
    except Exception:
        choice_idx = 0
    selected = events[choice_idx]

    # 3) Normalizar campos
    sympla_id = (_infer_sympla_code(selected) or str(selected.get("id") or selected.get("eventId") or "")).strip()
    event_name = (selected.get("name") or selected.get("eventName") or "").strip()
    event_link = (selected.get("url") or selected.get("event_link") or "").strip()
    start_date = (selected.get("start_date") or selected.get("startDate") or "").strip()
    end_date = (selected.get("end_date") or selected.get("endDate") or "").strip()
    addr = selected.get("address") if isinstance(selected.get("address"), dict) else {}
    city = (addr.get("city") if isinstance(addr, dict) else None) or selected.get("city") or ""
    state = (addr.get("state") if isinstance(addr, dict) else None) or selected.get("state") or ""
    def _extract_place(ev: dict) -> str:
        a = ev.get("address") if isinstance(ev.get("address"), dict) else {}
        # Tenta múltiplas chaves comuns em APIs para nome do local
        candidate_keys_addr = [
            "venue", "name", "place", "place_name", "venue_name",
            "address", "address_line", "address_line1", "address_line_1",
            "local", "local_name", "location_name",
        ]
        for k in candidate_keys_addr:
            try:
                v = a.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
            except Exception:
                continue
        # Top-level fallbacks
        candidate_keys_top = ["placeName", "place", "venue", "location", "location_name"]
        for k in candidate_keys_top:
            try:
                v = ev.get(k)
                if isinstance(v, str) and v.strip():
                    return v.strip()
            except Exception:
                continue
        return ""
    place_name = _extract_place(selected)

    # 3.1) Datas (formatação humana PT-BR)
    def _parse_date_ymd(date_str: str) -> tuple[int | None, int | None, int | None]:
        try:
            # Tenta formatos comuns do Sympla: 'YYYY-MM-DD HH:MM:SS' ou 'YYYY-MM-DDTHH:MM:SSZ'
            import re as _re
            m = _re.match(r"(\d{4})-(\d{2})-(\d{2})", date_str)
            if not m:
                return None, None, None
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return y, mo, d
        except Exception:
            return None, None, None

    # Locale configurável via env ou YAML (padrão: pt_BR)
    import os as _os
    _locale_pref = (
        _os.environ.get("EVENT_DATE_LOCALE")
        or _os.environ.get("LOCALE")
        or (cfg.content_config.get("email", {}).get("locale") if isinstance(cfg.content_config, dict) else None)
        or "pt_BR"
    )

    def _format_ptbr_date_range(start_str: str, end_str: str) -> str:
        try:
            from babel.dates import format_date as _fmt_date
        except Exception:
            # Se Babel não estiver instalado, mantém string original
            return start_str if (not end_str or start_str == end_str) else f"{start_str} a {end_str}"

        y1, m1, d1 = _parse_date_ymd(start_str)
        y2, m2, d2 = _parse_date_ymd(end_str) if end_str else (y1, m1, d1)
        if not all(v is not None for v in (y1, m1, d1)):
            return start_str
        if not all(v is not None for v in (y2, m2, d2)):
            y2, m2, d2 = y1, m1, d1

        from datetime import date as _date
        dt1 = _date(int(y1), int(m1), int(d1))
        dt2 = _date(int(y2), int(m2), int(d2))
        m1_name = _fmt_date(dt1, format='MMMM', locale=_locale_pref)
        m2_name = _fmt_date(dt2, format='MMMM', locale=_locale_pref)

        if y1 == y2:
            if m1 == m2:
                if d1 == d2:
                    return f"{d1} de {m1_name}"
                return f"{d1} e {d2} de {m1_name}"
            return f"{d1} de {m1_name} a {d2} de {m2_name}"
        return f"{d1} de {m1_name} de {y1} a {d2} de {m2_name} de {y2}"

    data_text = _format_ptbr_date_range(start_date, end_date)

    # 3.2) Cupom e link com cupom
    # Ler cupom atual (se existir) do YAML
    current_coupon = ""
    try:
        existing_content = {}
        existing_path = Path(content_file)
        if existing_path.exists():
            existing_content = yaml.safe_load(existing_path.read_text(encoding="utf-8")) or {}
        current_coupon = str(((existing_content.get("evento") or {}).get("cupom")) or "").strip()
    except Exception:
        current_coupon = ""

    # Definir cupom padrão (ex.: CINA30) ao obter as informações do evento
    # Caso já exista no YAML, mantém; caso contrário, usa DEFAULT_COUPON (env) ou 'CINA30'
    default_coupon = os.environ.get("DEFAULT_COUPON", "CINA30").strip() or "CINA30"
    def _is_valid_coupon(code: str) -> bool:
        try:
            return bool(re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,}$", code or ""))
        except Exception:
            return False
    coupon = current_coupon if _is_valid_coupon(current_coupon) else default_coupon

    # Montar link com parâmetro de cupom 'd'
    def _with_coupon_param(url_str: str, code: str) -> str:
        try:
            if not code:
                return url_str
            from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
            parts = urlparse(url_str)
            q = dict(parse_qsl(parts.query, keep_blank_values=True))
            q["d"] = code
            new_query = urlencode(q, doseq=True)
            return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_query, parts.fragment))
        except Exception:
            # Fallback simples
            joiner = "&" if ("?" in url_str) else "?"
            return f"{url_str}{joiner}d={code}"

    event_link_with_coupon = _with_coupon_param(event_link, coupon)

    # 3.3) Resumo e confirmação (Rich)
    summary = Table(show_header=False, header_style="bold", box=None)
    summary.add_column("Campo", style="bold white", no_wrap=True)
    summary.add_column("Valor", style="cyan")
    summary.add_row("Nome", event_name)
    summary.add_row("ID (Sympla)", str(sympla_id))
    summary.add_row("Data", data_text)
    summary.add_row("Cidade/UF", f"{city}/{state}")
    summary.add_row("Local", place_name)
    summary.add_row("Link", event_link_with_coupon)
    summary.add_row("Cupom", coupon)

    console.print(Panel(summary, title="Resumo do evento selecionado", title_align="left", border_style="bright_cyan"))
    if not typer.confirm("Confirmar atualização do YAML e Postgres com este evento?", default=True):
        typer.echo("Operação cancelada. Nenhuma alteração aplicada.")
        return

    # 4) Atualizar YAML
    content_path = Path(content_file)
    content_dict = {}
    if content_path.exists():
        content_dict = yaml.safe_load(content_path.read_text(encoding="utf-8")) or {}
    content_dict.setdefault("evento", {})
    content_dict["evento"].update({
        "sympla_id": sympla_id,
        "nome": event_name,
        "link": event_link_with_coupon,
        "data": data_text,
        "cidade": city,
        "uf": state,
        "local": place_name,
        "cupom": coupon,
    })
    content_path.write_text(yaml.safe_dump(content_dict, allow_unicode=True, sort_keys=False), encoding="utf-8")
    ui_success(f"YAML atualizado: {content_path}")

    # 5) Atualizar Postgres (usando SQLs parametrizadas do diretório sql/)
    from .db import Database
    with Database(cfg) as db:
        # Desativar todos os eventos ativos
        try:
            db.execute("sql/events/deactivate_all_events.sql")
        except Exception as e:
            ui_warn(f"Não foi possível desativar eventos existentes: {e}")

        # Tentar UPDATE por sympla_id
        try:
            detail_payload = {
                "cupom": coupon,
                "data_text": data_text,
                "original_link": event_link,
                "event_code": sympla_id,
            }
            affected = db.execute(
                "sql/events/update_event_param.sql",
                (sympla_id, event_name, start_date, end_date, city, state, place_name, event_link_with_coupon, json.dumps(detail_payload, ensure_ascii=False)),
            )
        except Exception as e:
            affected = 0
            ui_warn(f"Falha no update (tudo bem se for novo): {e}")
        if not affected:
            detail_payload = {
                "cupom": coupon,
                "data_text": data_text,
                "original_link": event_link,
                "event_code": sympla_id,
            }
            db.execute(
                "sql/events/insert_event_param.sql",
                (sympla_id, event_name, start_date, end_date, city, state, place_name, event_link_with_coupon, json.dumps(detail_payload, ensure_ascii=False)),
            )

    ui_success("Evento ativo sincronizado no Postgres e YAML.")


def _ensure_valid_sender(config_path: Path) -> None:
    """Garante que o campo email.sender no config.yaml não seja placeholder.

    Se for vazio ou terminar com @exemplo.com, solicita ao usuário um remetente autorizado
    e atualiza o arquivo de configuração.
    """
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        email_cfg = data.get("email", {}) if isinstance(data, dict) else {}
        sender = str(email_cfg.get("sender", "")).strip()
        if not sender:
            typer.echo("\n⚠ Remetente (From) não configurado corretamente no config.yaml.")
            typer.echo("Informe um remetente autorizado no provedor SMTP (ex.: nome <no-reply@seu-dominio.com.br>)")
            new_sender = typer.prompt("Remetente (From)")
            if "@" not in new_sender:
                typer.echo("Remetente inválido. Mantendo configuração atual.")
                return
            email_cfg["sender"] = new_sender
            data["email"] = email_cfg
            config_path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
            typer.echo(f"✅ Remetente atualizado em {config_path}")
    except Exception as e:
        typer.echo(f"Não foi possível validar/atualizar o remetente: {e}")


def _self_test() -> None:
    """Executa uma bateria de auto-testes e mostra um resumo."""
    errors: List[str] = []
    checks: List[str] = []

    ui_section("Auto-teste da aplicação")

    # 1) Ambiente
    env_mode = os.environ.get("ENVIRONMENT", "test")
    ui_info(f"ENVIRONMENT: {env_mode}")
    checks.append("environment")

    # 2) Arquivos de config
    try:
        config_file, content_file = _ensure_or_create_default_config()
        if config_file.exists() and content_file.exists():
            ui_success(f"Config OK: {config_file}")
            ui_success(f"Email content OK: {content_file}")
        else:
            raise FileNotFoundError("Arquivos de configuração ausentes")
        checks.append("config_files")
    except Exception as e:
        ui_error(f"Falha ao preparar configs: {e}")
        errors.append("config_files")

    # 3) Template e renderização
    try:
        cfg = Config(str(config_file), str(content_file))
        template_path_str = cfg.content_config.get("email", {}).get("template_path")
        if not template_path_str:
            raise ValueError("email.template_path não definido em config/email.yaml")
        template_path = Path(template_path_str)
        if not template_path.exists():
            raise FileNotFoundError(f"Template não encontrado: {template_path}")
        ui_success(f"Template OK: {template_path}")
        # Render preview in-memory
        processor = TemplateProcessor(cfg)
        test_recipient = os.environ.get("TEST_RECIPIENT") or cfg.email_config.get("test_recipient") or ""
        recipient = {"email": test_recipient, "name": ""}
        html = processor.process(template_path, recipient)
        if html and "</html>" in html.lower():
            ui_success("Renderização do template OK")
        else:
            ui_warn("Renderização do template produziu conteúdo sem <html> — verifique seu template.")
        checks.append("template_render")
    except Exception as e:
        ui_error(f"Falha na renderização do template: {e}")
        errors.append("template_render")

    # 4) SMTP DNS/porta
    try:
        smtp = cfg.smtp_config
        host = (smtp.get("host") or "").strip()
        port = int(smtp.get("port", 587))
        if not host:
            raise ValueError("SMTP host não configurado")
        socket.getaddrinfo(host, port)
        # Tentativa rápida de abrir socket TCP
        with socket.create_connection((host, port), timeout=int(os.environ.get("SMTP_TEST_TIMEOUT", "5"))):
            pass
        ui_success(f"SMTP resolvido e porta acessível: {host}:{port}")
        checks.append("smtp_connect")
    except Exception as e:
        ui_error(f"SMTP indisponível: {e}")
        errors.append("smtp_connect")

    # 5) Postgres DNS/conexão
    try:
        pg = cfg.postgres_config
        host = pg.get("host")
        port = int(pg.get("port", 5432))
        user = pg.get("user")
        database = pg.get("database")
        socket.getaddrinfo(host, port)
        conn = psycopg.connect(host=host, port=port, user=user, password=pg.get("password"), dbname=database, connect_timeout=5)
        conn.close()
        ui_success("Postgres conectado com sucesso")
        checks.append("postgres_connect")
    except Exception as e:
        ui_error(f"Postgres indisponível: {e}")
        errors.append("postgres_connect")

    # 6) Sympla API
    try:
        token = (os.environ.get("SYMPLA_TOKEN") or "").strip()
        if not token:
            raise RuntimeError("SYMPLA_TOKEN não configurado no ambiente (.env)")
        headers = {"S_token": token}
        base_url = os.environ.get("SYMPLA_BASE_URL", "https://api.sympla.com.br/public/v4").rstrip("/")
        url = f"{base_url}/events"
        params = {"per_page": 1}
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if 200 <= resp.status_code < 300:
            ui_success("Sympla API acessível com o token fornecido")
            checks.append("sympla_api")
        else:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:120]}")
    except Exception as e:
        ui_error(f"Sympla API indisponível: {e}")
        errors.append("sympla_api")

    # 7) Sumário
    ok = len(checks) - len(errors)
    total = len(checks)
    if errors:
        ui_warn(f"Auto-teste concluído com falhas ({ok}/{total} OK).")
    else:
        ui_success("Auto-teste concluído com sucesso (tudo OK).")


def _test_postgres_connection() -> None:
    """Testa a conexão com o Postgres usando variáveis do .env (PG*)."""
    config_file, content_file = _ensure_or_create_default_config()
    cfg = Config(str(config_file), str(content_file))
    pg = cfg.postgres_config
    host = pg.get("host")
    port = int(pg.get("port", 5432))
    user = pg.get("user")
    password = pg.get("password")
    database = pg.get("database")

    missing = [k for k, v in {"PGUSER": user, "PGDATABASE": database}.items() if not v]
    if missing:
        typer.echo(f"⚠️ Configure as variáveis no .env: {', '.join(missing)}")

    try:
        socket.getaddrinfo(host, port)
    except socket.gaierror:
        typer.echo(f"❌ Não foi possível resolver o host Postgres (PGHOST): {host}")
        return

    try:
        conn = psycopg.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            dbname=database,
            connect_timeout=5,
        )
        conn.close()
        typer.echo("✅ Conexão com Postgres OK")
    except Exception as e:
        typer.echo(f"❌ Falha ao conectar ao Postgres: {e}")


if __name__ == "__main__":
    typer.run(main)