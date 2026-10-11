import sys
import os

# Agrega la subcarpeta al entorno de ejecución de Python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_sales_assistant'))

# Volvemos a importar "app" desde "app.main" ya que allí es donde se inicializa FastAPI
from app.main import app
