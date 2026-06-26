/*
  alerts.js
  Fetches current and historical alerts from the backend
  and builds colored alert strips dynamically.
*/

const DEVICE_ID = 2;

function severityClass(severity) {
  if (severity === "critical") return "alert-critical";
  if (severity === "warning") return "alert-warning";
  return "alert-info";
}

function formatTime(isoString) {
  if (!isoString) return "";
  const d = new Date(isoString);
  return d.toLocaleString();
}

function buildStrip(alert, showStatus) {
  const cls = severityClass(alert.severity);
  const status = showStatus
    ? `<div class="time">${alert.resolved_at ? "✓ Resolved" : "● Active"}</div>`
    : "";

  return `
    <div class="alert-strip ${cls}">
      <div class="severity">${alert.severity.toUpperCase()}</div>
      <div class="message">${alert.message}</div>
      <div class="time">${formatTime(alert.created_at)}</div>
      ${status}
    </div>
  `;
}

function loadCurrentAlerts() {
  Api.getCurrentAlerts(DEVICE_ID)
    .done(function (data) {
      const container = $("#currentAlerts");
      container.empty();

      if (data.alerts.length === 0) {
        container.html('<div class="no-alerts">No active alerts. You\'re all good! 👍</div>');
        return;
      }

      data.alerts.forEach(function (alert) {
        container.append(buildStrip(alert, false));
      });
    })
    .fail(function () {
      $("#currentAlerts").html('<div class="muted">Could not load alerts.</div>');
    });
}

function loadAlertHistory() {
  Api.getAlertHistory(DEVICE_ID)
    .done(function (data) {
      const container = $("#historyAlerts");
      container.empty();

      if (data.alerts.length === 0) {
        container.html('<div class="no-alerts">No alert history yet.</div>');
        return;
      }

      data.alerts.forEach(function (alert) {
        container.append(buildStrip(alert, true));
      });
    })
    .fail(function () {
      $("#historyAlerts").html('<div class="muted">Could not load history.</div>');
    });
}

$(document).ready(function () {
  loadCurrentAlerts();
  loadAlertHistory();
});