import os
import re
from typing import Dict, List, Any, Optional, Set, Union
import jinja2

def get_template_environment(
    template_dir: str, 
    **options
) -> jinja2.Environment:
    """
    Cria um ambiente Jinja2 para renderização de templates.
    
    Args:
        template_dir: Diretório contendo os templates
        **options: Opções adicionais para o ambiente
        
    Returns:
        Ambiente Jinja2 configurado
    """
    loader = jinja2.FileSystemLoader(template_dir)
    env = jinja2.Environment(loader=loader, **options)
    return env

def load_template(
    template_dir: str, 
    template_name: str
) -> jinja2.Template:
    """
    Carrega um template do sistema de arquivos.
    
    Args:
        template_dir: Diretório contendo os templates
        template_name: Nome do arquivo de template
        
    Returns:
        Template carregado
        
    Raises:
        jinja2.exceptions.TemplateNotFound: Se o template não for encontrado
    """
    env = get_template_environment(template_dir)
    template = env.get_template(template_name)
    return template

def render_template(
    template_dir: str,
    template_name: str,
    context: Optional[Dict[str, Any]] = None,
    strict: bool = False
) -> str:
    """
    Renderiza um template com o contexto fornecido.
    
    Args:
        template_dir: Diretório contendo os templates
        template_name: Nome do arquivo de template
        context: Dicionário com variáveis para renderização
        strict: Se True, falha se variáveis estiverem ausentes
        
    Returns:
        Template renderizado como string
        
    Raises:
        ValueError: Se strict=True e variáveis obrigatórias estiverem ausentes
    """
    if context is None:
        context = {}
    
    # Validar variáveis se strict=True
    if strict:
        variables = get_template_variables(template_dir, template_name)
        validate_template_variables(variables, context)
    
    # Carregar e renderizar template
    template = load_template(template_dir, template_name)
    return template.render(**context)

def get_template_variables(
    template_dir: str,
    template_name: str
) -> Set[str]:
    """
    Extrai todas as variáveis utilizadas em um template.
    
    Args:
        template_dir: Diretório contendo os templates
        template_name: Nome do arquivo de template
        
    Returns:
        Conjunto com nomes de variáveis utilizadas no template
    """
    # Carregar o conteúdo do template
    template_path = os.path.join(template_dir, template_name)
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"Template não encontrado: {template_path}")
    
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Padrão para identificar variáveis {{ var }}
    var_pattern = r'{{\s*([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*)\s*}}'
    # Padrão para variáveis em condicionais {% if var %}
    cond_pattern = r'{%\s*if\s+([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*)\s*%}'
    # Padrão para variáveis em expressões condicionais {% if var ou condicional com var %} incluindo operadores
    extended_cond_pattern = r'{%\s*if\s+.*?([a-zA-Z0-9_]+).*?%}'
    # Padrão para loops {% for item in items %}
    loop_pattern = r'{%\s*for\s+[a-zA-Z0-9_]+\s+in\s+([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)*)\s*%}'
    
    # Extrair todas as variáveis
    variables = set()
    
    # Adicionar variáveis diretas {{ var }}
    for match in re.finditer(var_pattern, content):
        var_name = match.group(1).split('.')[0]  # Pegar apenas o nome base da variável
        variables.add(var_name)
    
    # Adicionar variáveis de condicionais {% if var %}
    for match in re.finditer(cond_pattern, content):
        var_name = match.group(1).split('.')[0]
        variables.add(var_name)
    
    # Adicionar variáveis de expressões condicionais mais complexas
    for match in re.finditer(extended_cond_pattern, content):
        var_name = match.group(1).split('.')[0]
        variables.add(var_name)
    
    # Adicionar variáveis de loops {% for item in items %}
    for match in re.finditer(loop_pattern, content):
        var_name = match.group(1).split('.')[0]
        variables.add(var_name)
    
    return variables

def validate_template_variables(
    required_vars: Union[List[str], Set[str]],
    context: Dict[str, Any],
    allow_empty: bool = True
) -> bool:
    """
    Verifica se todas as variáveis requeridas estão presentes no contexto.
    
    Args:
        required_vars: Lista ou conjunto de variáveis requeridas
        context: Dicionário com variáveis para renderização
        allow_empty: Se False, valores vazios não são aceitos
        
    Returns:
        True se todas as variáveis estiverem presentes
        
    Raises:
        ValueError: Se alguma variável estiver ausente
    """
    missing_vars = []
    
    for var in required_vars:
        if var not in context:
            missing_vars.append(var)
        elif not allow_empty and not context[var]:
            missing_vars.append(f"{var} (vazio)")
    
    if missing_vars:
        raise ValueError(f"Variáveis ausentes no contexto: {', '.join(missing_vars)}")
    
    return True 