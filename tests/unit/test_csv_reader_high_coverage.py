import pytest
import pandas as pd
import os
import tempfile
import signal
import sys
import shutil
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open, call, ANY
from io import StringIO

from src.utils.csv_reader import CSVReader

@pytest.fixture
def sample_csv_content():
    """Cria conteúdo CSV de exemplo para testes"""
    return """id,nome,email,enviado,falhou
1,João Silva,joao@example.com,,
2,Maria Santos,maria@example.com,ok,
3,Pedro Alves,pedro@example.com,,ok
4,Ana Lima,ana@example.com,,
5,Carlos Ferreira,carlos@example.com,ok,
"""

@pytest.fixture
def sample_csv_with_unsubscribe():
    """Cria conteúdo CSV de exemplo com coluna de descadastro"""
    return """id,nome,email,enviado,falhou,descadastro
1,João Silva,joao@example.com,,,
2,Maria Santos,maria@example.com,ok,,
3,Pedro Alves,pedro@example.com,,ok,
4,Ana Lima,ana@example.com,,,S
5,Carlos Ferreira,carlos@example.com,ok,,
"""

@pytest.fixture
def temp_csv_file(sample_csv_content):
    """Cria um arquivo CSV temporário para testes"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as temp_file:
        temp_file.write(sample_csv_content)
        temp_path = temp_file.name
    
    yield temp_path
    
    # Limpar após os testes
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(f"{temp_path}.bak"):
            os.remove(f"{temp_path}.bak")
        if os.path.exists(f"{temp_path}.temp.csv"):
            os.remove(f"{temp_path}.temp.csv")
    except:
        pass

@pytest.fixture
def temp_csv_with_unsubscribe(sample_csv_with_unsubscribe):
    """Cria um arquivo CSV temporário com coluna de descadastro"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as temp_file:
        temp_file.write(sample_csv_with_unsubscribe)
        temp_path = temp_file.name
    
    yield temp_path
    
    # Limpar após os testes
    try:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(f"{temp_path}.bak"):
            os.remove(f"{temp_path}.bak")
        if os.path.exists(f"{temp_path}.temp.csv"):
            os.remove(f"{temp_path}.temp.csv")
    except:
        pass

@pytest.fixture
def csv_reader(temp_csv_file):
    """Cria uma instância de CSVReader para testes"""
    # Desativar os handlers de sinal para testes
    with patch('src.utils.csv_reader.signal.signal'):
        csv_reader = CSVReader(temp_csv_file)
        yield csv_reader
        csv_reader.cleanup()

def test_csvreader_init(temp_csv_file):
    """Testa a inicialização do CSVReader"""
    with patch('src.utils.csv_reader.signal.signal') as mock_signal:
        reader = CSVReader(temp_csv_file)
        
        # Verificar os atributos básicos
        assert reader.file_path == temp_csv_file
        assert reader.batch_size == 100  # valor padrão
        assert reader.backup_path == f"{temp_csv_file}.bak"
        
        # Verificar se o backup foi criado
        assert os.path.exists(reader.backup_path)
        
        # Verificar se o sinal foi configurado
        mock_signal.assert_called_with(signal.SIGINT, ANY)
        
        # Limpar
        reader.cleanup()

def test_csvreader_init_with_custom_batch_size(temp_csv_file):
    """Testa a inicialização do CSVReader com tamanho de lote personalizado"""
    with patch('src.utils.csv_reader.signal.signal'):
        reader = CSVReader(temp_csv_file, batch_size=50)
        
        # Verificar o tamanho de lote personalizado
        assert reader.batch_size == 50
        
        # Limpar
        reader.cleanup()

def test_csvreader_init_nonexistent_file():
    """Testa a inicialização do CSVReader com arquivo inexistente"""
    with pytest.raises(FileNotFoundError):
        CSVReader('arquivo_inexistente.csv')

