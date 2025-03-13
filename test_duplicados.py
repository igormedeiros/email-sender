import os
import csv
from datetime import datetime
import pandas as pd

def add_to_test_unsubscribe_list(email: str) -> bool:
    """
    Adiciona um email à lista de descadastros de teste.
    
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
        file_path = "data/test_duplicados.csv"
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
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

# Testes para verificar a validação de duplicação

# Limpar o arquivo de teste anterior
if os.path.exists("data/test_duplicados.csv"):
    os.remove("data/test_duplicados.csv")
    print("Arquivo de teste anterior removido.")

print("\n===== TESTE 1: Adicionar email pela primeira vez =====")
result = add_to_test_unsubscribe_list("teste@exemplo.com")
print(f"Resultado: {result}")

print("\n===== TESTE 2: Adicionar email com letras maiúsculas =====")
result = add_to_test_unsubscribe_list("TESTE@exemplo.com")
print(f"Resultado: {result}")

print("\n===== TESTE 3: Adicionar email com espaços =====")
result = add_to_test_unsubscribe_list(" teste@exemplo.com ")
print(f"Resultado: {result}")

print("\n===== TESTE 4: Adicionar um email diferente =====")
result = add_to_test_unsubscribe_list("outro@exemplo.com")
print(f"Resultado: {result}")

# Verificar o arquivo final
if os.path.exists("data/test_duplicados.csv"):
    print("\nConteúdo final do arquivo:")
    
    # Ler usando pandas para confirmar a estrutura
    try:
        df = pd.read_csv("data/test_duplicados.csv")
        print(df)
    except Exception as e:
        print(f"Erro ao ler com pandas: {str(e)}")
        
        # Tentar ler como texto
        with open("data/test_duplicados.csv", 'r', encoding='utf-8') as file:
            print(file.read())
else:
    print("\nErro: O arquivo não foi criado.") 