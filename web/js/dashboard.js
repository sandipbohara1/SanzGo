/*
  dashboard.js
  Fetches the latest sensor reading from the backend every 5 seconds
  and updates the metric grid on the Dashboard screen.
  Uses a hardcoded device ID for now — will read from Auth.getDeviceId() once login is wired up.
*/

// Hardcoded for development — replace with Auth.getDeviceId() once login is working
const DEVICE_ID = 2;

function loadProfile() {
  Api.getProfile()
    .done(function (data) {
      const p = data.profile;
      $("#greetingName").text("Hello, " + p.display_name);
      if (p.city) $("#greetingCity").text(p.city);
    })
    .fail(function () {
      // No profile loaded — silently skip, hardcoded greeting already set in HTML
    });
}

function loadLatestReading() {
  Api.getLatestReading(DEVICE_ID)
    .done(function (data) {
      const r = data.reading;

      // Update connection pill — green dot
      $("#connectionDot").css("background", "var(--teal)");
      $("#connectionLabel").text("Pico Connected");

      // Update main metrics
      $("#heartRate").text(r.heart_rate != null ? Math.round(r.heart_rate) : "--");
      $("#spo2").text(r.spo2 != null ? r.spo2.toFixed(1) : "--");
      $("#temperature").text(r.temperature != null ? r.temperature.toFixed(1) : "--");
      $("#aqi").text(r.aqi != null ? r.aqi : "--");

      // Update secondary metrics
      $("#humidity").text(r.humidity != null ? r.humidity.toFixed(1) : "--");
      $("#eco2").text(r.eco2 != null ? r.eco2 : "--");
      $("#tvoc").text(r.tvoc != null ? r.tvoc : "--");

      // Update last updated timestamp
      if (r.recorded_at) {
        const d = new Date(r.recorded_at);
        $("#lastUpdated").text("Last updated: " + d.toLocaleTimeString());
      }

      // Color-code heart rate if critical/warning
      const hr = r.heart_rate;
      if (hr > 130 || hr < 40) {
        $("#heartRate").css("color", "var(--alert-red)");
      } else if (hr > 100 || hr < 50) {
        $("#heartRate").css("color", "var(--amber)");
      } else {
        $("#heartRate").css("color", "var(--alert-red)"); // default red per spec
      }
    })
    .fail(function () {
      // No data or no device — show disconnected state
      $("#connectionDot").css("background", "var(--amber)");
      $("#connectionLabel").text("No Data Yet");
    });
}

// Load on page ready
$(document).ready(function () {
  loadProfile();
  loadLatestReading();

  // Refresh every 5 seconds
  setInterval(loadLatestReading, 5000);
});