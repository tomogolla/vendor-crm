# DigitalOcean Droplet deployment

This setup runs one Django/Gunicorn backend and one SvelteKit Node server behind
Caddy. Caddy obtains and renews HTTPS certificates. Only ports 80 and 443 are
published; Django is private and `/admin/` is proxied by Caddy. SQLite and admin
static files live in Docker volumes. This is a single-server, modest-traffic
configuration; move to PostgreSQL before scaling to multiple app servers.

## 1. Prepare the Droplet

Create an Ubuntu 24.04 LTS Droplet with an SSH key. Allow enough RAM for the
frontend build (2 GB is a reasonable starting point). Install Docker Engine and
the Compose plugin using https://docs.docker.com/engine/install/ubuntu/ or use
DigitalOcean's Docker image. Verify `docker compose version` works.

Point your domain's A record at the Droplet. Only add an AAAA record if IPv6 is
configured. In the DigitalOcean Cloud Firewall, allow inbound TCP 22 from your
administrator IP and TCP 80/443 from the internet; UDP 443 is optional. Keep
outbound DNS, HTTPS, and your mail provider's port available. Do not publish
ports 3000 or 8000. Use a sudo-capable account for the following Docker commands
(or an account already authorized to use Docker).

Copy the complete project to the server, including `frontend/vendorops`.
**The frontend is a separate Git repository referenced as a gitlink by the root
repository, with no .gitmodules file. A normal root clone is not sufficient.**
Commit/push both repositories and check out the intended frontend revision, or
transfer both working directories. Do not transfer `.env`, `.venv`, node_modules,
local databases, or generated build output as source code. Existing local data
can be imported explicitly as described below.

## 2. Configure

From the project root:

```sh
cp .env.example .env
chmod 600 .env
python3 -c 'import secrets; print(secrets.token_urlsafe(64))'
nano .env
```

Set APP_DOMAIN to your actual domain (no `https://`, port, or path) and SECRET_KEY
to the generated value. Keep the secret stable across deployments and back it up
securely. Compose injects this root .env; backend/.env is not used by the containers.
DEBUG is forced off, and startup rejects missing/short development secrets.

For invoice and sequence emails, configure SMTP_HOST, SMTP_USERNAME and
SMTP_PASSWORD and authorize SMTP_FROM with your provider. DigitalOcean blocks
ports 25, 465 and 587: https://docs.digitalocean.com/support/why-is-smtp-blocked/.
Use a provider supporting STARTTLS on another port, such as 2525, and verify
connectivity on the Droplet. If that isn't available, an email HTTP API integration
is needed. Leaving SMTP_HOST empty disables email-dependent approval actions.

## 3. Build and start

```sh
docker compose build
docker compose up -d
docker compose ps -a
docker compose logs --tail=100 init backend frontend caddy
docker compose exec backend python manage.py createsuperuser
```

`init` must exit with code 0; it runs migrations and collectstatic before the
backend starts. Backend and frontend should become healthy. Visit
`https://YOUR_DOMAIN/login` and `https://YOUR_DOMAIN/admin/`. Verify sign-in,
vendor creation/editing, CSV import, logout, and a test invoice email.

```sh
docker compose exec backend python manage.py check --deploy
```

Django can report SSL redirect and HSTS subdomain/preload warnings: HTTPS redirect
is intentionally enforced at Caddy so internal HTTP API calls work. HSTS applies
to this host only; subdomains/preload are not enabled. Investigate other warnings.

## 4. Backups and updates

Make a consistent online SQLite backup (includes users and auth tokens):

```sh
mkdir -p backups
chmod 700 backups
docker compose exec -T backend python -c "import sqlite3; s=sqlite3.connect('/data/db.sqlite3'); d=sqlite3.connect('/data/backup.sqlite3'); s.backup(d); d.close(); s.close()"
docker compose cp backend:/data/backup.sqlite3 ./backups/db.sqlite3
chmod 600 backups/db.sqlite3
```

Archive backups with timestamps, copy them off the Droplet, and automate this
regularly. Also securely preserve .env and the Caddy certificate volume. A Docker
volume is persistent storage, not a backup. Never run `docker compose down -v`
unless you intend to delete the database and certificates.

Before updates, back up the database, record both Git revisions, then update both
source checkouts. Rebuild before stopping the running services:

```sh
docker compose build
docker compose stop caddy frontend backend
docker compose run --rm init
docker compose up -d --force-recreate
docker compose ps -a
```

This update process has brief downtime. If migrations fail, keep the services
stopped and investigate. For rollback, restore the previous source revisions and
images plus the matching pre-update database backup; older code may not support
a newer schema.

### Restore a backup or import an existing local database

On the machine containing the original SQLite database, use SQLite's backup API
as above to obtain a consistent copy; do not copy a live database file directly.
Transfer that copy securely to `backups/db.sqlite3` on the Droplet. For a fresh
installation run `docker compose build` first. The following deliberately
replaces all current application data, so take a backup first:

```sh
docker compose stop caddy frontend backend
docker compose run --rm --no-deps -v "$PWD/backups:/backup:ro" init python -c "import shutil; shutil.copyfile('/backup/db.sqlite3', '/data/db.sqlite3')"
docker compose run --rm init
docker compose up -d --force-recreate
```

Test restores periodically. Recreate the operator account only if the restored
database doesn't already contain it.

## Troubleshooting

- Certificate failures: check DNS, ports 80/443, and `docker compose logs caddy`.
- Sign-in/form errors: APP_DOMAIN must match the browser's HTTPS hostname; restart
  the stack after changing .env. SvelteKit uses an explicit ORIGIN for form checks.
- Backend unavailable: inspect init/backend logs and SECRET_KEY/ALLOWED_HOSTS.
- Static files missing: rerun `docker compose run --rm init`.
- CSV rejected before reaching the app: the proxy and Node limits are 3 MB to
  accommodate the app's 2 MB CSV limit plus multipart encoding overhead.

References: https://svelte.dev/docs/kit/adapter-node and
https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/.
