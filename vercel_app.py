import sys
import os

# Fuerza a Python a reconocer la subcarpeta del asistente
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ai_sales_assistant'))

from app.api import app
