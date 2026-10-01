# vendor-crm
The good flea vendor crm

## Local development

Start the Django API (SQLite):

```sh
cd backend
source .venv/bin/activate
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

In another terminal, start the frontend:

```sh
cd frontend/vendorops
npm install
npm run dev
```

Open `/vendors` and select **Add vendor lead**. Leads are saved in
`backend/db.sqlite3` and displayed on the Vendors page. The frontend server
connects to Django at `http://127.0.0.1:8000`; set `DJANGO_API_URL` in
`frontend/vendorops/.env` to override it. No mock JSON server is needed for this page.

Business name, category, source, interest level, and at least one contact method
are required. Follow-up dates and conversation notes are optional. The browser
converts local follow-up times to UTC before saving and displays them in local time.

Vendor OS requires a Django user account. Create the first operator, then sign in
at `/login`:

```sh
backend/.venv/bin/python backend/manage.py createsuperuser
```

SvelteKit stores the API token in an HTTP-only, same-site cookie. Every application
route and Django API endpoint requires authentication. Additional accounts can be
created or disabled in Django Admin, and signing out revokes the active token.

Checks: `python manage.py test api` in `backend`, and `npm run check` / `npm run build`
in `frontend/vendorops`.

The Add vendor lead modal also includes a seven-section call questionnaire with
verbatim rep scripts, discovery questions, offer interest (1–5), closing checkboxes,
and follow-up status. Call answers are optional for incomplete calls. Both call
times and follow-up times use the browser's local timezone and are saved in UTC.
Expand **View call questionnaire** on a saved lead to review its answers.

Click a business name in the Vendor leads table to open `/vendors/<id>`. The
profile reuses the lead questionnaire as an editable form. **Save changes** updates
the existing lead; **Save checklist** stores Vendor contract, COI, and Info packet
checks. Waitlist and Decline save the application decision. **Approve application**
opens a modal that emails an approval invoice and records its amount, due date,
secure invoice link, recipient, and sent time. A sent invoice cannot be sent
again from this screen, and the decision becomes Approved only after sending succeeds.

To enable invoice email, configure Django's SMTP connection before starting it:

```sh
export SMTP_HOST=smtp.example.com
export SMTP_PORT=587
export SMTP_USERNAME=your-smtp-user
export SMTP_PASSWORD=your-smtp-password
export SMTP_USE_TLS=true
```

Set `SMTP_USE_SSL=true` and `SMTP_USE_TLS=false` for an SSL-only relay. The sender
address is `booking@thegoodflea.com`; the SMTP provider must allow that sender.
Without `SMTP_HOST`, the approval action reports a configuration error and does
not approve the vendor. The modal requires a vendor email, invoice amount in USD,
due date, and an HTTPS invoice link supplied by the rep. The approval email uses
the Good Flea welcome template and includes the amount, due date, selected market
dates, and invoice link. The app does not generate a payment link or collect payments.

## Market weekends

The **Market weekends** page shows all twelve fall weekends as tabs. Each weekend
has 40 booth spaces and reports booked vendors, remaining spaces, and the total
payment received for that weekend. Approved vendors are added automatically to
each market weekend selected on their lead profile.

Payments are tracked per vendor and weekend so a multi-weekend invoice is not
counted in full on every date. Update **Market weekend bookings** in Django admin
when payment is received; the page then updates the vendor's amount and weekend
total. Sending an invoice creates the bookings with `$0.00` paid until payment is
recorded.

## Application pipeline and CSV import

The **Applications** page lists records in the `New application` funnel stage.
Choose **Import vendors CSV** to upload a UTF-8 CSV up to 2 MB or 5,000 data rows.
Every row must include a business name and Instagram handle. Supported headers are:

```text
Business Name, Instagram, Email, Phone, Category, Source, First Name,
Last Name, Contact Name, Notes, Requested Dates
```

Underscored equivalents such as `business_name`, `instagram_handle`, and
`vendor_category` are also accepted. If category is absent it defaults to
`Unique Things`; source defaults to `Google form`; interest defaults to `Cold`.
Requested dates containing multiple weekends must be quoted in the CSV and use
` | ` between dates.

Instagram handles are stripped of `@` and compared case-insensitively against
existing records and earlier rows in the same file. Duplicate rows are skipped
and reported. Invalid rows are reported by row number while valid rows import.

Imported records open in the same vendor applicant profile used for review. When
**Accept application** successfully sends the approval invoice, the funnel stage
changes to `Vendor`: the record leaves Applications and appears in Vendors.

## DigitalOcean deployment

See [the Droplet deployment guide](deploy/README.md) for the Docker Compose setup,
automatic HTTPS, environment configuration, persistent storage, backups, and updates.
Start by copying `.env.example` to `.env` and configuring your domain and secret key.
