# GeoJoy tourism website

This is the existing GeoJoy Python/SQLite application—not a static-site rebuild. Its routes, APIs, database schema, four-language content, authentication, booking form, uploads and admin capabilities are retained.

## Run locally

From this directory, with Python 3.10 or newer:

```bash
python3 server.py
```

Open the local website at `http://127.0.0.1:8052/` and the admin panel at `http://127.0.0.1:8052/admin/`. The server binds to loopback by default. `PORT` selects the port; `HOST` selects the bind address.

When a hosting platform supplies `PORT` but no `HOST` (as Render does), the server binds to `0.0.0.0` so the platform's port scanner can reach it. An explicit `HOST` always overrides this. Running locally without `PORT` still defaults to loopback.

The original CSS/JavaScript sources remain at the project root. Conventional hosts also need the matching files in `static/` (plus the local SVG favicon); run `python3 sync_static_assets.py` after changing those sources. The included `Procfile` runs that sync before starting the app. The server supports both `/static/<asset>` and legacy root-level CSS/JavaScript URLs.

## Preserve data

- `geojoy_v8.db` is the existing SQLite database; do not replace it with a sample or empty database when updating an existing installation.
- `uploads/` stores the site's local photos and admin-uploaded media. Preserve it alongside the database.
- Back up both locations before changes. See [DEPLOYMENT.md](DEPLOYMENT.md) for a systemd, Nginx, HTTPS and backup example.
- There is no schema migration for this update. Only the Tbilisi region's saved image path changes in the delivered database.

## Admin security

The existing administrator credential remains in the database and is not published in this handoff. Change it to a unique strong password and set a recovery phrase in **Admin → Security** before exposing the site publicly. `GEOJOY_ADMIN_PASSWORD` is only an initial credential for a database that does not yet have an administrator security record; it does not reset an existing account.

For an HTTPS reverse-proxy deployment, set `GEOJOY_COOKIE_SECURE=1` so the session cookie includes `Secure` in addition to its existing `HttpOnly` and `SameSite=Strict` flags. Do not enable that flag for a plain-HTTP local test.

## Photos and verification

The replacement Tbilisi region photo is `uploads/geojoy_regions_tbilisi_dusk.webp`. Source, creator, license and original dimensions for site photos are recorded in [`photo_manifest.json`](photo_manifest.json) and the existing [photo credits page](photo-credits.html).

The two browser-verification runs and documented scope limits are in [`QA_REPORT.md`](QA_REPORT.md); screenshot and JSON evidence is under [`qa/`](qa/).

## Live URL status

A Render web service is visible in the supplied dashboard screenshot, but it was still failing its port scan. No reachable public service URL was supplied or verified. Once the service is healthy, the URL patterns are `https://YOUR_DOMAIN/` for the public website and `https://YOUR_DOMAIN/admin/` for the admin panel; these remain templates, not live links.
