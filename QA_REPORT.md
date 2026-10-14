# GeoJoy — QA and change report

## Current status

**Local project:** The delivered application passed two independent full browser-verification rounds on fresh disposable copies. The delivery database was not modified by QA.

**Live Render deployment:** Not fully verified and currently missing all referenced photos. On 2026-10-14, the live content API returned 60 unique `/uploads/*.webp` paths; a direct GET test found **0/60 HTTP 200** and **60/60 HTTP 404**. The homepage and app assets respond, but the hero and destination photos do not load. Do not describe the live deployment as complete until the assets are redeployed and retested.

The likely cause is confirmed in the source deployment rules: `.gitignore` contained `uploads/*`, excluding the curated photos from a Git-based deployment. The corrected rule now allows only `uploads/geojoy_*.webp`; the deployment guide includes the exact Git staging/push instructions. The release ZIP contains all 60 WebP files.

**Live admin check:** `/admin/` returns HTTP 200 and renders the GeoJoy Admin Panel login page with a password field. Its stylesheet, JavaScript, favicon, and `/api/health` also return HTTP 200. No live credentials were submitted, so authenticated login and editing workflows remain unverified on Render. No live data was changed.

## Two-round local test results

Each round used a fresh disposable copy of the project and database. These results establish local behavior only; they do not override the live Render photo failure reported above.

| Check | Round 1 | Round 2 |
|---|---:|---:|
| Public page routes returned HTTP 200 | 7 / 7 | 7 / 7 |
| Unique local image URLs checked | 60 / 60 | 60 / 60 |
| Local image response status/type | HTTP 200, `image/webp` | HTTP 200, `image/webp` |
| Homepage images decoded | 42; 0 broken | 42; 0 broken |
| Admin sections loaded | 11 / 11 | 11 / 11 |
| Public/admin horizontal overflow across 1440, 1024, 768, 520, 390, and 320 px | None | None |
| Phone-width logout action | Visible | Visible |
| Browser console/page/request errors | 0 | 0 |
| SQLite restart persistence and integrity | PASS; integrity `ok` | PASS; integrity `ok` |
| HTTPS-configured session-cookie flags | PASS | PASS |

The Tbilisi card image was opened and decoded at **1440 × 960**, **390 × 844**, and **320 × 844**. The browser loaded `uploads/geojoy_regions_tbilisi_dusk.webp`, reported `object-fit: cover`, and showed nonzero natural dimensions at each viewport. Desktop and phone screenshots are in `qa/evidence/`.

## Admin workflows exercised locally

Across the two disposable rounds, QA authenticated, loaded all 11 admin sections, and logged out. It exercised the Tbilisi region image preview, image upload (HTTP 200), save, public rendering after refresh, restoration of the selected Tbilisi photo, representative region/tour edit-save and add/delete paths, the booking form and protected admin booking view, contact save and public telephone-link rendering after refresh, branding and translation save/restore, transfer-slide add/delete/save, image upload/reference clearing, and the mobile logout action. Contact and image changes survived a server-process restart in both copies.

The original database schema and non-photo stored content were compared against the project. The only stored-content difference is the Tbilisi region image path; the source database had **zero booking rows**. SQLite integrity checks passed.

## Live Render verification — 2026-10-14

All checks below used read-only HTTPS GET requests against the URL supplied by the user. No admin form was submitted and no database or account state was changed.

| Live check | Result |
|---|---:|
| `/` public homepage | HTTP 200 |
| `/admin/` admin login route | HTTP 200; login markup and password input present |
| `/api/content?build=8.9.0` | HTTP 200; 60 unique upload paths |
| `/api/health` | HTTP 200 |
| `/static/styles.css`, `/static/app.js`, `/static/admin.css`, `/static/admin.js`, `/static/geojoy-favicon.svg` | HTTP 200 |
| Legacy root `/styles.css`, `/app.js` | HTTP 200 |
| Unique `/uploads/*.webp` paths | **0 / 60 HTTP 200; 60 / 60 HTTP 404** |
| Live authenticated admin features | Not tested; credentials were not supplied or entered |
| Live data changes | None |

The rendered homepage DOM also marked its hero image with `image-load-failed` and `naturalWidth: 0`, consistent with the HTTP 404 results. This is the reason the live deployment is not yet photo-complete.

## Deployment correction

The prior `.gitignore` rule `uploads/*` excluded every image from Git. The corrected file keeps runtime uploads ignored while allowing the bundled images to ship:

```gitignore
uploads/*
!uploads/.gitkeep
!uploads/geojoy_*.webp
```

For Git-based Render deployments, stage the ignore change and image files, then push and wait for Render to redeploy:

```bash
git add .gitignore uploads/geojoy_*.webp
git commit -m "Include GeoJoy photo assets"
git push
```

Keep the production SQLite database and runtime uploads on persistent storage and do not overwrite newer live data with a starter copy. After redeployment, repeat GET checks for all 60 paths and inspect the live homepage before claiming the photo fix is complete.

## Other findings and limitations

