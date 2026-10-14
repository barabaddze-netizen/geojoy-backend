# GeoJoy Tbilisi update — completion checklist

- [x] Replace the Tbilisi region photo with the verified authentic Old Tbilisi/fortress-at-dusk source and local WebP; remove the retired image path and file.
- [x] Confirm the replacement appears in the public region card and admin editor; upload, save, refresh, restore and retest it through the existing UI.
- [x] Preserve routes, APIs, authentication flow, languages, content, business logic and SQLite schema; verify only the Tbilisi region image field changed in stored content.
- [x] Bind to `0.0.0.0` by default when a platform injects `PORT` but no `HOST`; retain loopback when local `PORT` is unset and respect explicit `HOST`/HTTPS cookie settings.
- [x] Provide a physical `/static/` directory, synchronize the existing CSS/JS sources, support legacy root aliases, and restrict static serving to the intended assets.
- [x] Make the existing admin site-view/logout controls visible at phone widths with one scoped CSS rule; verify no overflow at all seven checked widths.
- [x] Complete two independent browser rounds and retain result JSON, screenshots and the current QA report.
- [x] Add a self-hosting guide with URL templates, password-change guidance, persistent data handling, HTTPS reverse proxy and backup steps.

## Known limits

A Render service is visible in the user's screenshot, but it is failing its port scan; no healthy public URL has been supplied or verified. The about-image removal control clears its content reference but does not delete the uploaded file from disk. Password-change/recovery submissions and external HTTPS deployment were not tested.

## Follow-up static-path repair

- [x] Add physical `/static/` files and sync script, safe route allowlist, legacy root aliases, local favicon and provider `Procfile`.
- [x] Run the targeted path, image, browser, admin-login and responsive suite twice on fresh local copies.
- [ ] Verify the user's deployed live site after its URL or hosting access is supplied; no production host was available in this session.

- [x] Fresh-extract the release ZIP and rerun the asset, route, image, browser and admin-login smoke checks.

## Render port-scan follow-up

- [x] Diagnose the provided log: the custom start command `python3 server.py` bypassed the Procfile while the app defaulted to loopback.
- [x] Change the hosted default bind behavior and document the Render start command/cookie environment setting.
- [ ] Confirm a successful external Render deployment after the user redeploys and supplies its public URL.

- [x] Reproduce Render's injected `PORT` with no `HOST`; verify listener on `0.0.0.0`, HTTP 200 routes, and explicit loopback override.
- [ ] Verify the user's Render deployment after the updated source is deployed; a healthy external URL has not yet been supplied.
- [x] Verify local startup without `PORT` still binds to `127.0.0.1` and serves the health endpoint.
