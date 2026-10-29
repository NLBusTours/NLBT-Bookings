# Connect the existing NLBT Inquiries spreadsheet without editing Emily's automation

**Important:** This is a completely separate, read-only Apps Script project. Never add the code to Emily's existing spreadsheet Apps Script project, change a sheet column, rename a bus/dropdown value, or overwrite her calendar-sync scripts.

## What our website will do
1. Every ~30 minutes, the existing GitHub Actions job reads the three private Google Calendar iCal feeds.
2. In the same private job, an independent read-only Apps Script checks the existing **NLBT Inquiries** Google Sheet (tab `NLBT Inquiries`, columns C:G).
3. The script accepts these exact existing bus names: **Artie 2.0 (RT2)**, **Archie 2.0 (RX2)** and **Arthree (R3)**. Old retired-bus rows are ignored.
4. **Confirmed** rows block their time; **Pending** rows become provisional holds; **Declined** rows do not block. Both statuses are folded into anonymous occupied intervals.
5. The job merges those intervals with the existing Google Calendar intervals, then publishes only booked/held time ranges to GitHub issue #1. No customer names, contact info, payments, email addresses, driver names, event IDs or raw rows are sent to GitHub.
6. Until this connection is working, **RT2 remains manual confirmation**. RX2 and R3 continue working from their calendars. If the Sheet bridge fails later, RT2 reverts to manual confirmation automatically.

## One-time setup, under the NLBT Google account

1. While signed in as the account that can **read** the NLBT Inquiries Sheet, open [a NEW standalone Google Apps Script project](https://script.google.com/home/projects/create). Do **not** open Extensions → Apps Script in Emily's live Sheet.
2. Name the project **NLBT Website Availability - Read Only**.
3. Paste the full contents of [standalone-sheets-bridge.gs](./standalone-sheets-bridge.gs) into the new project's `Code.gs` and save.
4. In **Project Settings → Script properties**, add `NLBT_SYNC_TOKEN`. Its value should be a unique, unpredictable token from a password manager (at least 32 characters). Keep it confidential.
5. Click **Deploy → New deployment → Web app**. Set **Execute as: Me** and **Who has access: Anyone**, then authorize the script's read access to the spreadsheet. This deliberately exposes a *token-gated* web app, not the private spreadsheet. The output contains **only sanitized time ranges**. Do not use the public website's URL here.
6. Copy the **Web app URL ending in `/exec`**. Do not share the token or URL in a screenshot or chat.
7. In [NLBT-Bookings GitHub Actions secrets](https://github.com/NLBusTours/NLBT-Bookings/settings/secrets/actions), add:
   - `NLBT_SHEETS_BRIDGE_URL` = standalone Web app `/exec` URL.
   - `NLBT_SHEETS_BRIDGE_TOKEN` = same secret token stored in the standalone Script Properties.
8. In [GitHub Actions](https://github.com/NLBusTours/NLBT-Bookings/actions/workflows/sync-bus-availability.yml), manually run **NLBT bus availability sync** once.
9. Check [anonymous availability issue #1](https://github.com/NLBusTours/NLBT-Bookings/issues/1): `sheet_verified` must be `true` and RT2 busy hours should include a confirmed RT2 booking such as November 7, 2026 10 PM–midnight and a pending hold such as October 31, 2026 9–11 PM, unless Emily has changed their statuses since this review.
10. Confirm the public booking form shows appropriate occupied hours when selecting RT2 on those dates.

## Security and operations

- Keep the source Sheet private. **Never publish the Sheet itself to the web**, expose Google Sheets API keys or place a script token in GitHub source files or website JavaScript.
- This integration never writes to Sheets or Google Calendar. It uses `getDisplayValues()` only.
- Google Apps Script `doPost` verifies a shared secret and returns sanitized anonymous intervals. HTTP GET to the endpoint is not a supported data route.
- If changing the standalone Apps Script code later, deploy a **new version** to the existing deployment and verify the same `/exec` URL remains in GitHub secrets.
- Refresh is approximately every 30 minutes, not instantaneous. GitHub scheduled runs and iCal feeds can be delayed. Driver, routing and turnaround times remain subject to staff confirmation.
- The public site never indicates a firm reservation; it blocks known confirmed and pending slots and flags unverified feeds.
- Important: The app uses the full spreadsheet's header and existing status strings. If Emily later changes the tab headers or status choices, our independent bridge should fail safely instead of publishing incomplete occupancy.

## If you want a simpler alternative later
Once Emily's original Sheet → Calendar mapping for **Artie 2.0 (RT2)** is fixed and all confirmed and provisional holds are reliably added to the calendar, the supplemental Sheet bridge can be retired. Until then it is an extra safety net.
