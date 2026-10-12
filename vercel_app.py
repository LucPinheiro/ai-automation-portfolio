import sys
import os

# Forzamos a Python a incluir la subcarpeta del asistente en el path global de la máquina
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_sales_assistant'))

# Ahora cargamos la aplicación de forma limpia
from app.main import app
