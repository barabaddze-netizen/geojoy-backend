# GeoJoy deployment guide

This package keeps the existing Python server, SQLite schema, APIs, routes, four-language content, authentication, and upload directory. It is a small self-hosted app; it is **not** a static-site bundle. The only new server settings are optional `HOST` binding and a production `GEOJOY_COOKIE_SECURE=1` flag. The site server itself does not terminate TLS.

## URLs

After your DNS and HTTPS certificate are configured, use:

- Public website: `https://YOUR_DOMAIN/`
- Admin panel: `https://YOUR_DOMAIN/admin/`

These are URL templates, not live links. Both paths use the same GeoJoy host. No persistent production host or domain was connected for this handoff.

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

Deploy the complete project, including `static/`, `uploads/`, and `geojoy_v8.db`. The canonical CSS/JavaScript sources remain at the project root; run `python3 sync_static_assets.py` after changing them to refresh the conventional `/static/` copies (four CSS/JS files plus the local SVG favicon). The included `Procfile` performs this sync and starts the existing Python app with `HOST=0.0.0.0` and `GEOJOY_COOKIE_SECURE=1`; the hosting provider must supply `PORT`, HTTPS, and persistent storage for the database and uploads. Use this Procfile only behind HTTPS. A static-only website host is insufficient because GeoJoy's API, forms, authentication, and admin panel require `server.py`.

After deployment, test the actual GET requests (not just `HEAD`, which this small server does not implement) for both current and legacy URLs:

```bash
BASE=https://YOUR_DOMAIN
for path in / /admin/ /static/styles.css /static/app.js /static/admin.css /static/admin.js /static/geojoy-favicon.svg /styles.css /app.js /admin.css /admin.js /uploads/geojoy_regions_tbilisi_dusk.webp; do
  curl -fsS -o /dev/null -w "$path %{http_code}\n" "$BASE$path"
done
```

Every listed request should return HTTP 200. The server allowlists the four expected CSS/JavaScript files and favicon under `/static/`; it returns 404 for unrelated project files instead of exposing them.

## Local verification

For a local-only run, use `python3 server.py` from the project directory, then open `http://127.0.0.1:8052/` or `http://127.0.0.1:8052/admin/`. Leave `HOST` unset for the safe loopback default and leave `GEOJOY_COOKIE_SECURE` unset when testing over plain HTTP.
