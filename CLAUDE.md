# Project
A Django web application for managing my rental houses. I'm a landlord in Uganda, so the default currency is UGX (no decimals, comma thousands separators, e.g. "UGX 450,000").

## Stack
- Python 3.12, Django 5.x, SQLite for dev (settings ready for PostgreSQL via env vars)
- Server-rendered templates with Bootstrap 5, mobile-friendly (I'll use it a lot from my phone)
- WeasyPrint to generate receipt PDFs from an HTML template
- PyMuPDF (fitz) to rasterize that same PDF into a JPG so both formats look identical
- django-environ for settings, with a .env.example
- django-phonenumber-field (default region UG) for phone numbers
- django-ratelimit for public pages
- Django's built-in auth; all management pages require login

## Data model
- LandlordProfile (singleton, editable in-app): business name, address, phone, WhatsApp number (E.164), optional logo, receipt footer text, WhatsApp message templates (see below), toggle for statement PIN check
- Property: name, location, notes
- Unit: property (FK), unit name/number, monthly rent, status (vacant/occupied)
- Tenant: full name, phone (E.164, required), email (optional), national ID (optional), notes
- Tenancy: tenant, unit, start date, end date (nullable), agreed monthly rent, deposit amount, is_active
- Payment: tenancy (FK), amount, payment date, period covered (month/year, allow a range e.g. Jan–Mar), method (Cash, Mobile Money – MTN, Mobile Money – Airtel, Bank, Other), reference/transaction ID, notes, recorded_by, created_at
- Receipt: one-to-one with Payment, auto-generated unique receipt number (RCP-YYYY-00001, sequential per year, safe against race conditions), issued_at
- ReceiptShare: payment, format (pdf/jpg), signed-link expiry, shared_by, shared_at (a log of WhatsApp shares)
- ExpenseCategory: name, description (user-manageable; seed defaults: Repairs & Maintenance, Utilities, Property Tax/Rates, Security, Cleaning, Insurance, Agent/Commission, Legal, Other)
- Expense: property (FK), unit (FK, optional), category (FK), amount, date, description (required), vendor/payee (optional), attachment (optional photo/scan), recorded_by, created_at
- TenantAccessLink: tenant, token_hash, created_by, created_at, expires_at, revoked, last_accessed_at, access_count
- LinkRequest: tenant, access_link (FK, the expired one), requested_at, handled (bool), handled_at

## Features

1. Dashboard: total collected this month, total expenses this month, net income, occupancy rate, tenants with outstanding balances, recent payments and expenses, and pending tenant link requests.

2. CRUD screens for properties, units, tenants, tenancies, payments, expenses and expense categories, with search and filters (property, date range, category, tenant).

3. Payments and receipts:
   - Recording a payment automatically creates its receipt, then redirects to the payment detail page.
   - Warn (but allow override) when recording against an inactive tenancy.

4. Receipt downloads:
   - On the payment detail page and in the payments list: "Download PDF" and "Download JPG" buttons. I choose which.
   - Files are generated on demand (not stored) and served as attachments named e.g. RCP-2026-00012.pdf / .jpg.

5. Receipt layout (single HTML template, A5 or half-A4, clean and printable): business name, address, phone, optional logo, receipt number, date, tenant name, property & unit, period covered, amount in figures AND words (English, e.g. "Four hundred fifty thousand shillings only"), payment method and reference, balance remaining (if any), "Received by" line, footer text.

6. Tenant balances: expected rent vs payments per tenancy, showing arrears or credit.

7. Expenses: record costs per property (optionally per unit) by category with a required description and optional receipt attachment.

8. Reports: income vs expenses by month and by property, expenses broken down by category, date-range filters, CSV export.

9. WhatsApp receipt sharing (manual, click-to-chat only, no WhatsApp API):
   - On the payment detail page, "Send via WhatsApp" with a choice of PDF or JPG.
   - Generate a signed, expiring public link to that receipt (django.core.signing, valid 30 days, no login, no guessable IDs).
   - Open https://wa.me/<tenant_phone>?text=<message> in a new tab with a pre-filled message from an editable template, e.g.
     "Hello {tenant}, thank you for your payment of UGX {amount} for {period}. Your receipt {receipt_no}: {link}"
   - Log each share in ReceiptShare and show the history on the payment page.

10. Tenant statement links (secure, expiring access to their own records):

   Generating:
   - From a tenant's page, "Generate access link" with expiry choices: 24 hours, 7 days, 30 days, or a custom date/time.
   - Token from secrets.token_urlsafe(32); store only its SHA-256 hash. URL: /statement/<token>/
   - List all links per tenant with last-used info; revoke any link early. Option to revoke older active links when generating a new one.
   - After generating: "Copy link" and "Send via WhatsApp" (click-to-chat, editable template), e.g.
     "Hello {tenant}, view your payment records here: {link} (valid until {expiry})."
     Note: the raw token is only available at creation time, so show the link once and make clear it can't be recovered later (generate a new one instead).

   Tenant view (no login, read-only, mobile-first):
   - Optional PIN check (toggle in settings): last 4 digits of the tenant's phone; lock for 15 minutes after 5 wrong attempts.
   - Shows tenant name, property/unit, tenancy dates, monthly rent, full payment history (date, period, amount, method, receipt no.), current balance/arrears or credit.
   - PDF and JPG receipt downloads per payment, authorised by the same token.
   - Clearly shows expiry ("This link expires on 15 Nov 2026, 6:00 PM").
   - Never exposes other tenants' data, internal IDs, notes, or expenses.

   Expired / revoked link page:
   - Friendly message: "This link has expired."
   - "Request a new link via WhatsApp" button. It first POSTs to the app (creating a LinkRequest, deduplicated so repeated clicks within an hour don't create duplicates), then redirects to wa.me/<landlord_whatsapp_number> with a pre-filled message:
     "Hello, I'd like a new link to view my rent payment records. Name: {tenant}, Unit: {unit}."
     Tenant details come from the expired link's record.
   - Pending requests appear on my dashboard with one-click "Generate & send new link", which marks the request handled.

   Security:
   - Rate-limit all public URLs (statement pages, receipt share links) per IP.
   - noindex meta + X-Robots-Tag, Referrer-Policy: no-referrer, Cache-Control: no-store on public pages.
   - Constant-time comparisons; identical responses for invalid vs non-existent tokens.

11. Phone numbers: store in E.164 (+2567XXXXXXXX); normalise inputs like "0772 123456" to "+256772123456".

12. Django admin registered for all models as a backup interface.

## Architecture
- Put receipt generation in a reusable service module (receipts/services.py: render_receipt_pdf(payment), render_receipt_jpg(payment)) used by downloads, share links and the tenant statement.
- Put WhatsApp link building in its own small module (e.g. messaging/whatsapp.py) so I can add the WhatsApp Cloud API later without touching views.
- Use integer/Decimal amounts, never floats.

## Quality
- Validation: amounts must be positive; required descriptions enforced.
- Tests for: receipt number generation, balance calculation, amount-in-words, PDF/JPG download endpoints returning valid files, phone normalisation, signed receipt link expiry/tampering, statement link expiry and revocation, PIN lockout, tenant isolation (link A can't access tenant B's receipts), LinkRequest creation/dedup, and correct wa.me URL encoding.
- Seed command (python manage.py seed_demo) creating sample properties, units, tenants, tenancies, payments and expenses.
- README with setup steps, including WeasyPrint system dependencies (Linux and Windows notes) and production notes (DEBUG off, ALLOWED_HOSTS, HTTPS, static/media serving).

## How to work
Before writing code, show me a short plan (apps, models, URL structure) and wait for my OK. Then build in stages, running migrations and tests after each and fixing failures before moving on:
1. Project setup, models, admin, seed command
2. Payments, receipts, PDF/JPG downloads
3. Expenses and categories
4. WhatsApp receipt sharing
5. Tenant statement links and link requests
6. Dashboard and reports
7. Final test pass and README