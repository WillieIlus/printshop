# PythonAnywhere Deployment Guide — PrintShop API

Manual configuration for Python 3.11, virtualenv, WSGI, static files.

---

## Confirmed Project Structure

| Item | Path |
|------|------|
| Project root | `printshop_api/` (contains `manage.py`) |
| Django settings | `printshop_api/printshop_api/settings.py` |
| WSGI module | `printshop_api/printshop_api/wsgi.py` |
| DJANGO_SETTINGS_MODULE | `printshop_api.settings` |
| WSGI_APPLICATION | `printshop_api.wsgi.application` |

---

## Step 1 — Clone and Setup

```bash
# Clone your repo (adjust URL as needed)
cd ~
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git printshop_api
cd printshop_api
```

**Note:** Project root is the directory containing `manage.py`. If your repo structure differs, `cd` into that directory.

---

## Step 2 — Create Python 3.11 Virtualenv

```bash
# Create virtualenv with Python 3.11
mkvirtualenv --python=/usr/bin/python3.11 venv

# Or if using existing venv path:
# python3.11 -m venv /home/amazingace00/.virtualenvs/venv
# source /home/amazingace00/.virtualenvs/venv/bin/activate
```

---

## Step 3 — Install Requirements

```bash
# Ensure you're in project root (directory with manage.py)
cd /home/amazingace00/printshop_api

# Activate virtualenv (if not already)
workon venv
# or: source /home/amazingace00/.virtualenvs/venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Step 4 — Environment Variables

In PythonAnywhere **Web** tab → **Environment variables**, add:

| Variable | Value |
|----------|-------|
| `DJANGO_DEBUG` | `False` |
| `DJANGO_SECRET_KEY` | *(generate with command below)* |

Generate secret key:
```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

---

## Step 5 — Run Migrations

```bash
cd /home/amazingace00/printshop_api
workon venv
python manage.py migrate --noinput
```

---

## Step 6 — Collect Static Files

```bash
cd /home/amazingace00/printshop_api
workon venv
python manage.py collectstatic --noinput
```

---

## Step 7 — Configure Web App (PythonAnywhere Web Tab)

1. **WSGI configuration file**  
   Open the WSGI file (e.g. `/var/www/amazingace00_pythonanywhere_com_wsgi.py`) and replace its contents with the content of `pythonanywhere_wsgi.py` in this repo.

2. **Virtualenv**  
   Set: `/home/amazingace00/.virtualenvs/venv`

3. **Static files mapping**  
   Add:
   - **URL:** `/static/`
   - **Directory:** `/home/amazingace00/printshop_api/staticfiles`

4. **Optional — Media files (if serving uploads)**  
   - **URL:** `/media/`
   - **Directory:** `/home/amazingace00/printshop_api/media`

---

## Step 8 — Reload Web App

In the PythonAnywhere **Web** tab, click **Reload** for your web app.

---

## Full Copy-Paste Command Sequence

```bash
# 1. Navigate to project
cd /home/amazingace00/printshop_api

# 2. Create/use virtualenv (Python 3.11)
mkvirtualenv --python=/usr/bin/python3.11 venv
workon venv

# 3. Install requirements
pip install --upgrade pip
pip install -r requirements.txt

# 4. Run migrations
python manage.py migrate --noinput

# 5. Collect static files
python manage.py collectstatic --noinput

# 6. Reload web app via PythonAnywhere Web tab
```

---

## Failure Recovery Checklist

| Symptom | Check | Fix |
|---------|-------|-----|
| **ImportError: No module named 'requests'** | `pip list \| grep requests` | `pip install requests` |
| **ImportError: No module named 'cryptography'** | `pip list \| grep cryptography` | `pip install cryptography` |
| **ImproperlyConfigured: STATIC_ROOT** | `grep STATIC_ROOT printshop_api/settings.py` | Ensure `STATIC_ROOT = BASE_DIR / "staticfiles"` exists |
| **Migration mismatches** | `python manage.py showmigrations` | `python manage.py migrate --noinput` |
| **ImproperlyConfigured: DJANGO_SETTINGS_MODULE** | WSGI file `os.environ.setdefault(...)` | Set `DJANGO_SETTINGS_MODULE=printshop_api.settings` |
| **Allauth provider import errors** | Check `INSTALLED_APPS` for `allauth.socialaccount.providers.*` | Ensure `requests` and `cryptography` installed |
| **404 on /static/** | Static files mapping in Web tab | Add URL `/static/` → `/home/amazingace00/printshop_api/staticfiles` |
| **502 Bad Gateway** | Error log in Web tab | Check WSGI path, virtualenv path, import errors |
| **CSRF verification failed** | `CSRF_TRUSTED_ORIGINS` | Add `https://amazingace00.pythonanywhere.com` |
| **DisallowedHost** | `ALLOWED_HOSTS` | Add `amazingace00.pythonanywhere.com` |

---

## Diagnostics Commands

```bash
# Verify Python version
python --version
# Expected: Python 3.11.x

# Verify Django
python -c "import django; print(django.get_version())"

# Verify critical packages
python -c "import requests; print('requests OK')"
python -c "import cryptography; print('cryptography OK')"
python -c "import rest_framework; print('DRF OK')"
python -c "import rest_framework_simplejwt; print('JWT OK')"
python -c "import allauth; print('allauth OK')"

# Verify settings
python -c "
from django.conf import settings
print('STATIC_ROOT:', getattr(settings, 'STATIC_ROOT', 'NOT SET'))
print('DEBUG:', settings.DEBUG)
print('ALLOWED_HOSTS:', settings.ALLOWED_HOSTS)
"
```

---

## Notes

- **Python 3.11** is required (not 3.13).
- Do **not** modify models, serializers, or JWT logic for deployment.
- `DEBUG` defaults to `False`; set `DJANGO_DEBUG=true` for local development.
- `SECRET_KEY` should be set via `DJANGO_SECRET_KEY` in production.
