/**
 * Standalone, READ-ONLY bridge for the NLBT booking availability checker.
 * Create a NEW Apps Script project under the NLBT Google account.
 * Do NOT paste into or modify Emily's spreadsheet-bound automation.
 *
 * Deploy as Web App: execute as Me, access Anyone.
 * Set Script Property NLBT_SYNC_TOKEN to a long random secret.
 * Put the /exec URL and the same token in GitHub Actions secrets.
 * This endpoint returns ONLY merged BUSY date/time intervals, never any
 * guest names, emails, driver details, booking IDs or raw sheet rows.
 */
const NLBT_BOOKING_SHEET_ID = '1FJDjnPzA5A-9_LnOPBhBtIvvV7jcLhI593Q4pib3R7E';
const NLBT_TAB_NAME = 'NLBT Inquiries';
const NLBT_ZONE = 'America/St_Johns';
const NLBT_MAX_DAYS = 400;

function doPost(event) {
  try {
    const expected = PropertiesService.getScriptProperties().getProperty('NLBT_SYNC_TOKEN');
    const input = JSON.parse(event && event.postData && event.postData.contents || '{}');
    if (!expected || typeof input.token !== 'string' ||
        input.token.length !== expected.length || input.token !== expected) {
      return nlbtJson_({error:'Unauthorized'});
    }
    return nlbtJson_(nlbtOccupancy_());
  } catch (error) {
    // Do not reveal spreadsheet contents, ID, token, names or error details.
    return nlbtJson_({error:'Unable to verify booking feed'});
  }
}

function nlbtJson_(data) {
  return ContentService.createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

function nlbtOccupancy_() {
  const spreadsheet = SpreadsheetApp.openById(NLBT_BOOKING_SHEET_ID);
  const sheet = spreadsheet.getSheetByName(NLBT_TAB_NAME);
  if (!sheet) throw new Error('Source sheet unavailable');
  const headings = sheet.getRange('C1:G1').getDisplayValues()[0];
  if (headings.join('|') !== 'Bus Requested|Driver|Date|Time|Status') {
    throw new Error('Unexpected columns; refusing to publish');
  }
  const map = {
    'Artie 2.0 (RT2)': 'RT2',
    'Archie 2.0 (RX2)': 'RX2',
    'Arthree (R3)': 'R3'
  };
  const rows = sheet.getLastRow() < 2 ? [] :
    sheet.getRange(2, 3, sheet.getLastRow() - 1, 5).getDisplayValues();
  const first = Utilities.formatDate(new Date(), NLBT_ZONE, 'yyyy-MM-dd');
  const last = nlbtAddDay_(first, NLBT_MAX_DAYS);
  const busy = {RT2:{},RX2:{},R3:{}};

  rows.forEach(row => {
    const vehicle = map[String(row[0] || '').trim()];
    const state = String(row[4] || '').trim().toLowerCase();
    if (!vehicle || state !== 'confirmed') return;
    const day = nlbtDate_(String(row[2] || '').trim());
    if (!day) throw new Error('Unparseable confirmed booking date');
    if (day < nlbtAddDay_(first, -1) || day > last) return;
    const match = String(row[3] || '').trim().match(/^(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})$/);
    if (!match) throw new Error('Unparseable confirmed booking time');
    const start = Number(match[1]) * 60 + Number(match[2]);
    const end = Number(match[3]) * 60 + Number(match[4]);
    if (Number(match[1]) > 23 || Number(match[3]) > 23 ||
        Number(match[2]) > 59 || Number(match[4]) > 59 || start === end) {
      throw new Error('Invalid confirmed booking time');
    }
    if (end > start) {
      nlbtAddInterval_(busy[vehicle], day, start, end, first, last);
    } else {
      nlbtAddInterval_(busy[vehicle], day, start, 1440, first, last);
      nlbtAddInterval_(busy[vehicle], nlbtAddDay_(day, 1), 0, end, first, last);
    }
  });

  Object.keys(busy).forEach(vehicle => {
    Object.keys(busy[vehicle]).forEach(day => {
      const ranges = busy[vehicle][day].sort((a,b) => a[0] - b[0]);
      const merged = [];
      ranges.forEach(range => {
        if (merged.length && merged[merged.length - 1][1] >= range[0]) {
          merged[merged.length - 1][1] = Math.max(merged[merged.length - 1][1], range[1]);
        } else {
          merged.push(range.slice());
        }
      });
      busy[vehicle][day] = merged;
    });
  });

  return {
    version:1,
    source:'nlbt-inquiries-confirmed',
    timezone:NLBT_ZONE,
    generated_at:new Date().toISOString(),
    from_date:first,
    through_date:last,
    busy:busy
  };
}

function nlbtAddInterval_(schedule, day, start, end, first, last) {
  if (day < first || day > last || end <= start) return;
  if (!schedule[day]) schedule[day] = [];
  schedule[day].push([start,end]);
}
function nlbtDate_(raw) {
  const match = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!match) return null;
  const month = Number(match[1]), day = Number(match[2]), year = Number(match[3]);
  const utc = new Date(Date.UTC(year, month - 1, day));
  if (utc.getUTCFullYear() !== year || utc.getUTCMonth() !== month - 1 ||
      utc.getUTCDate() !== day) return null;
  return utc.toISOString().slice(0,10);
}
function nlbtAddDay_(iso, offset) {
  const d = new Date(iso + 'T00:00:00Z');
  d.setUTCDate(d.getUTCDate() + offset);
  return d.toISOString().slice(0,10);
}
