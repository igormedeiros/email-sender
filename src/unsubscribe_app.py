from flask import Flask, request, render_template, redirect, url_for
import os
import csv
import pandas as pd
from pathlib import Path
from typing import List, Optional
import datetime

app = Flask(__name__, template_folder='../templates')

# Funções auxiliares

def get_unsubscribe_file() -> str:
    """Retorna o caminho para o arquivo de descadastros."""
    # Primeiro verifica na pasta da aplicação
    base_dir = Path(__file__).parent.parent
    return str(base_dir / "data" / "descadastros.csv")

def add_to_unsubscribe_list(email: str) -> bool:
    """
    Adiciona um email à lista de descadastros.
    
    Args:
        email: Email a ser adicionado
        
    Returns:
        True se o email foi adicionado com sucesso, False caso contrário
    """
    if not email:
        return False
        
    try:
        file_path = get_unsubscribe_file()
        
        # Verifica se o arquivo existe
        if not os.path.exists(file_path):
            # Cria o arquivo e adiciona o email
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                file.write(email + '\n')
            return True
            
        # Verifica se o email já está na lista
        emails = []
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                emails = [line.strip() for line in file]
        except Exception:
            # Se não conseguir ler, assume que o arquivo está vazio
            pass
            
        if email in emails:
            return True  # Email já está na lista
            
        # Adiciona o email ao final do arquivo
        with open(file_path, 'a', newline='', encoding='utf-8') as file:
            file.write(email + '\n')
            
        return True
    except Exception as e:
        print(f"Erro ao adicionar email à lista de descadastros: {str(e)}")
        return False

def remove_from_unsubscribe_list(email: str) -> bool:
    """
    Remove um email da lista de descadastros.
    
    Args:
        email: Email a ser removido
        
    Returns:
        True se o email foi removido com sucesso, False caso contrário
    """
    if not email:
        return False
        
    try:
        file_path = get_unsubscribe_file()
        
        # Verifica se o arquivo existe
        if not os.path.exists(file_path):
            return True  # Se o arquivo não existe, não há nada para remover
            
        # Lê o arquivo e remove o email
        df = pd.read_csv(file_path, header=None, names=['email'])
        df = df[df['email'].str.strip() != email.strip()]
        
        # Salva o arquivo atualizado
        df.to_csv(file_path, index=False, header=False)
        
        return True
    except Exception as e:
        print(f"Erro ao remover email da lista de descadastros: {str(e)}")
        return False

# Rotas

@app.route('/')
def index():
    return 'API de descadastro está funcionando. Use /unsubscribe?email=seu@email.com para descadastrar.'

@app.route('/unsubscribe')
def unsubscribe():
    """Rota para processar descadastros"""
    email = request.args.get('email')
    
    if not email:
        return render_template(
            'error.html',
            title="Erro - Descadastro",
            heading="Ocorreu um erro",
            error_message="Email não fornecido. Por favor, use o link correto.",
            current_year=datetime.datetime.now().year
        )
    
    # Tenta adicionar o email à lista de descadastros
    success = add_to_unsubscribe_list(email)
    
    if not success:
        return render_template(
            'error.html',
            title="Erro - Descadastro",
            heading="Ocorreu um erro",
            error_message="Não foi possível processar seu descadastro. Por favor, tente novamente.",
            current_year=datetime.datetime.now().year
        )
    
    # Gera a URL para o recadastro
    subscribe_url = url_for('resubscribe', _external=True)
    
    return render_template(
        'descadastro.html',
        title="Descadastro confirmado",
        heading="Descadastro Confirmado",
        email=email,
        subscribe_url=subscribe_url,
        current_year=datetime.datetime.now().year
    )

@app.route('/resubscribe')
def resubscribe():
    """Rota para processar recadastros"""
    email = request.args.get('email')
    
    if not email:
        return render_template(
            'error.html',
            title="Erro - Recadastro",
            heading="Ocorreu um erro",
            error_message="Email não fornecido. Por favor, use o link correto.",
            current_year=datetime.datetime.now().year
        )
    
    # Tenta remover o email da lista de descadastros
    success = remove_from_unsubscribe_list(email)
    
    if not success:
        return render_template(
            'error.html',
            title="Erro - Recadastro",
            heading="Ocorreu um erro",
            error_message="Não foi possível processar seu recadastro. Por favor, tente novamente.",
            current_year=datetime.datetime.now().year
        )
    
    return render_template(
        'recadastro.html',
        title="Recadastro confirmado",
        heading="Recadastro Confirmado",
        email=email,
        current_year=datetime.datetime.now().year
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
