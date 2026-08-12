import sys
import os

# Add backend directory to sys.path
backend_path = os.path.join(os.path.dirname(__file__), '..', 'backend')
if backend_path not in sys.path:
    sys.path.append(backend_path)

from app import create_app

app = create_app()