- The about-image removal action clears and saves the image reference; the existing server does not expose a physical uploaded-file deletion operation, so tests did not claim it deletes file bytes.
- The data retains one legacy `transferSettings.image` fallback path that intentionally mirrors the first transfer slide for compatibility; it is not a second displayed photo.
- The Security section was opened locally, but password-change and account-recovery submissions were not made. Existing credentials and recovery settings were left unchanged.
- `GEOJOY_COOKIE_SECURE=1` was tested locally: the login response emitted `Secure`, `HttpOnly`, and `SameSite=Strict`. A real external HTTPS reverse-proxy deployment was not exercised by those local checks.
- Live admin route reachability is verified, but live login and authenticated editing are not. Live responsive browser checks across all widths have not been repeated after deployment.

## Evidence

- `qa/round1-results.json` and `qa/round2-results.json` contain the two local full-round results.
- `qa/static-fix-round1.json`, `qa/static-fix-round2.json`, `qa/final-zip-smoke.json`, and `qa/render-port-binding.json` record the targeted static-path, clean-extract, and Render-style bind tests.
- `qa/evidence/` contains the local region-card desktop/mobile captures and authenticated admin/mobile screenshots.
- The photo source, creator, license, original dimensions, and credits are recorded in `photo_manifest.json` and the photo-credit page.


## Corrected release package smoke test — 2026-10-14

After updating `.gitignore` and the deployment notes, the refreshed ZIP was integrity-checked and extracted into a clean temporary directory. The extracted server returned HTTP 200 for the homepage, admin login route, health/content APIs, all required `/static/` CSS/JavaScript/favicon routes, and the legacy root CSS/JavaScript aliases. Its content API listed 60 unique photo paths; **all 60 returned HTTP 200 as `image/webp` and decoded successfully**. The admin login markup/title/password field were present. A temporary Git repository also confirmed that `uploads/geojoy_*.webp` is no longer ignored while arbitrary runtime uploads and `geojoy_v8.db` remain ignored.

This validates the corrected source archive locally. It does **not** repair or verify the already-running Render service; that deployment still needs the corrected assets committed/uploaded and redeployed before the live photo checks can pass.


## API routing diagnosis — 2026-10-15

The user-reported public URL is `https://geojoy.ge/`. A read-only request to `https://geojoy.ge/api/content?build=8.9.0` returned **HTTP 404 with Vercel's JSON not-found response**. This identifies the immediate API 404 as a frontend-origin routing problem: the public `app.js` correctly requests the relative path `/api/content`, but the Vercel deployment had no rewrite to the separate Python backend.

The checked Python source already defines `GET /api/content`; its database path is `Path(__file__).resolve().parent / 'geojoy_v8.db'`, so it is absolute and independent of the process working directory. I tightened that route to exact-match `/api/content` (with optional trailing slash), normalized trailing slashes for API methods, and added JSON 404 responses for unknown GET/DELETE API paths. The frontend's failure banner no longer directs hosted users to start `run_windows.bat` or use local port 8052.

The Render origin returned **HTTP 502** for `/`, `/api/health`, and `/api/content` during this check. Therefore the Vercel routing fix is prepared but cannot be end-to-end verified until the Render service is healthy. A root-level `vercel.json` now proxies `/api/*` and `/uploads/*` to Render and maps the existing static HTML routes. Neither Vercel nor Render was changed from this session; commit and redeploy are still required.


## Local API fix smoke tests — 2026-10-15

A temporary clean copy was launched with its current working directory outside the application folder and with only `PORT` injected. The server bound to `0.0.0.0`, opened the database relative to `server.py`, and served the content API, admin status/protected endpoints, admin HTML, static JavaScript, and an uploaded WebP. `/api/content` and `/api/content/` returned JSON HTTP 200; protected admin endpoints returned JSON HTTP 401; unknown GET, POST, PUT, PATCH, and DELETE `/api/*` routes returned JSON HTTP 404. The `vercel.json` rewrites parsed and matched the configured `/api/:path*` and `/uploads/:path*` targets. Python compilation and JavaScript syntax checks passed, and root/static `app.js` copies matched.

These are local results. The live Vercel 404 and Render 502 remain until the updated project is committed/deployed and the Render service is healthy.


## Live follow-up from screenshot — 2026-10-15

The screenshot's Network panel shows repeated requests to `https://www.geojoy.ge/api/content?build=8.9.0`, each failing with HTTP 404. Fresh read-only GET checks confirm `https://geojoy.ge/` redirects to `https://www.geojoy.ge/`, so `www` is the canonical hostname the browser actually uses. The Vercel response is plain-text `The page could not be found / NOT_FOUND`.

Render has recovered since the earlier check: `https://geojoy-backend.onrender.com/api/health` and `/api/content?build=8.9.0` both return HTTP 200 JSON, and a sample `/uploads/geojoy_transferslides_56.webp` returns HTTP 200 `image/webp`. The remaining live failure is therefore the Vercel rewrite not being present/active on the deployment serving `www.geojoy.ge`; the local `vercel.json` has not yet been reflected in that running deployment. The project and deployment docs now call out the canonical hostname and this verified split status. End-to-end success remains unverified until the Vercel project deploys the rewrite and `https://www.geojoy.ge/api/content?build=8.9.0` returns HTTP 200 JSON.
