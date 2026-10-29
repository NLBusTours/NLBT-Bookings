# NL Bus Tours Booking Form

This is the customer booking inquiry form embedded from GitHub Pages into the NL Bus Tours GoDaddy website.

## Fleet (October 2026)
- **RT2:** Active. Availability uses the connected Google calendar currently named **RT**, as confirmed by the owner. The original Artie (RT) remains retired and is NOT offered as an active bus.
- **RX2 (Archie 2.0):** Active. Availability uses the **Archie 2.0 (RX2)** Google calendar.
- **R3 (Arthree):** Active, 17-passenger mini coach. Availability uses the **Arthree (R3)** Google calendar.
- **Artie (RT), Arbie (RB), Archie (RX):** Retired. Visible as memorial fleet tiles and disabled in the booking dropdown.

The RT2 and RX2 photo and specification placeholders must be replaced with actual owner-approved exterior/interior photographs and accurate capacities. The retired fleet retains the owner's original photo assets.

## Calendar availability setup (private, one time)
The form reads a sanitized status issue, **not** raw calendar events. Customers see only booked or held time ranges for the selected bus and date. This is not a reservation system.

1. Sign into the Google Calendar account that owns each NLBT bus calendar. Go to **Settings**, select the calendar, and find **Integrate calendar → Secret address in iCal format**. If you lack permissions, ask the calendar owner. Never put a secret iCal URL into an email, screenshot or conversation.
2. Open GitHub repository **Settings → Secrets and variables → Actions**: https://github.com/NLBusTours/NLBT-Bookings/settings/secrets/actions
3. Create **three separate repository secrets**:
    - `NLBT_RT2_ICAL_URL` = iCal subscription address for the calendar **currently named RT**.
    - `NLBT_RX2_ICAL_URL` = iCal subscription address for **Archie 2.0 (RX2)**.
    - `NLBT_R3_ICAL_URL` = iCal subscription address for **Arthree (R3)**.
4. From GitHub **Actions → NLBT bus availability sync**, manually trigger **Run workflow** once: https://github.com/NLBusTours/NLBT-Bookings/actions/workflows/sync-bus-availability.yml
5. Confirm the action succeeds and issue [#1](https://github.com/NLBusTours/NLBT-Bookings/issues/1) contains a current anonymous `generated_at` timestamp. Test busy slots for each bus.

The workflow refreshes every ~30 minutes. GitHub Actions scheduled jobs may run late; the website shows **Calendar not verified** if the snapshot is older than two hours, invalid, or has not been configured. It **never invents availability** and still allows manual booking inquiries when unverified. A known booking conflict blocks submitting the same bus/time.

### Privacy and reliability
- All raw calendar feeds and tokens remain in GitHub Actions secrets and the runner.
- Only merged date/time intervals appear on the public issue. No titles, client names, emails, locations, event IDs or guest counts are published.
- Each bus is checked independently; an RX2 booking does not block R3 or RT2.
- Calendar availability does not account for travel/setup buffers unless they are already marked as busy in the source calendar. Driver assignment must be confirmed by staff.
- The form's existing Web3Forms contact submission and thank-you page remain unchanged.
- Until configured, customers may submit requests, but no verified availability is promised.

## Hosting
GitHub Pages publishes the `main` branch root; the existing GoDaddy iframe URL does not need to change for code-only upgrades.
