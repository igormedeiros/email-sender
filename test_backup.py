import os
import pandas as pd
import csv
from pathlib import Path
from src.config import Config
from src.email_service import EmailService

# Função para criar um arquivo CSV de teste
def create_test_csv(file_path, num_entries=10):
    """Cria um arquivo CSV de teste com algumas entradas"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Criar dados de teste
    data = []
    for i in range(num_entries):
        # Metade com 'enviado' = 'ok'
        if i < num_entries // 2:
            data.append({
                'email': f'test{i}@example.com',
                'nome': f'Teste {i}',
                'enviado': 'ok',
                'falhou': ''
            })
        # A outra metade com 'falhou' = 'ok'
        else:
            data.append({
                'email': f'test{i}@example.com',
                'nome': f'Teste {i}',
                'enviado': '',
                'falhou': 'ok'
            })
    
    # Criar o DataFrame e salvar como CSV
    df = pd.DataFrame(data)
    df.to_csv(file_path, index=False)
    print(f"Arquivo de teste criado: {file_path} com {num_entries} entradas")

# Limpar diretórios de teste e backup
test_dir = "data/test"
test_file = f"{test_dir}/test_flags.csv"
backup_dir = "backup"

# Criar diretórios
os.makedirs(test_dir, exist_ok=True)
os.makedirs(backup_dir, exist_ok=True)

# Remover arquivos anteriores, se existirem
if os.path.exists(test_file):
    os.remove(test_file)
    print(f"Arquivo de teste anterior removido: {test_file}")

backup_file = f"{backup_dir}/test_flags.csv.bak"
if os.path.exists(backup_file):
    os.remove(backup_file)
    print(f"Arquivo de backup anterior removido: {backup_file}")

# Criar arquivo CSV de teste
create_test_csv(test_file, 10)

# Mostrar conteúdo do arquivo original
print("\nConteúdo do arquivo original:")
df_original = pd.read_csv(test_file)
print(df_original)

# Instanciar as classes necessárias
config = Config()
email_service = EmailService(config)

# Executar a função de limpeza de flags
print("\nExecutando a função clear_sent_flags...")
try:
    cleared_count = email_service.clear_sent_flags(test_file)
    print(f"✅ {cleared_count} flags foram limpas com sucesso!")
    
    # Verificar se o backup foi criado
    if os.path.exists(backup_file):
        print(f"✅ Backup criado com sucesso: {backup_file}")
        
        # Mostrar conteúdo do arquivo de backup
        print("\nConteúdo do arquivo de backup:")
        df_backup = pd.read_csv(backup_file)
        print(df_backup)
        
        # Verificar se o backup é idêntico ao original
        if df_backup.equals(df_original):
            print("✅ O backup é idêntico ao arquivo original!")
        else:
            print("❌ O backup NÃO é idêntico ao arquivo original")
    else:
        print(f"❌ Backup não encontrado: {backup_file}")
    
    # Mostrar conteúdo do arquivo atualizado
    print("\nConteúdo do arquivo após limpar as flags:")
    df_updated = pd.read_csv(test_file)
    print(df_updated)
    
    # Verificar se as flags foram realmente limpas
    enviado_ok = len(df_updated[df_updated['enviado'] == 'ok'])
    falhou_ok = len(df_updated[df_updated['falhou'] == 'ok'])
    
    if enviado_ok == 0 and falhou_ok == 0:
        print("✅ Todas as flags foram limpas corretamente!")
    else:
        print(f"❌ Algumas flags não foram limpas: {enviado_ok} 'enviado=ok', {falhou_ok} 'falhou=ok'")
    
except Exception as e:
    print(f"❌ Erro ao executar o teste: {str(e)}") 