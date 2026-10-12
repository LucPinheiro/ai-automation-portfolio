import sys
import os

# Forzamos a la máquina virtual a entender que 'app' está dentro de la subcarpeta
root_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(root_dir, 'ai_sales_assistant'))
sys.path.insert(0, os.path.join(root_dir, 'ai_sales_assistant', 'app'))

# Ahora importamos de forma segura
from app.main import app
