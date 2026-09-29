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

The API currently has no access restrictions, matching the prototype's lack of
authentication. Add access control before exposing vendor contact data publicly.

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
