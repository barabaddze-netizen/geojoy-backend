# GeoJoy deployment guide

This package keeps the existing Python server, SQLite schema, APIs, routes, four-language content, authentication, and upload directory. It is a small self-hosted app; it is **not** a static-site bundle. The only new server settings are optional `HOST` binding and a production `GEOJOY_COOKIE_SECURE=1` flag. The site server itself does not terminate TLS.

## URLs

Current Render deployment (checked 2026-10-14):

- Public website: https://geojoy-backend.onrender.com/
- Admin panel: https://geojoy-backend.onrender.com/admin/

Both page routes are reachable (HTTP 200). However, the live content API references 60 photo files and all 60 `/uploads/*.webp` requests currently return HTTP 404. The admin login page and its CSS/JavaScript load, but authenticated admin functions were not tested against the live service. Do not treat the current deployment as complete until the photos are redeployed and rechecked.

## 1. Prepare a persistent Ubuntu server

Use Ubuntu 22.04/24.04 with Python 3.10 or newer, a domain pointing to the server, and persistent disk storage. Install the runtime and reverse proxy:

```bash
sudo apt update
sudo apt install -y python3 nginx certbot python3-certbot-nginx
sudo useradd --system --home /opt/geojoy --shell /usr/sbin/nologin geojoy
sudo mkdir -p /opt/geojoy
```

Copy the **complete project** into `/opt/geojoy`. Keep `geojoy_v8.db` and the entire `uploads/` directory on persistent storage. If migrating an existing installation, back up its latest database and uploads first, then place those production copies in the project directory; do not overwrite newer production data with the sample copy from this package. Make the files writable by the service account because the application saves SQLite updates and image uploads there:

```bash
sudo chown -R geojoy:geojoy /opt/geojoy
sudo chmod 750 /opt/geojoy
```

The existing app opens `geojoy_v8.db` beside `server.py` and stores uploaded media in `uploads/`. Startup runs the app's existing database initialization/migration logic; there is no new schema migration for the Tbilisi photo change.

## 2. Secure the admin account before public exposure

Before opening the site to visitors, sign in using the credential already stored in the database, open **Admin → Security**, change it to a unique strong password, and set a recovery phrase. Passwords and recovery phrases are stored as salted hashes. Do not reuse the bundled/local starter credential.

`GEOJOY_ADMIN_PASSWORD` is used only when initializing a database that has no administrator security record; it does **not** reset the password in an existing database. If provisioning a genuinely new database, set `GEOJOY_ADMIN_PASSWORD` to a long random secret before its first startup, then sign in and configure recovery. Keep secrets out of shell history and source control.

## 3. Run GeoJoy as a systemd service

Create `/etc/systemd/system/geojoy.service`:

```ini
[Unit]
Description=GeoJoy tourism website
After=network.target

[Service]
Type=simple
User=geojoy
Group=geojoy
WorkingDirectory=/opt/geojoy
Environment=HOST=127.0.0.1
Environment=PORT=8052
Environment=GEOJOY_COOKIE_SECURE=1
ExecStart=/usr/bin/python3 /opt/geojoy/server.py
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true
ReadWritePaths=/opt/geojoy

[Install]
WantedBy=multi-user.target
```

Enable and verify it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now geojoy
sudo systemctl status geojoy --no-pager
curl -fsS http://127.0.0.1:8052/api/health
```

The app binds to loopback by default, so its port is not directly exposed to the internet. `GEOJOY_COOKIE_SECURE=1` adds the `Secure` attribute to session cookies and should be enabled only when users reach the site through HTTPS.

## 4. Publish through Nginx and HTTPS

Create an Nginx site for your domain. The relevant proxy block is:

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN www.YOUR_DOMAIN;

    client_max_body_size 12m;
    location / {
        proxy_pass http://127.0.0.1:8052;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
```