def test_detect_separator():
    """Testa a detecção do separador do CSV"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as temp_file:
        # CSV com vírgula
        temp_file.write("id,nome,email\n1,Joao,joao@example.com\n")
        temp_path = temp_file.name
    
    try:
        with patch('src.utils.csv_reader.signal.signal'):
            reader = CSVReader(temp_path)
            # Acesso direto ao método protegido para teste
            separator = reader._detect_separator(temp_path)
            assert separator == ','
            reader.cleanup()
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(f"{temp_path}.bak"):
            os.remove(f"{temp_path}.bak")

    # Teste com ponto e vírgula
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as temp_file:
        temp_file.write("id;nome;email\n1;Joao;joao@example.com\n")
        temp_path = temp_file.name
    
    try:
        with patch('src.utils.csv_reader.signal.signal'):
            reader = CSVReader(temp_path)
            separator = reader._detect_separator(temp_path)
            assert separator == ';'
            reader.cleanup()
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        if os.path.exists(f"{temp_path}.bak"):
            os.remove(f"{temp_path}.bak")

def test_total_records(csv_reader):
    """Testa a contagem de registros a enviar"""
    # Deve ter 2 registros para enviar (João e Ana, que têm enviado='')
    assert csv_reader.total_records == 2

def test_total_records_with_unsubscribe(temp_csv_with_unsubscribe):
    """Testa a contagem de registros a enviar com descadastro"""
    with patch('src.utils.csv_reader.signal.signal'):
        reader = CSVReader(temp_csv_with_unsubscribe)
        
        # Deve ter 1 registro para enviar (João, pois Ana está descadastrada)
        assert reader.total_records == 1
        
        reader.cleanup()

def test_get_batches(csv_reader):
    """Testa a obtenção de lotes de registros"""
    batches = list(csv_reader.get_batches())
    
    # Deve retornar 1 lote com 2 registros (João e Ana)
    assert len(batches) == 1
    assert len(batches[0]) == 2
    
    # Verificar os emails que estão no lote
    emails = [record['email'] for record in batches[0]]
    assert 'joao@example.com' in emails
    assert 'ana@example.com' in emails

def test_get_batches_with_unsubscribe(temp_csv_with_unsubscribe):
    """Testa a obtenção de lotes de registros com descadastro"""
    with patch('src.utils.csv_reader.signal.signal'):
        reader = CSVReader(temp_csv_with_unsubscribe)
        
        batches = list(reader.get_batches())
        
        # Deve retornar 1 lote com 1 registro (João, pois Ana está descadastrada)
        assert len(batches) == 1
        assert len(batches[0]) == 1
        
        # Verificar o email que está no lote
        assert batches[0][0]['email'] == 'joao@example.com'
        
        reader.cleanup()

def test_mark_as_sent(csv_reader, temp_csv_file):
    """Testa a marcação de email como enviado"""
    # Mock do método _atomic_save para evitar a escrita real
    with patch.object(csv_reader, '_atomic_save', return_value=True) as mock_save:
        csv_reader.mark_as_sent('joao@example.com')
        
        # Verificar se o método _atomic_save foi chamado
        mock_save.assert_called_once()
        
        # Verificar se o registro foi marcado
        idx = csv_reader.df[csv_reader.df['email'] == 'joao@example.com'].index
        assert len(idx) > 0
        assert csv_reader.df.loc[idx[0], 'enviado'] == 'ok'

def test_mark_as_failed(csv_reader, temp_csv_file):
    """Testa a marcação de email como falha"""
    # Mock do método _atomic_save para evitar a escrita real
    with patch.object(csv_reader, '_atomic_save', return_value=True) as mock_save:
        csv_reader.mark_as_failed('joao@example.com')
        
        # Verificar se o método _atomic_save foi chamado
        mock_save.assert_called_once()
        
        # Verificar se o registro foi marcado
        idx = csv_reader.df[csv_reader.df['email'] == 'joao@example.com'].index
        assert len(idx) > 0
        assert csv_reader.df.loc[idx[0], 'falhou'] == 'ok'

def test_mark_nonexistent_email(csv_reader):
    """Testa a marcação de email inexistente"""
    # Mock do método _atomic_save para evitar a escrita real
    with patch.object(csv_reader, '_atomic_save', return_value=True) as mock_save:
        with patch('src.utils.csv_reader.log.warning') as mock_log:
            csv_reader.mark_as_sent('inexistente@example.com')
            
            # Verificar se o aviso foi logado
            mock_log.assert_called_once_with('Email inexistente@example.com not found in CSV file')
            # Verificar que _atomic_save não foi chamado
            mock_save.assert_not_called()

def test_clear_sent_flags_all(csv_reader):
    """Testa a limpeza de todas as flags"""
    # Mock para evitar a escrita real e outras operações
    with patch('shutil.copy2') as mock_copy:
        with patch.object(csv_reader, '_atomic_save', return_value=True) as mock_save:
            csv_reader.clear_sent_flags(clear_all=True)
            
            # Verificar se os métodos foram chamados
            mock_copy.assert_called_once()
            mock_save.assert_called_once()
            
            # Verificar se as colunas foram limpas
            assert (csv_reader.df['enviado'] == '').all()
            assert (csv_reader.df['falhou'] == '').all()

def test_clear_sent_flags_preserve_failed(csv_reader):
    """Testa a limpeza apenas das flags de envio, preservando falhas"""
    # Garantir que temos um registro marcado como falha
    idx = csv_reader.df[csv_reader.df['email'] == 'pedro@example.com'].index
    csv_reader.df.loc[idx, 'falhou'] = 'ok'
    
    # Mock para evitar a escrita real e outras operações
    with patch('shutil.copy2') as mock_copy:
        with patch.object(csv_reader, '_atomic_save', return_value=True) as mock_save:
            csv_reader.clear_sent_flags(clear_all=False)
            
            # Verificar se os métodos foram chamados
            mock_copy.assert_called_once()
            mock_save.assert_called_once()
            
            # Verificar se as colunas foram corretamente modificadas
            assert (csv_reader.df['enviado'] == '').all()
            
            # Verificar se o status de falha foi preservado
            idx = csv_reader.df[csv_reader.df['email'] == 'pedro@example.com'].index
            assert csv_reader.df.loc[idx[0], 'falhou'] == 'ok'

def test_atomic_save_success(csv_reader):
    """Testa o salvamento atômico com sucesso"""
    temp_path = f"{csv_reader.file_path}.temp.csv"
    final_path = csv_reader.file_path
    
    # Mock para evitar a escrita real
    with patch('pandas.DataFrame.to_csv') as mock_to_csv:
        with patch('os.path.exists', return_value=True) as mock_exists:
            with patch('os.replace') as mock_replace:
                # Testar o salvamento
                result = csv_reader._atomic_save(temp_path, final_path)
                
                # Verificar se os métodos foram chamados
                mock_to_csv.assert_called_once()
                mock_replace.assert_called_once_with(temp_path, final_path)
                
                # Verificar se o resultado é True (sucesso)
                assert result is True

def test_atomic_save_failure(csv_reader):
    """Testa o salvamento atômico com falha"""
    temp_path = f"{csv_reader.file_path}.temp.csv"
    final_path = csv_reader.file_path
    
    # Mock para simular falha no DataFrame.to_csv()
    with patch('pandas.DataFrame.to_csv', side_effect=Exception("Erro ao salvar")) as mock_to_csv:
        with patch.object(csv_reader, '_restore_backup') as mock_restore:
            # Testar o salvamento
            result = csv_reader._atomic_save(temp_path, final_path)
            
            # Verificar se to_csv foi chamado
            mock_to_csv.assert_called_once()
            
            # Verificar se o backup foi restaurado
            mock_restore.assert_called_once()
            
            # Verificar se o resultado é False (falha)
            assert result is False

def test_should_save(csv_reader):
    """Testa a verificação se deve salvar"""
    # Definir último salvamento para mais de 5 minutos atrás
    csv_reader.last_save = time.time() - 301  # 301 segundos = 5 minutos e 1 segundo
    
    # Deve retornar True (deve salvar)
    assert csv_reader._should_save() is True
    
    # Após verificar, last_save deve ter sido atualizado
    assert time.time() - csv_reader.last_save < 2  # menos de 2 segundos atrás
    
    # Agora não deve salvar
    assert csv_reader._should_save() is False

def test_periodic_save(csv_reader):
    """Testa o salvamento periódico"""
    # Mock para simular que deve salvar
    with patch.object(csv_reader, '_should_save', return_value=True) as mock_should_save:
        with patch.object(csv_reader, '_atomic_save', return_value=True) as mock_atomic_save:
            # Testar o salvamento periódico
            csv_reader._periodic_save()
            
            # Verificar se os métodos foram chamados
            mock_should_save.assert_called_once()
            mock_atomic_save.assert_called_once()

def test_restore_backup(csv_reader):
    """Testa a restauração do backup"""
    # Mock para evitar operações reais de arquivo
    with patch('os.path.exists', return_value=True) as mock_exists:
        with patch('os.remove') as mock_remove:
            with patch('shutil.copy2') as mock_copy:
                # Testar a restauração
                csv_reader._restore_backup()
                
                # Verificar se os métodos foram chamados
                mock_exists.assert_called()
                mock_copy.assert_called_once()
                assert mock_remove.call_count == 2  # Remove original e backup após copiar

def test_cleanup(csv_reader):
    """Testa a limpeza do backup"""
    # Mock para evitar operações reais de arquivo
    with patch('os.path.exists', return_value=True) as mock_exists:
        with patch('os.remove') as mock_remove:
            # Testar a limpeza
            csv_reader.cleanup()
            
            # Verificar se os métodos foram chamados
            mock_exists.assert_called_once_with(csv_reader.backup_path)
            mock_remove.assert_called_once_with(csv_reader.backup_path)

def test_safe_shutdown(csv_reader):
    """Testa o encerramento seguro"""
    # Mock para evitar operações reais
    with patch.object(csv_reader, '_atomic_save', return_value=True) as mock_save:
        # Testar o encerramento
        csv_reader._safe_shutdown()
        
        # Verificar se o método foi chamado
        mock_save.assert_called_once()

def test_safe_shutdown_failure(csv_reader):
    """Testa o encerramento seguro com falha no salvamento"""
    # Mock para simular falha no salvamento
    with patch.object(csv_reader, '_atomic_save', return_value=False) as mock_save:
        with patch.object(csv_reader, '_restore_backup') as mock_restore:
            # Testar o encerramento
            csv_reader._safe_shutdown()
            
            # Verificar se os métodos foram chamados
            mock_save.assert_called_once()
            mock_restore.assert_called_once()

def test_setup_signal_handlers(csv_reader):
    """Testa a configuração dos handlers de sinal"""
    with patch('signal.signal') as mock_signal:
        # Acessar o método protegido para testá-lo diretamente
        csv_reader._setup_signal_handlers()
        
        # Verificar se o sinal foi configurado
        mock_signal.assert_called_with(signal.SIGINT, ANY)

def test_exception_handling_mark_as_sent(csv_reader):
    """Testa o tratamento de exceções em mark_as_sent"""
    # Mock para simular uma exceção ao usar o DataFrame
    with patch('pandas.DataFrame.__getitem__', side_effect=Exception("Erro de teste")):
        with patch('src.utils.csv_reader.log.error') as mock_log:
            # Tentar marcar como enviado
            csv_reader.mark_as_sent('joao@example.com')
            
            # Verificar se o erro foi logado
            mock_log.assert_called_once()
            assert "Error marking email" in mock_log.call_args[0][0]

def test_exception_handling_mark_as_failed(csv_reader):
    """Testa o tratamento de exceções em mark_as_failed"""
    # Mock para simular uma exceção ao usar o DataFrame
    with patch('pandas.DataFrame.__getitem__', side_effect=Exception("Erro de teste")):
        with patch('src.utils.csv_reader.log.error') as mock_log:
            # Tentar marcar como falha
            csv_reader.mark_as_failed('joao@example.com')
            
            # Verificar se o erro foi logado
            mock_log.assert_called_once()
            assert "Error marking email" in mock_log.call_args[0][0]

def test_exception_handling_clear_sent_flags(csv_reader):
    """Testa o tratamento de exceções em clear_sent_flags"""
    # Mock para simular uma exceção
    with patch('shutil.copy2', side_effect=Exception("Erro de teste")) as mock_copy:
        with patch('src.utils.csv_reader.log.error') as mock_log:
            with patch.object(csv_reader, '_restore_backup') as mock_restore:
                # Tentar limpar flags
                csv_reader.clear_sent_flags()
                
                # Verificar se o erro foi logado
                mock_log.assert_called_once()
                assert "Error clearing flags" in mock_log.call_args[0][0]
                
                # Verificar se o backup foi restaurado
                mock_restore.assert_called_once()

def test_signal_handler(csv_reader):
    """Testa o handler de sinal"""
    # Extrair o handler de sinal do método _setup_signal_handlers
    with patch('sys.exit') as mock_exit:
        with patch.object(csv_reader, '_safe_shutdown') as mock_shutdown:
            # Forçar a configuração do sinal para capturar o handler
            csv_reader._setup_signal_handlers()
            
            # Simular um sinal SIGINT
            for sig_handler in signal.signal.mock_calls:
                # Encontrar a chamada do handler de SIGINT
                if sig_handler[1][0] == signal.SIGINT:
                    handler = sig_handler[1][1]
                    # Chamar o handler diretamente
                    handler(signal.SIGINT, None)
                    break
            
            # Verificar se os métodos foram chamados
            mock_shutdown.assert_called_once()
            mock_exit.assert_called_once_with(1) 