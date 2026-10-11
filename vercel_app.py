import sys
import os

# Inserta la subcarpeta en el path para solucionar los ModuleNotFoundError
sys.path.append(os.path.join(os.path.dirname(__file__), 'ai_sales_assistant'))

from app.main import app
