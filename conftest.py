import sys
import os
from pathlib import Path

# Adiciona o diretório src ao path para que os imports funcionem
# sem necessidade de usar o prefixo src.
project_root = Path(__file__).parent
src_path = project_root / "src"

# Adiciona o caminho ao sys.path se ainda não estiver lá
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root)) 