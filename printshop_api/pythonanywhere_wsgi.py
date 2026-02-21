"""
PythonAnywhere WSGI configuration for printshop_api.

Paste this content into the WSGI configuration file in the PythonAnywhere Web tab.
Or replace the default content of /var/www/amazingace00_pythonanywhere_com_wsgi.py
with this file's contents.

Project structure on PythonAnywhere:
  /home/amazingace00/printshop_api/     <- project root (manage.py here)
  /home/amazingace00/printshop_api/printshop_api/  <- Django project package
  /home/amazingace00/.virtualenvs/venv  <- virtualenv
"""

import sys
import os

# Project root: directory containing manage.py
project_home = "/home/amazingace00/printshop_api"
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Activate virtualenv (PythonAnywhere does this automatically if configured in Web tab)
# Ensure virtualenv path is set in Web app: /home/amazingace00/.virtualenvs/venv

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "printshop_api.settings")

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
