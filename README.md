---
noteId: "459e11c0d69e11f18a959d2097fbc20d"
tags: []

---

# RentApp

A Django app for managing rental properties, tenants, payments, receipts and expenses,
built for a landlord in Uganda (UGX currency, no decimals, comma thousands separators).

## Stack

- Python 3.12+, Django 5.x, SQLite for dev (PostgreSQL via `DATABASE_URL` for production)
- Server-rendered templates with Bootstrap 5 (via CDN), mobile-friendly
- ReportLab to generate receipt PDFs (pure Python, no native dependencies); PyMuPDF (fitz)
  to rasterize the same PDF into a JPG
- django-environ, django-phonenumber-field (region UG), django-ratelimit

## Setup

1. **Create and activate a virtual environment**

   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

2. **Install Python dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**

   ```bash
   cp .env.example .env   # Linux/macOS
   copy .env.example .env # Windows
   ```

   Edit `.env` and set a real `SECRET_KEY` (generate one with
   `python -c "import secrets; print(secrets.token_urlsafe(50))"`).

4. **Run migrations**

   ```bash
   python manage.py migrate
   ```

   This also seeds the default expense categories (Repairs & Maintenance, Utilities,
   Property Tax/Rates, Security, Cleaning, Insurance, Agent/Commission, Legal, Other).

5. **(Optional) Load demo data**

   ```bash
   python manage.py seed_demo
   ```

   Creates sample properties, units, tenants, tenancies, payments (with receipts) and
   expenses, plus a login user `landlord` / `changeme123` (change this password). Pass
   `--flush` to wipe and recreate the demo records (the receipt numbering sequence is
   never reset, by design).

6. **Run the dev server**

   ```bash
   python manage.py runserver
   ```

   Visit `http://127.0.0.1:8000/` and log in (or create a user with
   `python manage.py createsuperuser`).

7. **Run tests**

   ```bash
   python manage.py test
   ```

Receipt PDF/JPG generation works out of the box on every platform — ReportLab is pure
Python (no native/system dependencies), and PyMuPDF ships prebuilt wheels.

## Production notes

- Set `DEBUG=False` in `.env`.
- Set `ALLOWED_HOSTS` to your real domain(s), comma-separated.
- Set `SECRET_KEY` to a long random value and keep it out of version control.
- Set `DATABASE_URL` to a PostgreSQL connection string, e.g.
  `postgres://USER:PASSWORD@HOST:5432/DBNAME`.
- Serve the app behind HTTPS (e.g. via a reverse proxy); consider adding
  `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` once HTTPS is in
  place.
- Run `python manage.py collectstatic` and serve `STATIC_ROOT` (`staticfiles/`) via
  your web server or a CDN; `MEDIA_ROOT` (`media/`, for logos and expense attachments)
  needs persistent storage (a volume, or object storage like S3) since it isn't baked
  into the deploy.
- django-ratelimit's public-view rate limiting uses Django's cache framework
  (`django.core.cache`), which defaults to in-memory and does **not** share state across
  multiple worker processes. In production, configure a shared cache backend (e.g.
  Redis) in `CACHES` so rate limits apply correctly across all workers.
- Signed receipt share links and statement access-link tokens rely on `SECRET_KEY` for
  their cryptographic signing/hashing — rotating `SECRET_KEY` invalidates all
  outstanding signed receipt links (statement links are unaffected, since those are
  looked up by a stored hash, not a Django signature).