Enable the site, test Nginx, and issue the certificate (Certbot will add TLS and the HTTP-to-HTTPS redirect):

```bash
sudo ln -s /etc/nginx/sites-available/geojoy /etc/nginx/sites-enabled/geojoy
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d YOUR_DOMAIN -d www.YOUR_DOMAIN
```

Allow SSH and web traffic through the firewall, but do **not** open port `8052` publicly. After DNS and TLS are active, verify both `https://YOUR_DOMAIN/` and `https://YOUR_DOMAIN/admin/`.

## 5. Data persistence and backups

Back up both the SQLite database and `uploads/`; neither should live on an ephemeral container filesystem. For a simple consistent backup, briefly stop the service, archive the two data locations, then start it again:

```bash
sudo systemctl stop geojoy
sudo tar -czf "/var/backups/geojoy-$(date +%F-%H%M).tar.gz" \
  -C /opt/geojoy geojoy_v8.db uploads
sudo systemctl start geojoy
```

Keep backups off the host and periodically test restoring them to a separate directory. The database schema and existing records are preserved; this update changes only the Tbilisi region's photo path, with no schema alteration.

## 6. Static assets and hosted startup

Deploy the complete project, including `static/`, all 60 curated `uploads/geojoy_*.webp` photos, and the production `geojoy_v8.db` on persistent storage. The `.gitignore` now permits only the bundled `uploads/geojoy_*.webp` files to be tracked; runtime-uploaded files and SQLite files remain ignored. The canonical CSS/JavaScript sources remain at the project root; run `python3 sync_static_assets.py` after changing them to refresh the conventional `/static/` copies (four CSS/JS files plus the local SVG favicon). The included `Procfile` performs this sync and starts the existing Python app with `HOST=0.0.0.0` and `GEOJOY_COOKIE_SECURE=1`; the hosting provider must supply `PORT`, HTTPS, and persistent storage for the database and uploads. Use this Procfile only behind HTTPS. A static-only website host is insufficient because GeoJoy's API, forms, authentication, and admin panel require `server.py`.

### Render web service

The provided Render log shows the service running the custom start command `python3 server.py`, which bypasses the `Procfile`. Previously, with no explicit `HOST`, the server defaulted to `127.0.0.1`; Render therefore could not detect a listener on `0.0.0.0`. The updated server now keeps the loopback default for local runs without `PORT`, but automatically binds to `0.0.0.0` when `PORT` is injected and `HOST` is omitted. An explicit `HOST` remains authoritative.

Recommended Render **Start Command**: `python3 sync_static_assets.py && python3 server.py`. Render supplies `PORT`; the new default handles the public bind. Add `GEOJOY_COOKIE_SECURE=1` in the Render Environment settings (or use the included `Procfile`, which sets it) so admin session cookies remain secure behind HTTPS. Keep a persistent disk mounted for `geojoy_v8.db` and `uploads/`; the free instance can spin down, so first requests may be delayed.

For a Git-based deployment, from the project root stage and push the bundled image assets along with the updated ignore rule:

```bash
git add .gitignore uploads/geojoy_*.webp
git commit -m "Include GeoJoy photo assets"
git push
```

If deploying from an uploaded archive instead, confirm the complete `uploads/` directory is included in the service source. Keep the production database on its persistent disk; do not replace it with a starter database during this photo-only deployment.

The live check on 2026-10-14 found `/`, `/admin/`, `/api/content`, `/api/health`, CSS/JavaScript routes, and the admin favicon returning HTTP 200, but 0 of the 60 referenced image URLs returned successfully. This matches the prior `uploads/*` ignore rule excluding the curated photos from a Git-based deployment. Redeploy the assets above, then repeat the actual GET checks below before considering the live site verified.

After deployment, test the actual GET requests (not just `HEAD`, which this small server does not implement) for both current and legacy URLs:

