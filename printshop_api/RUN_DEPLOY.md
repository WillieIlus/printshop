# Run & Deploy – PrintShop API

## Quick Start (Development)

```bash
cd printshop_api
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
cp .env.example .env     # Edit with your DB, SECRET_KEY, etc.
python manage.py migrate
python manage.py runserver
```

API: http://localhost:8000/api/

## Production Deployment

### Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret (generate with `python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`) |
| `DEBUG` | `False` in production |
| `ALLOWED_HOSTS` | Your domain(s), e.g. `api.yourdomain.com,www.yourdomain.com` |
| `DATABASE_URL` | PostgreSQL connection string (or configure `DATABASES` in settings) |
| `CORS_ALLOWED_ORIGINS` | Frontend origin(s), e.g. `https://yourdomain.com,https://www.yourdomain.com` |
| `CSRF_TRUSTED_ORIGINS` | Same as CORS for cookie/CSRF, e.g. `https://yourdomain.com` |
| `PASSWORD_RESET_URL` | Base URL for reset links in emails, e.g. `https://yourdomain.com/auth/reset-password` |
| `DEFAULT_FROM_EMAIL` | Email sender for password reset |
| `EMAIL_HOST`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | SMTP for sending emails |

### Steps

1. Run migrations: `python manage.py migrate`
2. Collect static: `python manage.py collectstatic --noinput`
3. Use gunicorn/uwsgi: `gunicorn printshop_api.wsgi:application`
4. Serve behind nginx with HTTPS
5. Configure CORS and `CSRF_TRUSTED_ORIGINS` for your frontend domain

### CORS + Cookie Auth (Launch Blocker)

For cookie-based auth (no localStorage) with frontend on a different subdomain:

- Set `CORS_ALLOWED_ORIGINS` to your frontend domain
- Set `CSRF_TRUSTED_ORIGINS` to `https://yourdomain.com`
- Configure cookies: `Secure`, `SameSite=Lax` (or `None` if cross-site)

## Endpoint Audit

See [ENDPOINT_AUDIT.md](./ENDPOINT_AUDIT.md) for UI ↔ backend endpoint mapping.
