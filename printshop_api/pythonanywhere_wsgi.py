"""
PythonAnywhere WSGI configuration for printshop_api.

Paste this content into the WSGI configuration file in the PythonAnywhere Web tab.
Replace YOUR_USERNAME with your PythonAnywhere username before use.

Project structure on PythonAnywhere (clone repo to ~/printshop_api):
  /home/YOUR_USERNAME/printshop_api/printshop_api/  <- project root (manage.py here)
  /home/YOUR_USERNAME/.virtualenvs/venv  <- virtualenv (set in Web tab)
"""

import sys
import os

# Project root: directory containing manage.py (adjust if you cloned elsewhere)
# Replace YOUR_USERNAME with your PythonAnywhere username
project_home = "/home/YOUR_USERNAME/printshop_api/printshop_api"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "printshop_api.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
