# Momand Super Store

Momand Super Store is being built on the existing Django Oscar catalogue and basket so the current store data remains usable. The React client is separate from Django templates and talks to the versioned API at `/api/v1/`.

## Current implementation

- Responsive React/Vite storefront with home, product browse/details, categories, cart, contact, about, login, registration, password reset, account, order history, and checkout pages.
- Django REST API for public catalogue/categories/contact, Oscar session basket, email-based JWT login with an HTTP-only refresh cookie, registration, password reset, and customer-scoped orders.
- Authenticated online checkout supports cash on delivery, requires an Oscar shipping-country record, rechecks stock, creates an Oscar order and audits its stock allocation.
- Staff POS supports barcode/name search, cash/card/bank-transfer recording, stock deduction, invoice history, and 58/80 mm browser-print receipt/reprint.
- Purchase receiving, supplier management, expenses, low-stock reporting, and stock adjustment APIs/pages are permission-protected and record stock movements transactionally.
- Django role groups are created by `seed_roles`; supermarket categories and sample grocery stock can be created idempotently with `seed_data`.
- POS returns/refunds are supported with return limits and optional stock restocking. Split tender, payment gateways, full tax/discount accounting, weighted profit and financial reconciliation, advanced reports/exports, image uploads, customer address management, and the Pashto UI remain incomplete. Treat this as an active development build, not as a complete production system.

## Local development

The cashier POS, returns/refunds, stock adjustment, and purchase receiving endpoints are permission-protected and backed by database transactions. Cashiers are restricted to their own POS sales and dashboard totals. `seed_roles` creates Django groups for the listed staff roles; assign users to the appropriate group in Django admin. Split tender and the remaining MIS/reporting screens are still under development.

Use Python 3.12+, Node.js, and npm. From the repository root:

```powershell
Copy-Item .env.example .env
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python backend\manage.py migrate
python backend\manage.py oscar_populate_countries --initial-only
python backend\manage.py seed_roles
python backend\manage.py seed_data
python backend\manage.py createsuperuser
python backend\manage.py runserver
```

To start the **local development** Docker stack, first copy `.env.example` to `.env`, replace `SECRET_KEY` and `POSTGRES_PASSWORD`, then run:

```powershell
docker compose up --build
```

Compose starts Django's development server, the Vite server, PostgreSQL, and Redis. It is for local development only; use a production WSGI server and HTTPS reverse proxy for deployment.

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

The API runs at `http://127.0.0.1:8000/api/v1/`; Vite proxies `/api` to Django in development. Product media is served from Django at `/media/`. Add staff accounts to a role group and set their Django `is_staff` flag; APIs check both the role's model permissions and staff status.

## Configuration

Set a strong unique `SECRET_KEY` before running beyond local development. `.env.example` documents SQLite/PostgreSQL selection, allowed hosts, CORS/CSRF origins, store currency, contact details, and frontend URL. To use PostgreSQL, set `DATABASE_ENGINE=django.db.backends.postgresql` and provide the database name, user, password, host, and port. `pycountry` is required by Oscar's `oscar_populate_countries` command; use it to populate checkout country records.

Never commit `.env`, production credentials, or customer data. Production deployment still needs HTTPS, PostgreSQL, static/media storage, email delivery, backups, monitoring, and reviewed security settings.

## Verification

```powershell
python backend\manage.py check
python backend\manage.py makemigrations --check --dry-run
python backend\manage.py migrate --check
python backend\manage.py test
cd frontend
npm run build
```

Run the focused store API and inventory service tests with `python backend\manage.py test backend.apps.api.tests apps.mis.tests`. The repository also includes the upstream Oscar test suite, which the unqualified `python backend\manage.py test` discovers and runs.
