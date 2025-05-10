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
        
    # Normaliza o email (lowercase e sem espaços extras)
    email = email.lower().strip()
        
    try:
        file_path = get_unsubscribe_file()
        data_atual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Garante que o diretório existe
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Verifica se o arquivo existe e não está vazio
        file_exists = os.path.exists(file_path) and os.path.getsize(file_path) > 0
        
        if not file_exists:
            # Cria o arquivo com cabeçalho e adiciona o email com a data
            print(f"Criando novo arquivo de descadastros e adicionando {email}")
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['email', 'data_descadastro'])
                writer.writerow([email, data_atual])
            return True
            
        # Verifica se o email já está na lista
        emails = []
        try:
            df = pd.read_csv(file_path)
            # Se o arquivo já tem cabeçalho, tenta ler a coluna email
            if 'email' in df.columns:
                # Converte todos os emails para lowercase e remove espaços
                emails = [e.lower().strip() if isinstance(e, str) else str(e).lower().strip() 
                          for e in df['email'].tolist()]
            # Se não tem cabeçalho, assume que a primeira coluna é email
            else:
                # Cria um novo arquivo com cabeçalho e preserva os emails existentes
                print("Arquivo sem cabeçalho detectado. Reformatando...")
                with open(file_path, 'r', encoding='utf-8') as file:
                    existing_emails = [line.strip().split(',')[0].lower().strip() 
                                       for line in file if line.strip()]
                
                with open(file_path, 'w', newline='', encoding='utf-8') as file:
                    writer = csv.writer(file)
                    writer.writerow(['email', 'data_descadastro'])
                    for old_email in existing_emails:
                        if old_email and old_email != 'email':  # Evita linha vazia ou cabeçalho antigo
                            writer.writerow([old_email, ''])  # Data vazia para registros antigos
                    
                emails = existing_emails
        except Exception as e:
            print(f"Erro ao ler arquivo de descadastros: {str(e)}")
            # Se não conseguir ler, assume que o arquivo está vazio ou mal formatado
            # Recria o arquivo
            print("Recriando arquivo de descadastros devido a erro de leitura")
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['email', 'data_descadastro'])
            emails = []
            
        if email in emails:
            print(f"Email {email} já está na lista de descadastros. Ignorando.")
            return True  # Email já está na lista
            
        # Adiciona o email ao final do arquivo com a data atual
        print(f"Adicionando novo email à lista de descadastros: {email}")
        with open(file_path, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([email, data_atual])
            
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
    
    # Normaliza o email (lowercase)
    email = email.lower().strip()
        
    try:
        file_path = get_unsubscribe_file()
        
        # Verifica se o arquivo existe
        if not os.path.exists(file_path):
            return True  # Se o arquivo não existe, não há nada para remover
            
        # Lê o arquivo e remove o email
        try:
            df = pd.read_csv(file_path)
            # Verifica se o CSV possui a coluna 'email'
            if 'email' in df.columns:
                # Converte todos os emails para lowercase para fazer a comparação case insensitive
                df['email_lower'] = df['email'].astype(str).str.lower().str.strip()
                # Filtra mantendo apenas os emails diferentes do email buscado
                df = df[df['email_lower'] != email]
                # Remove a coluna temporária
                df = df.drop(columns=['email_lower'])
            else:
                # Se não tiver cabeçalho, assume primeira coluna como email
                # Cria um dataframe com cabeçalho
                df.columns = ['email'] if len(df.columns) == 1 else ['email', 'data_descadastro']
                df['email_lower'] = df['email'].astype(str).str.lower().str.strip()
                df = df[df['email_lower'] != email]
                df = df.drop(columns=['email_lower'])
        except Exception as e:
            print(f"Erro ao ler arquivo CSV: {str(e)}")
            # Tenta usar o método antigo com case insensitive
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = []
                for line in file:
                    parts = line.strip().split(',')
                    if len(parts) >= 1:
                        email_in_file = parts[0].lower().strip()
                        if email_in_file != email and email_in_file != 'email':
                            lines.append(line)
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write('email,data_descadastro\n')  # Adiciona cabeçalho
                for line in lines:
                    file.write(line)
                        
            return True
        
        # Salva o arquivo atualizado
        df.to_csv(file_path, index=False)
        
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
    """Rota para processar recadastros - Funcionalidade desativada"""
    return render_template(
        'error.html',
        title="Funcionalidade indisponível",
        heading="Funcionalidade indisponível",
        error_message="A funcionalidade de recadastro não está mais disponível.",
        current_year=datetime.datetime.now().year
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
