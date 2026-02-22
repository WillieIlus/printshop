# PythonAnywhere Deployment Guide — PrintShop API

Manual configuration for Python 3.11, virtualenv at `~/.virtualenvs/venv`, WSGI, static files.

---

## Confirmed Project Structure

| Item | Path |
|------|------|
| Repo root | `~/printshop_api/` (contains `requirements.txt`, `printshop_api/`) |
| Project root | `~/printshop_api/printshop_api/` (contains `manage.py`) |
| Django settings | `printshop_api/printshop_api/settings.py` |
| DJANGO_SETTINGS_MODULE | `printshop_api.settings` |
| STATIC_ROOT | `printshop_api/printshop_api/staticfiles` |

---

## Step 1 — Clone and Setup

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git printshop_api
cd printshop_api/printshop_api
```

---

## Step 2 — Create Python 3.11 Virtualenv

```bash
# Create virtualenv with Python 3.11 at ~/.virtualenvs/venv
python3.11 -m venv ~/.virtualenvs/venv
source ~/.virtualenvs/venv/bin/activate
```

---

## Step 3 — Install Requirements

```bash
# From repo root (requirements.txt is here)
cd ~/printshop_api
source ~/.virtualenvs/venv/bin/activate

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
cd ~/printshop_api/printshop_api
source ~/.virtualenvs/venv/bin/activate
python manage.py migrate --noinput
```

---

## Step 6 — Collect Static Files

```bash
cd ~/printshop_api/printshop_api
source ~/.virtualenvs/venv/bin/activate
python manage.py collectstatic --noinput
```

---

## Step 7 — Configure Web App (PythonAnywhere Web Tab)

1. **WSGI configuration file**  
   Open the WSGI file (e.g. `/var/www/YOUR_USERNAME_pythonanywhere_com_wsgi.py`) and replace its contents with `pythonanywhere_wsgi.py`. **Replace `YOUR_USERNAME`** with your PythonAnywhere username.

2. **Virtualenv**  
   Set: `/home/YOUR_USERNAME/.virtualenvs/venv`

3. **Static files mapping**  
   - **URL:** `/static/`
   - **Directory:** `/home/YOUR_USERNAME/printshop_api/printshop_api/staticfiles`

4. **Optional — Media files**  
   - **URL:** `/media/`
   - **Directory:** `/home/YOUR_USERNAME/printshop_api/printshop_api/media`

---

## Step 8 — Reload Web App

In the PythonAnywhere **Web** tab, click **Reload** for your web app.

---

## Full Copy-Paste Command Sequence

Replace `YOUR_USERNAME` with your PythonAnywhere username.

```bash
# 1. Clone
cd ~
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git printshop_api

# 2. Virtualenv (Python 3.11)
python3.11 -m venv ~/.virtualenvs/venv
source ~/.virtualenvs/venv/bin/activate

# 3. Install requirements
cd ~/printshop_api
pip install --upgrade pip
pip install -r requirements.txt

# 4. Migrations
cd ~/printshop_api/printshop_api
python manage.py migrate --noinput

# 5. Collect static
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
| **ImproperlyConfigured: DJANGO_SETTINGS_MODULE** | WSGI file | Set `DJANGO_SETTINGS_MODULE=printshop_api.settings` |
| **Allauth provider import errors** | `INSTALLED_APPS` | Ensure `requests` and `cryptography` installed |
| **404 on /static/** | Static files mapping in Web tab | Add `/static/` → `.../printshop_api/staticfiles` |
| **502 Bad Gateway** | Error log in Web tab | Check WSGI path, virtualenv path, import errors |
| **CSRF verification failed** | `CSRF_TRUSTED_ORIGINS` | Add `https://YOUR_USERNAME.pythonanywhere.com` |
| **DisallowedHost** | `ALLOWED_HOSTS` | `.pythonanywhere.com` already included |

---

## Diagnostics Commands

```bash
source ~/.virtualenvs/venv/bin/activate
cd ~/printshop_api/printshop_api

python --version                    # Expected: Python 3.11.x
python -c "import django; print(django.get_version())"
python -c "import requests; print('requests OK')"
python -c "import cryptography; print('cryptography OK')"
python -c "
from django.conf import settings
print('STATIC_ROOT:', getattr(settings, 'STATIC_ROOT', 'NOT SET'))
print('DEBUG:', settings.DEBUG)
print('ALLOWED_HOSTS:', settings.ALLOWED_HOSTS)
"
```

---

## Notes

- **Python 3.11** required.
- Virtualenv: `~/.virtualenvs/venv`
- `DEBUG` defaults to `False`; set `DJANGO_DEBUG=true` for local development.
- `SECRET_KEY` set via `DJANGO_SECRET_KEY` in production.
- `ALLOWED_HOSTS` includes `.pythonanywhere.com` for all subdomains.