```bash
BASE=https://geojoy-backend.onrender.com
for path in / /admin/ /static/styles.css /static/app.js /static/admin.css /static/admin.js /static/geojoy-favicon.svg /styles.css /app.js /admin.css /admin.js /uploads/geojoy_regions_tbilisi_dusk.webp; do
  curl -fsS -o /dev/null -w "$path %{http_code}\n" "$BASE$path"
done
```

After the photo redeploy, every listed request should return HTTP 200. The server allowlists the four expected CSS/JavaScript files and favicon under `/static/`; it returns 404 for unrelated project files instead of exposing them.

## Vercel frontend → Render API

The apex domain `https://geojoy.ge/` redirects to the canonical `https://www.geojoy.ge/`. A browser request to `/api/content` stays on Vercel unless Vercel is configured to proxy it. The latest live check on 2026-10-15 found `www.geojoy.ge/api/content?build=8.9.0` still returning Vercel's plain-text 404, while Render's `/api/health` and `/api/content?build=8.9.0` returned JSON HTTP 200. This confirms the backend is currently up and the remaining live issue is that the Vercel rewrite has not been deployed/activated. The root `vercel.json` included here rewrites all `/api/*` requests (including admin and booking routes) and `/uploads/*` media requests to `https://geojoy-backend.onrender.com`. Existing frontend requests remain relative; no `localhost:8052` setting is needed.

In the Vercel project connected to the live `www.geojoy.ge` domain, ensure **Root Directory** points to the folder containing `vercel.json` (the same project root used to serve `index.html`), then commit and deploy that file. Vercel rewrites apply to all domains assigned to that project, including the canonical `www` hostname and apex alias. The static HTML routes (`/admin`, `/admin/`, `/photo-credits`, `/tours`, `/regions`, `/contact`, `/transfers`, and `/about`) are mapped in the same file.

The latest read-only check confirms Render responds with HTTP 200 for `/api/health`, `/api/content?build=8.9.0`, and `/uploads/geojoy_transferslides_56.webp`. After Vercel deploys the rewrite, test `https://www.geojoy.ge/api/content?build=8.9.0` and require HTTP 200 JSON, then test an `/uploads/...` URL through `www.geojoy.ge`. The browser screenshot's repeated `www.geojoy.ge/api/content?build=8.9.0` 404s show that the current live Vercel deployment still needs this configuration; do not treat the local config or a successful Render response alone as end-to-end verification.

## Local verification

For a local-only run, use `python3 server.py` from the project directory with `PORT` unset, then open `http://127.0.0.1:8052/` or `http://127.0.0.1:8052/admin/`. If you choose a local custom `PORT`, explicitly set `HOST=127.0.0.1`. Leave `GEOJOY_COOKIE_SECURE` unset when testing over plain HTTP.

## Direct frontend → Render API calls (v8.9.1)

The public site (`app.js`, `index.html`) now calls the Render backend directly via `API_BASE = 'https://geojoy-backend.onrender.com'` at the top of `app.js`: `GET /api/content`, `POST /api/bookings`, and every `/uploads/...` image URL (the loader rewrites `/uploads/...` values in the API response to absolute Render URLs).

- **Backend must be redeployed on Render** with the updated `server.py`, which adds CORS for the public endpoints only (`/api/content`, `/api/bookings`, `/api/health`). Allowed origins default to `https://www.geojoy.ge` and `https://geojoy.ge`; override with the `GEOJOY_CORS_ORIGINS` env var (comma-separated, e.g. to add a Vercel preview domain).
- The **admin panel** (`admin.js`) intentionally stays on same-origin `/api/...` requests: it uses an `HttpOnly; SameSite=Strict` session cookie, which would not work (and would be unsafe to loosen) cross-site. These requests rely on the `/api/*` rewrite in `vercel.json`, which is unchanged and already points at Render.
- Local development: change `API_BASE` in `app.js` to `''` (empty string) and run `python3 sync_static_assets.py`.
