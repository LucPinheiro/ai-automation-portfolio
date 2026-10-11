import sys
import os

# Forzamos la inclusión de la subcarpeta en las rutas absolutas de la máquina virtual
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_sales_assistant'))

from app.main import app
