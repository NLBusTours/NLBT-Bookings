# Bus availability activation and operations

The NLBT booking form checks three independent calendar feeds using encrypted GitHub Actions repository secrets. Each private address is never included in client JavaScript or public issue content.

- RT2 uses the Google Calendar currently labelled **Artie (RT)** (the previous Artie vehicle is retired).
- RX2 uses **Archie 2.0 (RX2)**.
- R3 uses **Arthree (R3)**.

Required repository secrets are `NLBT_RT2_ICAL_URL`, `NLBT_RX2_ICAL_URL` and `NLBT_R3_ICAL_URL`. The source calendars must be maintained with correct start/end times and block busy hours including any required preparation or travel buffer. The workflow refreshes on the half hour, on relevant push, and when manually dispatched.

Check Actions workflow `NLBT bus availability sync` for a successful run. Verify GitHub issue #1 contains a current `generated_at` and only sanitized date/time ranges. If the fetch fails, the website should say availability is **not verified** and never falsely claim an opening.
