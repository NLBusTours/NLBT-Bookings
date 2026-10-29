# NL Bus Tours Booking Form

This is the customer booking inquiry form embedded from GitHub Pages into the NL Bus Tours GoDaddy website.

## Fleet (October 2026)
- **Artie 2.0 (RT2):** Active. Availability uses the connected Google calendar currently named **RT**, as confirmed by the owner. The original Artie (RT) remains retired and is NOT offered as an active bus.
- **RX2 (Archie 2.0):** Active. Availability uses the **Archie 2.0 (RX2)** Google calendar.
- **R3 (Arthree):** Active, 17-passenger mini coach. Availability uses the **Arthree (R3)** Google calendar.
- **Artie (RT), Arbie (RB), Archie (RX):** Retired. Visible as memorial fleet tiles and disabled in the booking dropdown.

## Active fleet photos
The owner supplied the four authentic vehicle photographs. They are optimized into one mobile-friendly WebP asset: `assets/active-fleet-photos.webp`. The top row shows **Artie 2.0 (RT2)** (black exterior and teal lounge seating); the bottom row shows **Archie 2.0 (RX2)** (white exterior and grey lounge seating). The active bus tiles show exterior photos; tapping opens both exterior and interior. These photos must not be swapped between buses.

Fleet tile order is **Artie 2.0 (RT2), Archie 2.0 (RX2), Arthree (R3), Artie (RT), Arbie (RB), Archie (RX)**. The three original retired buses feature ❤️‍🩹🕊️ instead of coloured hearts, preserve their original images and are unbookable. The owner can supply accurate seating capacities and amenities for RT2 and RX2 separately; no unverified specifications are advertised.

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

## New bus descriptions (owner-confirmed)
- **Artie 2.0 (RT2):** Black exterior, teal lounge seating, two high-power Bluetooth speakers with superior sound compared with RX2, and more dynamic party lighting.
- **Archie 2.0 (RX2):** White exterior, grey lounge seating, two high-power Bluetooth speakers and party lighting.
- Both have short marketing copy on fleet tiles, optional desktop hover descriptions, and expanded detailed descriptions on tap. No unverified passenger capacities are advertised.

## Calendar booking-entry safety
An empty slot does **not** guarantee availability. The checker covers events actually entered on the correct Google Calendar, and pending inquiries or unrecorded holds do not appear. Therefore the customer-facing message states **No calendar conflict found — NOT confirmed**. Booking staff should record firm commitments or tentative holds as *Busy* on the correct bus calendar, and release those holds if cancelled. Updates can take time to reach the private iCal feed and scheduled sync. A previously reported RT2 booking for October 31, 2026, from 9–11 PM was absent from the connected RT calendar when checked on October 29; confirm with Emily before treating the time as open.
