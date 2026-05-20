"""
wsgi.py
WSGI entry point for running the handbook app under Apache mod_wsgi
"""

import sys
from pathlib import Path

# Add handbook directory to path
handbook_dir = Path(__file__).parent
sys.path.insert(0, str(handbook_dir))

from app import app as application

# For debugging
if __name__ == "__main__":
    application.run()
