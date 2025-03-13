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
        
    try:
        file_path = "data/test_descadastros.csv"
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Garante que o diretório existe
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # Verifica se o arquivo existe
        file_exists = os.path.exists(file_path) and os.path.getsize(file_path) > 0
        
        if not file_exists:
            # Cria o arquivo com cabeçalho e adiciona o email com a data
            with open(file_path, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerow(['email', 'data_descadastro'])
                writer.writerow([email, data_atual])
            return True
            
        # Adiciona o email ao final do arquivo com a data atual
        with open(file_path, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([email, data_atual])
            
        return True
    except Exception as e:
        print(f"Erro ao adicionar email à lista de descadastros: {str(e)}")
        return False

# Limpar o arquivo de teste anterior
if os.path.exists("data/test_descadastros.csv"):
    os.remove("data/test_descadastros.csv")
    print("Arquivo de teste anterior removido.")

# Testar a função
print("Adicionando email de teste...")
result = add_to_test_unsubscribe_list("teste@exemplo.com")
print(f"Resultado: {result}")

# Adicionar um segundo email
print("Adicionando segundo email de teste...")
result = add_to_test_unsubscribe_list("segundo@exemplo.com")
print(f"Resultado: {result}")

# Verificar se o arquivo foi criado e qual é o seu conteúdo
if os.path.exists("data/test_descadastros.csv"):
    print("\nArquivo criado com sucesso!")
    
    # Ler o conteúdo do arquivo
    with open("data/test_descadastros.csv", 'r', encoding='utf-8') as file:
        print("\nConteúdo do arquivo:")
        print(file.read())
    
    # Ler usando pandas para confirmar a estrutura
    try:
        df = pd.read_csv("data/test_descadastros.csv")
        print("\nEstrutura do DataFrame:")
        print(df.head())
    except Exception as e:
        print(f"\nErro ao ler com pandas: {str(e)}")
else:
    print("\nErro: O arquivo não foi criado.") 