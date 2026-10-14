# GeoJoy Tbilisi update — completion checklist

- [x] Replace the Tbilisi region photo with the verified authentic Old Tbilisi/fortress-at-dusk source and local WebP; remove the retired image path and file.
- [x] Confirm the replacement appears in the public region card and admin editor; upload, save, refresh, restore and retest it through the existing UI.
- [x] Preserve routes, APIs, authentication flow, languages, content, business logic and SQLite schema; verify only the Tbilisi region image field changed in stored content.
- [x] Add the optional safe host-bind and HTTPS `Secure` cookie environment settings, retaining loopback/plain-HTTP local defaults.
- [x] Provide a physical `/static/` directory, synchronize the existing CSS/JS sources, support legacy root aliases, and restrict static serving to the intended assets.
- [x] Make the existing admin site-view/logout controls visible at phone widths with one scoped CSS rule; verify no overflow at all seven checked widths.
- [x] Complete two independent browser rounds and retain result JSON, screenshots and the current QA report.
- [x] Add a self-hosting guide with URL templates, password-change guidance, persistent data handling, HTTPS reverse proxy and backup steps.

## Known limits

No persistent public host or domain was configured. The about-image removal control clears its content reference but does not delete the uploaded file from disk. Password-change/recovery submissions and external HTTPS deployment were not tested.

## Follow-up static-path repair

- [x] Add physical `/static/` files and sync script, safe route allowlist, legacy root aliases, local favicon and provider `Procfile`.
- [x] Run the targeted path, image, browser, admin-login and responsive suite twice on fresh local copies.
- [ ] Verify the user's deployed live site after its URL or hosting access is supplied; no production host was available in this session.

- [x] Fresh-extract the release ZIP and rerun the asset, route, image, browser and admin-login smoke checks.
