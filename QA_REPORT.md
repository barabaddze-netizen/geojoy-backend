# GeoJoy — QA and change report

## Outcome

**The final updated project passed two independent full browser-verification rounds.** Each round used a fresh disposable copy of the delivered database and files; the delivery database was not modified by the QA workflows.

The selected Tbilisi region image now uses a different, authentic Old Tbilisi/fortress-at-dusk photograph. Its locally served WebP derivative is **1,913 × 1,920 px** (799,414 bytes); the source image is **2,933 × 2,943 px**. The existing Tbilisi region card and admin editor both display the new local path. The retired Tbilisi region image file and its active references were removed.

The admin stylesheet received one targeted mobile rule to show the existing site-view and logout actions below the admin tab bar. No application routes, content, API handlers, business logic, authentication rules, or database schema were rewritten. The Python server now accepts optional `HOST` and `GEOJOY_COOKIE_SECURE` environment settings so an HTTPS reverse-proxy deployment can bind safely and set a Secure session cookie; its loopback/plain-HTTP local defaults remain unchanged.

## Two-round test results

| Check | Round 1 | Round 2 |
|---|---:|---:|
| Public page routes returned HTTP 200 | 7 / 7 | 7 / 7 |
| Unique local image URLs checked | 60 / 60 | 60 / 60 |
| Local image response status/type | HTTP 200, `image/webp` | HTTP 200, `image/webp` |
| Homepage images decoded | 42; 0 broken | 42; 0 broken |
| Admin sections loaded | 11 / 11 | 11 / 11 |
| Public/admin horizontal overflow across 1440, 1024, 768, 520, 390, 360 and 320 px | None | None |
| Phone-width logout action | Visible | Visible |
| Browser console/page/request errors | 0 | 0 |
| SQLite restart persistence and integrity | PASS; integrity `ok` | PASS; integrity `ok` |
| HTTPS-configured session-cookie flags | PASS | PASS |

The Tbilisi card image was also opened and decoded at **1440 × 960**, **390 × 844** and **320 × 844**. The browser loaded `uploads/geojoy_regions_tbilisi_dusk.webp`, reported `object-fit: cover`, and showed a nonzero, natural image size at each tested viewport. Desktop and phone screenshots are included in `qa/evidence/`.

## Admin workflows actually exercised

Across the two disposable rounds, the browser test authenticated, loaded all 11 admin sections and logged out. It exercised the existing Tbilisi region image preview, image upload (HTTP 200), save, public rendering after refresh, restoration of the selected Tbilisi photo, and a second public refresh. It also exercised representative region/tour edit-save and add/delete paths, the booking form and protected admin booking view, contact save plus public telephone-link rendering after refresh, branding and translation save/restore, transfer-slide add/delete/save, image upload/reference clearing, and the mobile logout action. Contact and image changes survived a server-process restart in both copies.

The original database schema and non-photo stored content were compared against the project before this update. The only stored-content difference is the Tbilisi region image path; the source database had **zero booking rows**. Schema integrity checks passed.

### Scope limits recorded honestly

- The existing about-image removal action was verified to clear and save the image reference. The existing server does not expose a physical uploaded-file deletion operation; the test did not claim that it deletes file bytes.
- The data retains one legacy `transferSettings.image` fallback path that intentionally mirrors the first transfer slide for compatibility. It is not a second displayed photo; the 60 distinct local photo files remain unique.
- The Security section was opened, but password-change and account-recovery submissions were intentionally not made. The existing credentials and recovery settings were left unchanged.
- `GEOJOY_COOKIE_SECURE=1` was tested on a local login response: it emitted `Secure`, `HttpOnly` and `SameSite=Strict`. A real external HTTPS/Nginx deployment was not run.
- No production host/domain was available or published. The URL forms in `DEPLOYMENT.md` are placeholders, not live links. Change the existing admin password and configure HTTPS before public exposure.

## Evidence

- `qa/round1-results.json` and `qa/round2-results.json` contain the machine-readable round results.
- `qa/evidence/` contains the region-card desktop/mobile captures and authenticated admin/mobile screenshots.
- The photo source, creator, license and original dimensions are recorded in `photo_manifest.json` and the existing photo-credit page.

## Follow-up: static asset and deployment-path regression

A fresh local reproduction confirmed that this project's Python server already served `/static/styles.css`, `/static/app.js`, `/static/admin.css`, and `/static/admin.js` successfully, but returned 404 for legacy root requests such as `/styles.css` and `/app.js`. The project also lacked a physical `static/` directory for conventional hosts. I added synchronized `static/` copies, a root-asset compatibility route, a five-file `/static/` allowlist (including a local favicon), and a `Procfile` that syncs assets before starting the existing Python server. Requests for arbitrary files such as `/static/geojoy_v8.db` now correctly return 404.

The targeted static-path suite then passed twice on fresh disposable project/database copies:

| Follow-up check | Round 1 | Round 2 |
|---|---:|---:|
| `/static/` and legacy root CSS/JS asset requests | 9 / 9 HTTP 200 | 9 / 9 HTTP 200 |
| Unique local WebP image endpoints | 60 / 60 HTTP 200 | 60 / 60 HTTP 200 |
| Public, admin, credits, section and health routes | 8 / 8 HTTP 200 | 8 / 8 HTTP 200 |
| Admin login and visible sections | PASS; 11 tabs | PASS; 11 tabs |
| Public responsive overflow at 1440, 768, 390 and 320 px | None | None |
| Browser console/page/request errors | 0 | 0 |
| Protected database-file path under `/static/` | HTTP 404 (expected) | HTTP 404 (expected) |

Python compilation and both JavaScript syntax checks passed for this follow-up. The added report files are `qa/static-fix-round1.json` and `qa/static-fix-round2.json`.

**Live-host limitation:** no live URL or hosting access was provided. Thus these results verify the updated project on its local Python server and fresh copies, not the user's deployed website or an external hosting platform. In particular, the reported live `/static/styles.css` failure still needs a request against the actual domain to confirm the host is running this project and the included `Procfile`/static directory. Do not treat the external live site as verified yet.

A clean extraction of the release ZIP was also run through the same targeted runtime suite. It passed all 9 static/legacy asset paths, all 60 image endpoints, all 8 routes, admin login and the 11-tab check at the four viewport widths with zero browser errors. Its machine-readable result is `qa/final-zip-smoke.json`. This remains a local clean-extract test, not proof of the user's external deployment; the deployed site still needs its actual URL for verification.
