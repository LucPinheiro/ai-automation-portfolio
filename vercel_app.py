import sys
import os

# Forzamos a Python a incluir la subcarpeta en las búsquedas de módulos
sys.path.append(os.path.join(os.path.dirname(__file__), 'ai_sales_assistant'))

from app.main import app
