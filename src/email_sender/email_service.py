import logging
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
import signal
import math

from .config import Config
from .email_templating import TemplateProcessor
from .infrastructure.reporting import TextReportGenerator
from .utils.ui import get_console, notify_telegram
from .smtp_manager import SmtpManager
from .db import Database

log = logging.getLogger("email_sender")

class EmailService:
    def __init__(self, config: Config):
        self.config = config
        # Passa o conteúdo do email.yaml para o TemplateProcessor
        # Handle both email_content attribute and content_config property
        email_content = getattr(self.config, 'email_content', None)
        if email_content is None:
            # Fallback to content_config property if email_content is not available
            email_content = getattr(self.config, 'content_config', {})
        self.template_processor = TemplateProcessor(email_content)
        self.report_generator = TextReportGenerator(reports_dir=self.config.email_config.get("reports_dir", "reports"))
        self.smtp_manager = SmtpManager(config)

    # Carrega o prompt de geração de assunto a partir de arquivo externo
    def _load_subject_prompt_template(self) -> Optional[str]:
        try:
            import os as _os
            from pathlib import Path as _P
            prompt_path = _os.environ.get("GENAI_SUBJECT_PROMPT_PATH", "prompts/subject_generation.md")
            p = _P(prompt_path)
            if p.exists():
                return p.read_text(encoding="utf-8")
        except Exception:
            return None
        return None

    def _build_event_brief(self) -> str:
        """Monta um resumo curto do evento a partir do YAML.

        Formato: "Evento: <nome> • <cidade/UF> • <data> • <local>" (campos opcionais)
        """
        try:
            evento_cfg = (self.config.content_config or {}).get("evento", {}) if hasattr(self.config, 'content_config') else {}
            name = str(evento_cfg.get("nome") or "").strip()
            city = str(evento_cfg.get("cidade") or "").strip()
            uf = str(evento_cfg.get("uf") or evento_cfg.get("state") or "").strip()
            date_text = str(evento_cfg.get("data") or "").strip()
            place = str(evento_cfg.get("local") or "").strip()
            parts: list[str] = []
            if name:
                parts.append(name)
            if city or uf:
                loc = f"{city}/{uf}" if city and uf else (city or uf)
                if loc:
                    parts.append(loc)
            if date_text:
                parts.append(date_text)
            if place:
                parts.append(place)
            brief = " • ".join([p for p in parts if p])
            return f"Evento: {brief}" if brief else ""
        except Exception:
            return ""

    # ————————————————————————————————————
    # Assunto via GenAI por padrão (sem hardcode), com fallback derivado de dados
    # ————————————————————————————————————
    def _build_subject_fallback(self) -> str:
        try:
            evento_cfg = (self.config.content_config or {}).get("evento", {}) if hasattr(self.config, 'content_config') else {}
            event_name = str(evento_cfg.get("nome") or "").strip()
            city = str(evento_cfg.get("cidade") or "").strip()
            uf = str(evento_cfg.get("uf") or evento_cfg.get("state") or "").strip()
            data_txt = str(evento_cfg.get("data") or "").strip()
            place = str(evento_cfg.get("local") or "").strip()
            parts = []
            if event_name:
                parts.append(event_name)
            loc = f"{city} ({uf})" if city and uf else (city or uf)
            if loc:
                parts.append(loc)
            if data_txt:
                parts.append(data_txt)
            if place:
                parts.append(place)
            subject = " — ".join([p for p in parts if p])
            # Limitar tamanho amigável para inbox
            return subject[:90]
        except Exception:
            return ""

    def _resolve_subject(self) -> str:
        """Gera o assunto por GenAI quando possível; caso contrário, deriva dos dados do evento.

        Regras:
        - Se houver chave de API (GOOGLE_API_KEY ou GENAI_API_KEY), sempre gerar via GenAI.
        - Caso contrário, compor a partir de `evento` (nome, cidade/UF, data, local), sem strings fixas.
        - Opcionalmente, se SUBJECT_USE_YAML=1, usa `email.subject` exatamente como está no YAML.
        """
        import os as _os
        # Respeitar opt-in explícito para usar YAML puro
        if (_os.environ.get("SUBJECT_USE_YAML") or "").lower() in {"1","true","yes","on"}:
            return str(self.config.content_config.get("email", {}).get("subject", "")).strip()

        evento_cfg = (self.config.content_config or {}).get("evento", {}) if hasattr(self.config, 'content_config') else {}
        api_key = _os.environ.get("GOOGLE_API_KEY") or _os.environ.get("GENAI_API_KEY")
        model_name = _os.environ.get("GENAI_MODEL", "gemini-2.5-flash")
        try:
            max_retries = int(_os.environ.get("GENAI_MAX_RETRIES", "1"))
        except Exception:
            max_retries = 1
        if api_key:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                from langchain_core.messages import HumanMessage

                # Montar contexto textual do evento
                parts: list[str] = []
                name = str(evento_cfg.get("nome") or "").strip()
                city = str(evento_cfg.get("cidade") or "").strip()
                uf = str(evento_cfg.get("uf") or evento_cfg.get("state") or "").strip()
                date_text = str(evento_cfg.get("data") or "").strip()
                place = str(evento_cfg.get("local") or "").strip()
                link = str(evento_cfg.get("link") or "").strip()
                if name:
                    parts.append(f"EVENTO: {name}")
                if city or uf:
                    loc = f"{city}/{uf}" if city and uf else (city or uf)
                    parts.append(f"LOCAL: {loc}")
                if date_text:
                    parts.append(f"DATA: {date_text}")
                if place:
                    parts.append(f"LOCALIDADE/ESPACO: {place}")
                if link:
                    parts.append(f"LINK: {link}")
                event_ctx = "\n".join(parts) or str(evento_cfg)

                # Carregar prompt externo e injetar contexto; se não houver prompt, não usa LLM
                tpl = self._load_subject_prompt_template()
                if not tpl:
                    raise RuntimeError("subject prompt template missing")
                if "{CONTEXT}" in tpl or "{VARIATION_HINT}" in tpl:
                    prompt = tpl.replace("{CONTEXT}", event_ctx).replace("{VARIATION_HINT}", "")
                else:
                    prompt = f"{tpl}\n\nCONTEXT:\n{event_ctx}\n"

                # Usar Gemini 2.5 Flash via LangChain
                llm = ChatGoogleGenerativeAI(model=model_name, api_key=api_key, temperature=0.6, max_retries=max_retries)
                resp = llm.invoke([HumanMessage(content=prompt)])
                text = getattr(resp, "content", None) or str(resp)
                text = (text or "").strip().strip('"').strip("'")
                return " ".join(text.split())[:90]
            except Exception:
                pass
        # Fallback derivado dos dados
        return self._build_subject_fallback()

    # Guardrails específicos foram removidos do código para evitar hardcode; a qualidade é guiada pelo prompt externo.

    def _generate_subject_for_body(self, body_html: str, existing_subject: str | None = None, *, temperature: float = 0.6, variation_hint: str | None = None) -> str:
        """Gera assunto curto com base no corpo renderizado.

        - Se houver chave de GenAI, usa LLM para sintetizar um assunto (<= 60 chars)
        - Fallback: extrai <title>, <h1>, <strong> ou inicia pelo texto plano truncado
        """
        try:
            import re as _re
            import os as _os

            def _first(pattern: str, text: str) -> str | None:
                m = _re.search(pattern, text, flags=_re.IGNORECASE | _re.DOTALL)
                return m.group(1).strip() if m else None

            title = _first(r"<title[^>]*>(.*?)</title>", body_html)
            h1 = _first(r"<h1[^>]*>(.*?)</h1>", body_html)
            strong = _first(r"<strong[^>]*>(.*?)</strong>", body_html)
            # Coletar mais sinais: múltiplos <strong>, bullets e headings
            def _all(pattern: str, text: str, max_items: int = 3) -> list[str]:
                arr = _re.findall(pattern, text, flags=_re.IGNORECASE | _re.DOTALL)
                cleaned: list[str] = []
                for it in arr:
                    t = _re.sub(r"<[^>]+>", " ", it)
                    t = _re.sub(r"\s+", " ", t).strip()
                    if t:
                        cleaned.append(t)
                    if len(cleaned) >= max_items:
                        break
                return cleaned

            strongs = _all(r"<strong[^>]*>(.*?)</strong>", body_html, max_items=3)
            bullets = _all(r"<li[^>]*>(.*?)</li>", body_html, max_items=3)
            h2h3 = _all(r"<(h2|h3)[^>]*>(.*?)</\1>", body_html, max_items=2)
            # Texto plano (remove scripts/styles e tags)
            text = _re.sub(r"<script[\s\S]*?</script>|<style[\s\S]*?</style>", " ", body_html, flags=_re.IGNORECASE)
            text = _re.sub(r"<[^>]+>", " ", text)
            text = _re.sub(r"\s+", " ", text).strip()

            api_key = _os.environ.get("GOOGLE_API_KEY") or _os.environ.get("GENAI_API_KEY")
            model_name = _os.environ.get("GENAI_MODEL", "gemini-2.5-flash")
            try:
                max_retries = int(_os.environ.get("GENAI_MAX_RETRIES", "1"))
            except Exception:
                max_retries = 1
            if api_key:
                try:
                    from langchain_google_genai import ChatGoogleGenerativeAI
                    from langchain_core.messages import HumanMessage
                    context_parts = []
                    if title:
                        context_parts.append(f"TITLE: {title}")
                    if h1 and h1 != title:
                        context_parts.append(f"H1: {h1}")
                    if strong:
                        context_parts.append(f"HIGHLIGHT: {strong}")
                    if strongs:
                        context_parts.append("DESTAQUES: " + "; ".join(strongs))
                    if bullets:
                        context_parts.append("BULLETS: " + "; ".join(bullets))
                    if h2h3:
                        h2h3_texts = [x if isinstance(x, str) else x[1] for x in h2h3]
                        context_parts.append("SECOES: " + "; ".join(h2h3_texts))
                    body_preview = text[:1600]
                    context_parts.append(f"BODY: {body_preview}")
                    ctx = "\n".join(context_parts)

                    tpl = self._load_subject_prompt_template()
                    if not tpl:
                        raise RuntimeError("subject prompt template missing")
                    prompt = tpl.replace("{CONTEXT}", ctx)
                    if variation_hint:
                        prompt = prompt.replace("{VARIATION_HINT}", variation_hint)
                    else:
                        prompt = prompt.replace("{VARIATION_HINT}", "")

                    llm = ChatGoogleGenerativeAI(model=model_name, api_key=api_key, temperature=temperature, max_retries=max_retries)
                    resp = llm.invoke([HumanMessage(content=prompt)])
                    out = getattr(resp, "content", None) or str(resp)
                    out = (out or "").strip().strip('"').strip("'")
                    return " ".join(out.split())[:90] or (existing_subject or self._build_subject_fallback())
                except Exception:
                    pass

            # Fallback heurístico
            for cand in [title, h1, strong]:
                if cand and cand.strip():
                    return " ".join(cand.split())[:90]
            if text:
                return text[:90]
            return existing_subject or self._build_subject_fallback()
        except Exception:
            return existing_subject or self._build_subject_fallback()

    def _maybe_interactive_subject(self, generated_subject: str, body_html: str, *, force: bool = False, show_current_first: bool = True) -> str:
        """Pergunta aprovação do assunto e permite regenerar algumas vezes.

        - force=True obriga interação (ignora env), útil em modo de teste.
        - Caso não seja TTY, retorna o gerado diretamente.
        """
        import os as _os
        interactive = force or ((_os.environ.get("SUBJECT_INTERACTIVE") or "").lower() in {"1","true","yes","on"})
        if not interactive:
            return generated_subject

        try:
            import sys
            import typer
            console = get_console()
            # Se não estiver em TTY, evita interação
            if not sys.stdin or not sys.stdin.isatty():
                return generated_subject

            current = generated_subject
            attempts_left = 2  # total 1 geração + até 2 variações
            while True:
                # Evita duplicar a primeira linha se já mostramos antes
                if show_current_first:
                    console.print(f"[bold cyan]Assunto gerado:[/bold cyan] [white]{current}[/white]")
                # Depois da primeira iteração, sempre mostramos
                show_current_first = True
                if typer.confirm("Aprovar este assunto?", default=True):
                    return current
                if attempts_left <= 0:
                    console.print("[yellow]Sem tentativas restantes. Mantendo o último assunto gerado.[/yellow]")
                    return current
                console.print("[cyan]Gerando outra variação de assunto...[/cyan]")
                # Gera uma variação pedindo diferença
                current = self._generate_subject_for_body(
                    body_html,
                    existing_subject=current,
                    temperature=0.9,
                    variation_hint="gere uma variação diferente do anterior, mais curiosa e com benefício específico"
                )
                attempts_left -= 1
        except Exception as e:
            # Log the exception for debugging
            try:
                console = get_console()
                console.print(f"[red]Erro na geração interativa de assunto: {e}[/red]")
            except:
                pass
            return generated_subject

    

    

    def process_email_template(self, template_path: str, recipient: Dict, email_subject: str) -> str:
        """
        Processa o template HTML, substituindo as variáveis pelos valores do destinatário.
        
        Args:
            template_path: Caminho para o arquivo de template HTML
            recipient: Dicionário com os dados do destinatário
            email_subject: Assunto do email (can be used by template processor if needed)
            
        Returns:
            HTML formatado
        """
        try:
            log.debug(f"Iniciando processamento de template em: {template_path}")
            log.debug(f"Dados do recipient: {recipient}")
            log.debug(f"Assunto do email: {email_subject}")
            
            # Antes de processar o template, garantir que o link do evento tenha o cupom aplicado
            # O cupom padrão pode vir do YAML ou do Postgres (evento ativo)
            self._ensure_event_coupon_and_link()
            # Garantir URLs padrão (unsubscribe) a partir do domínio público configurado
            try:
                email_cfg = self.config.email_config if hasattr(self.config, 'email_config') else {}
                domain = (email_cfg.get("public_domain") or "").strip()
                if domain:
                    urls = self.template_processor.content_config.setdefault("urls", {})
                    urls.setdefault("unsubscribe", f"https://{domain}/api/unsubscribe")
                    # Base da API para tracking (open/click)
                    urls.setdefault("base_api", f"https://{domain}")
            except Exception:
                pass
            
            log.debug(f"Content config após _ensure_event_coupon_and_link: {self.template_processor.content_config}")
            
            # Corrected method call to 'process' and ensure template_path is a Path object
            html_content = self.template_processor.process(Path(template_path), recipient)
            log.debug(f"Conteúdo HTML processado (tamanho: {len(html_content)})")
            if not html_content:
                log.error("Conteúdo HTML vazio após processamento!")
            else:
                log.debug(f"Primeiros 200 caracteres do HTML: {html_content[:200]}")
            return html_content
        except Exception as e:
            log.error(f"Erro ao processar template via TemplateProcessor: {str(e)}")
            if isinstance(e, AttributeError):
                log.exception("AttributeError details:")
            raise

    def _ensure_event_coupon_and_link(self) -> None:
        """Garante que `evento.cupom` e `evento.link` estejam consistentes e que o link
        inclua o parâmetro de cupom `d` por padrão.

        Regras:
        - Se `evento.cupom` estiver ausente, tenta buscar no Postgres (evento ativo -> detail.cupom)
        - Se `evento.link` estiver ausente, tenta usar `event_link` do Postgres
        - Sempre que houver cupom e link, aplica/força `?d=<cupom>` (ou `&d=`) no link
        """
        try:
            evento_cfg = (self.config.email_content or {}).get("evento", {})
            # Cupom padrão se nada vier do YAML/DB
            default_coupon = ( __import__('os').environ.get("DEFAULT_COUPON", "CINA30").strip() or "CINA30" )

            # Leitura atual
            def _is_valid_coupon(code: str) -> bool:
                try:
                    import re as _re
                    return bool(_re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]{2,}$", code or ""))
                except Exception:
                    return False
            coupon_code = str(evento_cfg.get("cupom") or "").strip()
            link_raw = str(evento_cfg.get("link") or "").strip()

            # Helper para aplicar o parâmetro d=<cupom> em uma URL
            def _with_coupon_param(url_str: str, code: str) -> str:
                if not url_str:
                    return url_str
                if not code:
                    return url_str
                try:
                    from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
                    parts = urlparse(url_str)
                    q = dict(parse_qsl(parts.query, keep_blank_values=True))
                    q["d"] = code
                    new_query = urlencode(q, doseq=True)
                    return urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_query, parts.fragment))
                except Exception:
                    joiner = "&" if ("?" in url_str) else "?"
                    return f"{url_str}{joiner}d={code}"

            # Se faltou qualquer um (cupom ou link), tentar recuperar do Postgres
            if not coupon_code or not link_raw:
                try:
                    with Database(self.config) as db:
                        row = db.fetch_one("sql/events/select_active_event.sql") or {}
                        if row:
                            # Preencher link a partir do DB se ausente
                            if not link_raw:
                                link_raw = str(row.get("event_link") or "").strip()
                            # Extrair cupom de detail (dict ou JSON) se ausente
                            if not coupon_code:
                                detail_obj = row.get("detail")
                                if isinstance(detail_obj, dict):
                                    coupon_code = str(
                                        (detail_obj.get("cupom") or detail_obj.get("coupon") or detail_obj.get("d") or "")
                                    ).strip()
                                else:
                                    try:
                                        if detail_obj:
                                            parsed = json.loads(detail_obj)
                                            if isinstance(parsed, dict):
                                                coupon_code = str(
                                                    (parsed.get("cupom") or parsed.get("coupon") or parsed.get("d") or "")
                                                ).strip()
                                    except Exception:
                                        pass
                except Exception:
                    # Se não conseguir acessar o DB, segue com o que já tem
                    pass

            # Atualizar YAML em memória com os valores resolvidos (cupom com fallback padrão)
            if not _is_valid_coupon(coupon_code):
                coupon_code = default_coupon
            if coupon_code:
                evento_cfg["cupom"] = coupon_code
            if link_raw:
                final_link = _with_coupon_param(link_raw, coupon_code) if coupon_code else link_raw
                evento_cfg["link"] = final_link

        except Exception:
            # Não bloquear envio por falha ao resolver cupom/link
            return

    def generate_report(self, start_time: float, end_time: float, total_sent: int, successful: int, failed: int, *, ignored_unsubscribed: int | None = None, ignored_bounces: int | None = None) -> Dict[str, Any]:
        """
        Gera um relatório do processo de envio de emails usando ReportGenerator.
        """
        try:
            return self.report_generator.generate_report(
                start_time, 
                end_time, 
                total_sent, 
                successful, 
                failed,
                ignored_unsubscribed=ignored_unsubscribed,
                ignored_bounces=ignored_bounces
            )
        except Exception as e:
            log.error(f"Erro ao gerar relatório via ReportGenerator: {str(e)}")
            raise

    # Legacy helpers removed: remove_duplicates, create_backup, send_test_email.

    def process_email_sending(self, template: str = "", limit: int = 0, is_test_mode: bool = False) -> Dict[str, Any]:
        """Processa envio em lote usando Postgres via SQL (fluxo simplificado)."""
        try:
            # Configurar console e formatação Rich
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel
            from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
            from rich.rule import Rule
            from rich.box import ROUNDED
            from rich.text import Text
            
            console = Console()
            console.rule("[bold blue]Iniciando Processo de Envio de Emails (Postgres)[bold blue]", style="blue")
            
            start_time = time.time()
            successful = 0
            failed = 0
            total_send_attempts = 0
            unsub_ignored = 0
            bounce_ignored = 0
            
            STATE_KEY = "last_sent_contact_id"
            
            pause_duration_after_attempts = self.config.email_config.get("batch_delay", 60)
            retry_attempts_config = self.config.email_config.get("retry_attempts", 3)
            retry_delay_config = self.config.email_config.get("retry_delay", 60)
            send_timeout = self.config.email_config.get("send_timeout", 10)
            max_retry_minutes = self.config.email_config.get("max_retry_minutes", 5)
            batch_size = self.config.email_config.get("batch_size", 200)
            
            # Exibir configurações de envio
            console.print("\n[bold]Configurações de envio:[/bold]")
            console.print(f"Tamanho do lote: [cyan]{batch_size} emails[/cyan]")
            console.print(f"Número máximo de tentativas: [cyan]{retry_attempts_config}[/cyan]")
            console.print(f"Tempo entre tentativas: [cyan]{retry_delay_config}s[/cyan]")
            console.print(f"Timeout por tentativa: [cyan]{send_timeout}s[/cyan]")
            console.print(f"Pausa entre lotes: [cyan]{pause_duration_after_attempts}s[/cyan]")
            
            base_subject = self._resolve_subject()
            console.print(f"Assunto base: [bold magenta]'{base_subject}'[/bold magenta]")
            asked_subject_once = False
            final_subject_for_batch: Optional[str] = None

            if not template.endswith('.html'):
                template += '.html'
                
            template_path_obj = Path(template)
            if not template_path_obj.exists():
                root_template_path = Path("templates") / template_path_obj.name
                if root_template_path.exists():
                    template_path_obj = root_template_path
                    console.print(f"Template encontrado em: [green]templates/{template_path_obj.name}[/green]")
                else:
                    console.print(f"[bold red]Erro: Template não encontrado: {template}[/bold red]")
                    raise FileNotFoundError(f"Template file not found: {template}")
            else:
                template_path_obj = template_path_obj.resolve()
                console.print(f"Template encontrado em: [green]{template_path_obj}[/green]")

            with Database(self.config) as db:
                # Criar a mensagem primeiro para obter um message_id
                try:
                    evento_cfg = (self.config.content_config or {}).get("evento", {})
                    now = datetime.now()
                    state = evento_cfg.get("uf", "")
                    month = f"{now.month:02d}"
                    year = str(now.year)
                    event_sympla_id = evento_cfg.get("sympla_id")

                    # Verificar se o evento existe no banco de dados
                    if not event_sympla_id:
                        raise ValueError("ID do evento (sympla_id) não encontrado no arquivo de configuração.")

                    event_row = db.fetch_one(
                        "sql/events/select_event_internal_id_by_sympla_id.sql", (event_sympla_id,)
                    )
                    if not event_row or not event_row.get("id"):
                        raise ValueError(
                            f"Evento com sympla_id='{event_sympla_id}' não encontrado no banco de dados. "
                            "Execute a opção 'Atualizar dados do evento Sympla' no menu principal."
                        )
                    
                    internal_event_id = event_row["id"]

                    message_row = db.fetch_one(
                        "sql/messages/create_message.sql",
                        (base_subject, state, month, year, internal_event_id),
                    )
                    message_id = message_row["id"]
                    console.print(f"Mensagem criada com ID: [cyan]{message_id}[/cyan]")
                except Exception as e:
                    console.print(f"[bold red]Erro ao criar a mensagem no banco de dados: {e}[/bold red]")
                    raise

                recipients = db.fetch_all("sql/contacts/select_recipients_for_message.sql", (is_test_mode, message_id))

                if not recipients:
                    console.print("[bold yellow]Atenção: Nenhum destinatário elegível encontrado no Postgres[/bold yellow]")
                    return {"status": "no_emails", "total_records": 0}

                if is_test_mode and limit > 0:
                    recipients = recipients[:limit]
                
                total_records = len(recipients)
                console.print(f"\n[bold]Total de registros para processar: [cyan]{total_records}[/cyan][/bold]")
                
                # Configurar tabela para exibir informações de envio em tempo real
                email_table = Table(title="Informações de Envio de Emails", box=ROUNDED, show_header=True)
                email_table.add_column("Email", style="cyan")
                email_table.add_column("Status", style="bold")
                email_table.add_column("Tentativas", style="yellow")
                email_table.add_column("Detalhes", style="dim")
                
                # Lista para armazenar resultados de envio para exibir depois
                email_results = []

                try:
                    class TimeoutException(Exception):
                        pass
                    
                    def timeout_handler(signum, frame):
                        raise TimeoutException
                    
                    signal.signal(signal.SIGALRM, timeout_handler)
                    configured_batch_size = self.config.email_config.get("batch_size", 200)
                    if configured_batch_size <= 0:
                        configured_batch_size = 200
                    total_batches = math.ceil(total_records / configured_batch_size) if total_records > 0 else 0
                    
                    with Progress(
                        SpinnerColumn(),
                        TextColumn("[progress.description]{task.description}"),
                        BarColumn(),
                        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                        TimeRemainingColumn(),
                        console=console
                    ) as progress:
                        progress_task = progress.add_task("[green]Processando emails...", total=total_records)
                        
                        processed_in_batch_count = 0 # Counter for actual emails processed in the current batch period
                        
                        def _iter_batches(items: List[Dict[str, Any]], size: int):
                            for i in range(0, len(items), size):
                                yield items[i:i+size]

                        notified_start = False  # only notify start after subject approval/definition
                        for batch_idx, batch_recipients in enumerate(_iter_batches(recipients, configured_batch_size)):
                            if not batch_recipients:
                                continue

                            batch_panel = Text(f"Lote {batch_idx + 1}/{int(total_batches)} - Processando {len(batch_recipients)} destinatários", style="bold blue")
                            progress.console.print(batch_panel)
                            
                            current_batch_processed_count = 0 # Emails processed in this specific non-empty batch

                            for recipient in batch_recipients:
                                progress.update(progress_task, advance=1)
                                recipient_email = str(recipient.get('email', '')).strip()
                                
                                if not recipient_email:
                                    email_results.append({
                                        'email': 'Missing email',
                                        'status': '[red]Erro[/red]',
                                        'tentativas': '0',
                                        'detalhes': 'Email ausente'
                                    })
                                    failed += 1
                                    continue
                                
                                total_send_attempts += 1
                                
                                attempts = 0
                                max_retry_minutes = 5  # Tempo máximo de tentativas em minutos
                                start_retry_time = time.time()
                                max_retry_time = start_retry_time + (max_retry_minutes * 60)
                                # Lista de padrões que indicam problemas de conexão ou rede
                                connection_errors = [
                                    "connection refused", "network is unreachable", "timed out", 
                                    "name or service not known", "temporary failure", "no route to host",
                                    "connection reset", "connection error", "network error", "socket error",
                                    "dns unavailable", "timeout", "service unavailable", "try again later", 
                                    "server busy", "connection lost", "temporarily rejected", "network down",
                                    "eof", "broken pipe", "refused", "host unreachable", "operation timed out", 
                                    "operation would block", "no address associated", "network dropped",
                                    "bad connection", "no response", "port unreachable", "cannot connect", 
                                    "temporary error", "network failure", "proxy error", "ssl error", 
                                    "name resolution", "circuit", "disconnected", "internet access", 
                                    "resource unavailable", "gateway", "routing"
                                ]
                                
                                # Define uma função para verificar se uma string contém algum padrão de erro de conexão
                                def is_connection_error(error_text):
                                    error_text = error_text.lower()
                                    return any(err_pattern in error_text for err_pattern in connection_errors)
                                
                                while True:
                                    # Verificar se atingiu o número máximo de tentativas OU o tempo máximo de tentativas
                                    if attempts >= retry_attempts_config and time.time() >= max_retry_time:
                                        progress.console.print(f"[red]❌ Número máximo de tentativas e tempo esgotados para {recipient_email}[/red]")
                                        failed += 1
                                        
                                        email_results.append({
                                            'email': recipient_email,
                                            'status': '[red]Falha[/red]',
                                            'tentativas': f"{attempts} (tempo esgotado)",
                                            'detalhes': 'Tempo máximo de tentativas esgotado (5 minutos)'
                                        })
                                        break
                                    
                                    try:
                                        attempts += 1
                                        tempo_decorrido = time.time() - start_retry_time
                                        tempo_restante = max(0, max_retry_time - time.time())
                                        
                                        progress.console.print(
                                            f"Tentando enviar para: [bold cyan]{recipient_email}[/bold cyan] "
                                            f"(Tentativa {attempts}/{retry_attempts_config}, "
                                            f"Tempo restante: {tempo_restante:.1f}s)"
                                        )
                                        signal.alarm(send_timeout)
                                        
                                        # Verificar elegibilidade do contato (defesa extra)
                                        try:
                                            with Database(self.config) as db_chk:
                                                ok_row = db_chk.fetch_one("sql/contacts/check_contact_eligible.sql", (recipient.get('id'),)) or {"ok": True}
                                                if not bool(ok_row.get("ok", True)):
                                                    email_results.append({
                                                        'email': recipient_email,
                                                        'status': '[yellow]Ignorado[/yellow]',
                                                        'tentativas': '0',
                                                        'detalhes': 'Contato marcado como unsubscribed/bounce'
                                                    })
                                                    break
                                        except Exception:
                                            pass

                                        html_content = self.process_email_template(str(template_path_obj), recipient, base_subject)
                                        log.debug(f"HTML gerado para {recipient_email} (tamanho: {len(html_content)})")
                                        if not html_content:
                                            log.error(f"HTML vazio gerado para {recipient_email}")
                                            progress.console.print(f"[red]❌ HTML vazio gerado para {recipient_email}[/red]")
                                            failed += 1
                                            email_results.append({
                                                'email': recipient_email,
                                                'status': '[red]Falha[/red]',
                                                'tentativas': '0',
                                                'detalhes': 'HTML vazio'
                                            })
                                            continue
                                        
                                        # Gerar assunto UMA ÚNICA VEZ para todo o lote, com base no primeiro corpo
                                        if final_subject_for_batch is None:
                                            console.print("[cyan]Gerando assunto do lote com base no conteúdo do primeiro email...[/cyan]")
                                            try:
                                                generated = self._generate_subject_for_body(html_content, existing_subject=base_subject)
                                            except Exception:
                                                generated = base_subject
                                            console.print(f"[bold cyan]Assunto gerado (lote):[/bold cyan] [white]{generated}[/white]")
                                            final_subject_for_batch = self._maybe_interactive_subject(
                                                generated,
                                                html_content,
                                                show_current_first=False,
                                            )
                                        email_subject = final_subject_for_batch or base_subject
                                        # Notificar início do envio em lote após definição/aprovação do assunto (apenas uma vez)
                                        if not notified_start:
                                            try:
                                                evt = self._build_event_brief()
                                                msg = "🚀 Iniciando processo de envio em lote"
                                                msg = f"{msg}\n{evt}" if evt else msg
                                                notify_telegram(msg)
                                            except Exception:
                                                pass
                                            notified_start = True
                                        
                                        log.debug(f"Enviando email para {recipient_email} - Subject: {email_subject}")
                                        log.debug(f"Tamanho do HTML antes do envio: {len(html_content)}")
                                        if len(html_content.strip()) == 0:
                                            raise ValueError("HTML vazio antes do envio")
                                            
                                        self.smtp_manager.send_email(
                                            to_email=recipient_email,
                                            subject=email_subject,
                                            content=html_content,
                                            is_html=True
                                        )
                                        
                                        signal.alarm(0)
                                        progress.console.print(f"[green]✅ Email enviado com sucesso para {recipient_email}[/green]")
                                        successful += 1
                                        
                                        email_results.append({
                                            'email': recipient_email,
                                            'status': '[green]Enviado[/green]',
                                            'tentativas': str(attempts),
                                            'detalhes': 'Enviado com sucesso'
                                        })
                                        # Atualizar estado do último enviado com sucesso
                                        try:
                                            # Criar uma nova conexão para atualizar o estado
                                            # Isso evita problemas com a conexão principal já fechada
                                            with Database(self.config) as state_db:
                                                state_db.execute(
                                                    "sql/runtime/upsert_send_state.sql",
                                                    (STATE_KEY, str(recipient.get('id'))),
                                                )
                                        except Exception as st_exc:
                                            log.warning(f"Falha ao atualizar estado de envio: {st_exc}")
                                        break
                                        
                                    except TimeoutException:
                                        signal.alarm(0)
                                        # Timeout é um problema de conexão, então ele tentará novamente se ainda estiver dentro do limite de tempo
                                        # Reduzir o número máximo de tentativas para 2 e o tempo de espera
                                        if attempts < 2 and time.time() < max_retry_time:
                                            wait_time = min(30, retry_delay_config)  # No máximo 30s entre tentativas
                                            progress.console.print(f"[yellow]⚠️ Timeout ao enviar para {recipient_email}. Tentando novamente em {wait_time}s...[/yellow]")
                                            time.sleep(wait_time)
                                            continue
                                        else:
                                            progress.console.print(f"[red]❌ Timeout ao enviar para {recipient_email} - tempo máximo excedido[/red]")
                                            failed += 1
                                            
                                            # Marcar o contato com uma tag de problema
                                            try:
                                                with Database(self.config) as tag_db:
                                                    tag_db.execute(
                                                        "sql/tags/assign_tag_problem_by_email.sql",
                                                        (recipient_email,),
                                                    )
                                            except Exception as tag_exc:
                                                log.warning(f"Falha ao marcar contato com tag de problema: {tag_exc}")
                                            
                                            email_results.append({
                                                'email': recipient_email,
                                                'status': '[red]Falha[/red]',
                                                'tentativas': str(attempts),
                                                'detalhes': f'Timeout após {send_timeout}s (tempo máximo excedido)'
                                            })
                                            break
                                        
                                    except Exception as e:
                                        signal.alarm(0)
                                        error_str = str(e).lower()
                                        error_is_connection_related = is_connection_error(error_str)
                                        
                                        # Se for erro de conexão e ainda estiver dentro do limite de tempo, tenta novamente
                                        # Reduzir o número máximo de tentativas para 2
                                        if error_is_connection_related and attempts < 2 and time.time() < max_retry_time:
                                            wait_time = min(30, retry_delay_config)  # No máximo 30s entre tentativas
                                            tempo_restante = max(0, (max_retry_time - time.time()) / 60)
                                            
                                            progress.console.print(
                                                f"[yellow]⚠️ Erro de conexão ao enviar para {recipient_email} "
                                                f"(Tentativa {attempts}): {str(e)}[/yellow]"
                                            )
                                            progress.console.print(f"[blue]🔄 Aguardando {wait_time}s antes de tentar novamente... "
                                                                  f"(Tempo restante: {tempo_restante:.1f} min)[/blue]")
                                            time.sleep(wait_time)
                                            continue
                                        # Se atingiu o número de tentativas OU não é erro de conexão OU tempo esgotado
                                        elif attempts >= 2 or not error_is_connection_related or time.time() >= max_retry_time:
                                            if error_is_connection_related:
                                                reason = "tempo máximo excedido" if time.time() >= max_retry_time else f"após {attempts} tentativas"
                                                progress.console.print(f"[red]❌ Falha de conexão ao enviar para {recipient_email} - {reason}: {str(e)}[/red]")
                                            else:
                                                progress.console.print(f"[red]❌ Falha ao enviar para {recipient_email}: {str(e)}[/red]")
                                            
                                            # Marcar o contato com uma tag de problema para erros de conexão
                                            if error_is_connection_related:
                                                try:
                                                    with Database(self.config) as tag_db:
                                                        tag_db.execute(
                                                            "sql/tags/assign_tag_problem_by_email.sql",
                                                            (recipient_email,),
                                                        )
                                                except Exception as tag_exc:
                                                    log.warning(f"Falha ao marcar contato com tag de problema: {tag_exc}")
                                            
                                            failed += 1
                                            email_results.append({
                                                'email': recipient_email,
                                                'status': '[red]Falha[/red]',
                                                'tentativas': str(attempts),
                                                'detalhes': str(e)[:50] + ('...' if len(str(e)) > 50 else '')
                                            })
                                            break
                                        else:
                                            progress.console.print(f"[yellow]⚠️ Falha temporária ao enviar para {recipient_email} (Tentativa {attempts}/2): {str(e)}[/yellow]")
                                            if retry_delay_config > 0:
                                                wait_time = min(30, retry_delay_config)  # No máximo 30s entre tentativas
                                                progress.console.print(f"[yellow]Aguardando {wait_time}s antes da próxima tentativa...[/yellow]")
                                                time.sleep(wait_time)
                                
                                # Increment counter for emails actually attempted in this batch
                                if recipient_email: # Ensure we count only if there was an email to process
                                    current_batch_processed_count +=1
                            
                            # NEW PAUSE LOGIC: Pause after processing a non-empty batch, if it's not the last batch and delay is positive
                            # And if actual emails were processed in this batch.
                            if current_batch_processed_count > 0 and total_batches > 0 and batch_idx < total_batches - 1 and pause_duration_after_attempts > 0:
                                pause_message = f"Pausa de {pause_duration_after_attempts}s após o lote {batch_idx + 1}/{int(total_batches)} (processou {current_batch_processed_count} emails)"
                                progress.console.print(f"[blue]{pause_message}[/blue]")
                                time.sleep(pause_duration_after_attempts)
                        # Nada a marcar no fluxo simplificado
                        
                except KeyboardInterrupt:
                    console.print("\n[bold yellow]Processo interrompido pelo usuário.[/bold yellow]")
                finally:
                    signal.alarm(0)
                
                end_time = time.time()
                duration = end_time - start_time
                
                # Exibir resultados em uma tabela formatada
                console.rule("[bold blue]Relatório de Envio de Emails[/bold blue]")
                
                # Mostrar tabela de resultados
                for result in email_results:
                    email_table.add_row(
                        result['email'],
                        result['status'],
                        result['tentativas'],
                        result['detalhes']
                    )
                
                console.print(email_table)
                
                # Tabela de resumo
                summary_table = Table(title="Resumo de Envio", box=ROUNDED)
                summary_table.add_column("Métrica", style="cyan")
                summary_table.add_column("Valor", style="bold")
                
                # Calcular métricas adicionais
                total_attempts = sum(int(r.get('tentativas', '1').split()[0]) for r in email_results if r.get('tentativas', '').strip() != '')
                avg_attempts_per_email = total_attempts / max(1, successful + failed)
                total_connection_errors = sum(1 for r in email_results if 'tempo' in r.get('detalhes', '').lower() or 'timeout' in r.get('detalhes', '').lower())
                tempo_total_min = duration / 60
                
                summary_table.add_row("Total de Registros", str(total_records))
                summary_table.add_row("Emails Enviados com Sucesso", f"[green]{successful}[/green]")
                summary_table.add_row("Emails com Falha", f"[red]{failed}[/red]")
                # Descadastros/bounces já são filtrados na SQL
                summary_table.add_row("Total de Tentativas", str(total_attempts))
                summary_table.add_row("Média de Tentativas por Email", f"{avg_attempts_per_email:.2f}")
                summary_table.add_row("Falhas por Erro de Conexão", str(total_connection_errors))
                summary_table.add_row("Descadastrados (ignorados)", str(unsub_ignored))
                summary_table.add_row("Bounces (ignorados)", str(bounce_ignored))
                summary_table.add_row("Tempo Total de Execução", f"{tempo_total_min:.2f} minutos ({duration:.1f}s)")
                
                console.print(summary_table)
                
                # Gerar relatório usando o report_generator
                report_data = self.generate_report(
                    start_time,
                    end_time,
                    total_send_attempts,
                    successful,
                    failed,
                    ignored_unsubscribed=unsub_ignored,
                    ignored_bounces=bounce_ignored,
                )
                
                console.print(f"Relatório salvo em: [bold cyan]{report_data.get('report_file', 'N/A')}[/bold cyan]")
                # Notificação Telegram com sumário
                try:
                    notify_telegram(
                        (
                            f"✅ Envio em lote concluído. Total: {total_records} | "
                            f"Sucesso: {successful} | Falhas: {failed} | "
                            f"Descadastrados ignorados: {unsub_ignored} | "
                            f"Bounces ignorados: {bounce_ignored} | "
                            f"Tempo: {duration:.1f}s"
                        )
                    )
                except Exception:
                    pass
                
                return report_data
        
        except Exception as e:
            import traceback
            log.error(f"Erro no processo de envio de emails: {str(e)}")
            log.debug(traceback.format_exc())
            raise