/* Public, read-only NLBT calendar checker. Never fetch private calendar feeds here. */
(() => {
  'use strict';
  const URL = 'https://api.github.com/repos/NLBusTours/NLBT-Bookings/issues/1';
  const START = '<!-- NLBT_AVAILABILITY_JSON_START';
  const END = 'NLBT_AVAILABILITY_JSON_END -->';
  const MAX_AGE = 2 * 60 * 60 * 1000;
  const BUS_IDS = ['RT2', 'RX2', 'R3'];
  // All three active buses use the same calendar-based availability checks.

  function parseDate(iso) {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(iso || '')) return null;
    const [year, month, day] = iso.split('-').map(Number);
    const date = new Date(Date.UTC(year, month - 1, day));
    return date.toISOString().slice(0, 10) === iso ? date : null;
  }
  function addDay(iso) {
    const date = parseDate(iso);
    if (!date) return null;
    date.setUTCDate(date.getUTCDate() + 1);
    return date.toISOString().slice(0, 10);
  }
  function clockMinutes(time) {
    if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(time || '')) return null;
    const [hour, minute] = time.split(':').map(Number);
    return hour * 60 + minute;
  }
  function requestedSegments(date, time, duration) {
    if (!parseDate(date)) return null;
    const start = clockMinutes(time);
    const length = Number(duration) * 60;
    if (start === null || !Number.isInteger(length) || length < 60 || length > 720 || length % 30 !== 0) return null;
    const segments = [];
    let day = date, from = start, remaining = length;
    while (remaining > 0) {
      const until = Math.min(1440, from + remaining);
      segments.push([day, from, until]);
      remaining -= until - from;
      day = addDay(day);
      from = 0;
    }
    return segments;
  }
  function currentSnapshot(snapshot, now = Date.now()) {
    return Boolean(snapshot && snapshot.version === 1 &&
      snapshot.timezone === 'America/St_Johns' &&
      Number.isFinite(Date.parse(snapshot.generated_at)) &&
      Date.parse(snapshot.generated_at) <= now + 60000 &&
      now - Date.parse(snapshot.generated_at) <= MAX_AGE &&
      parseDate(snapshot.from_date) && parseDate(snapshot.through_date) &&
      snapshot.buses && BUS_IDS.every(bus => snapshot.buses[bus] &&
         snapshot.buses[bus].busy && typeof snapshot.buses[bus].busy === 'object'));
  }
  function rangesFor(snapshot, bus, day) {
    if (day < snapshot.from_date || day > snapshot.through_date) return null;
    const ranges = snapshot.buses[bus]?.busy?.[day] || [];
    if (!Array.isArray(ranges)) return null;
    if (ranges.some(x => !Array.isArray(x) || x.length !== 2 ||
        !Number.isInteger(x[0]) || !Number.isInteger(x[1]) ||
        x[0] < 0 || x[1] > 1440 || x[0] >= x[1])) return null;
    return ranges;
  }
  function status(snapshot, bus, date, time, duration, now = Date.now()) {
    if (!BUS_IDS.includes(bus)) return 'invalid';
    const segments = requestedSegments(date, time, duration);
    if (!segments) return 'invalid';
    if (!currentSnapshot(snapshot, now)) return 'unknown';
    for (const [day, from, until] of segments) {
      const ranges = rangesFor(snapshot, bus, day);
      if (ranges === null) return 'unknown';
      if (ranges.some(([start, end]) => from < end && until > start)) return 'booked';
    }
    return 'available';
  }
  function clockLabel(total) {
    const hour = Math.floor(total / 60) % 24;
    return (hour % 12 || 12) + ':' + String(total % 60).padStart(2, '0') + (hour < 12 ? ' AM' : ' PM');
  }
  function busyText(snapshot, bus, date, now = Date.now()) {
    if (!currentSnapshot(snapshot, now)) return null;
    if (!BUS_IDS.includes(bus) || !parseDate(date)) return null;
    const ranges = rangesFor(snapshot, bus, date);
    if (ranges === null) return null;
    if (!ranges.length) return 'No bookings or holds currently shown for this bus. Pending requests may not be entered yet.';
    if (ranges.length === 1 && ranges[0][0] === 0 && ranges[0][1] === 1440) return 'Already booked/held: All day.';
    return 'Already booked/held: ' + ranges.map(([a, b]) => clockLabel(a) + '–' + clockLabel(b)).join('; ') + '.';
  }
  if (typeof module !== 'undefined' && module.exports) {
    module.exports = {requestedSegments, currentSnapshot, status, busyText};
  }
  if (typeof document === 'undefined') return;
  const form = document.getElementById('bookingForm');
  const bus = document.getElementById('bus-choice');
  const date = document.getElementById('raw-date');
  const time = document.getElementById('booking-time');
  const duration = document.getElementById('booking-duration');
  const panel = document.getElementById('bus-availability');
  const message = document.getElementById('bus-availability-status');
  const details = document.getElementById('bus-busy-hours');
  const refresh = document.getElementById('bus-refresh');
  if (![form,bus,date,time,duration,panel,message,details,refresh].every(Boolean)) return;
  let snapshot = null, state = 'loading', lastLoad = 0;
  function render() {
    panel.hidden = !BUS_IDS.includes(bus.value);
    if (panel.hidden) return;
    details.textContent = '';
    if (!date.value) {message.textContent = 'Choose a date to see this bus’s busy hours.';return;}
    if (currentSnapshot(snapshot)) {
      details.textContent = busyText(snapshot, bus.value, date.value) || 'The requested date is outside the verified calendar range.';
    }
    if (!time.value || !duration.value) {
      message.textContent = 'Select a start time and duration to check the requested hours.';
      return;
    }
    const result = status(snapshot, bus.value, date.value, time.value, duration.value);
    if (result === 'booked') message.textContent = 'This bus is already booked during some or all of your requested hours. Choose another date, time or bus.';
    else if (result === 'available') message.textContent = 'No calendar conflict found for these hours. The bus is NOT confirmed: pending requests may not yet appear. Our team will verify availability.';
    else if (result === 'invalid') message.textContent = 'Choose a valid start time and duration between 1 and 12 hours (in half-hour increments).';
    else message.textContent = state === 'loading'
      ? 'Checking the bus calendar…'
      : 'Calendar not verified right now. You can still send an inquiry for manual confirmation.';
    if (!currentSnapshot(snapshot)) details.textContent = 'Exact booked hours are unavailable until the calendar feed is connected and up to date.';
  }
  async function load(force = false) {
    if (!force && Date.now() - lastLoad < 60000) return;
    lastLoad = Date.now();
    state = 'loading';
    render();
    try {
      const res = await fetch(URL, {cache:'no-store', headers:{Accept:'application/vnd.github+json'}});
      if (!res.ok) throw new Error('Calendar snapshot unavailable');
      const issue = await res.json();
      if (typeof issue.body !== 'string') throw new Error('Invalid public snapshot');
      const from = issue.body.indexOf(START), to = issue.body.indexOf(END, from + START.length);
      if (from < 0 || to < 0) throw new Error('Snapshot missing');
      const data = JSON.parse(issue.body.slice(from + START.length, to).trim());
      if (!currentSnapshot(data)) throw new Error('Snapshot stale or invalid');
      snapshot = data;state = 'ready';
    } catch (_) {snapshot = null; state = 'unknown';}
    render();
  }
  for(const field of [bus,date,time,duration]) {
    field.addEventListener('change', render);
    field.addEventListener('input', render);
  }
  refresh.addEventListener('click',()=>load(true));
  // Capture BEFORE existing Web3Forms submit handler.
  form.addEventListener('submit',event=>{
    if (!BUS_IDS.includes(bus.value)) {
      event.preventDefault();event.stopImmediatePropagation();
      message.textContent='Please select one of the three active buses.';bus.focus();return;
    }
    const result = status(snapshot,bus.value,date.value,time.value,duration.value);
    if (result === 'booked' || result === 'invalid') {
      event.preventDefault();event.stopImmediatePropagation();panel.hidden=false;
      message.textContent = result === 'booked'
        ? 'This bus is booked during your requested hours. Please select another date, time or bus.'
        : 'Please enter a valid start time and duration to send your inquiry.';
      panel.scrollIntoView({behavior:'smooth',block:'center'});
    }
  },true);
  render();load();
})();
