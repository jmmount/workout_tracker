/**
 * Health Log writer for the Workout Guide app.
 *
 * Paste into the Health Log spreadsheet's own Apps Script project
 * (Extensions -> Apps Script), then Deploy -> New deployment -> Web app:
 * execute as Me, access "Anyone with the link". Put the web app URL in
 * the app's backend/.env as SHEETS_ENDPOINT. The URL is the only secret;
 * anyone with it can append workout rows to this sheet.
 *
 * The app POSTs {"rows": [[...15 columns...], ...]} as text/plain;
 * rows are appended to the Workouts tab in order.
 */
function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    var rows = body.rows || [];
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName('Workouts');
    rows.forEach(function (r) { sheet.appendRow(r); });
    return ContentService
      .createTextOutput(JSON.stringify({ ok: true, rows: rows.length }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService
      .createTextOutput(JSON.stringify({ ok: false, error: String(err) }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet() {
  return ContentService
    .createTextOutput(JSON.stringify({ ok: true, service: 'health-log-writer' }))
    .setMimeType(ContentService.MimeType.JSON);
}
