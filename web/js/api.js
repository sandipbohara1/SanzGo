/*
  api.js
  Every call to the SanzGo FastAPI backend lives here, using jQuery.ajax.
  Mirrors the same endpoints we already tested in Postman.
*/

const Api = {
  // Change this if your backend runs on a different host/port
  baseUrl: "http://127.0.0.1:8000",

  // Builds the Authorization header for authenticated requests
 authHeader: function () {
    // Auth disabled for development — returns empty headers
    // Wire up Auth.getToken() here when login is ready
    return {};
},

  // --- Auth ---
  oauthLogin: function (idToken) {
    return $.ajax({
      url: this.baseUrl + "/auth/oauth",
      method: "POST",
      contentType: "application/json",
      data: JSON.stringify({ id_token: idToken })
    });
  },

  // --- Profile ---
  getProfile: function () {
    return $.ajax({
      url: this.baseUrl + "/profile/me",
      method: "GET",
      headers: this.authHeader()
    });
  },

  setupProfile: function (zoneColor, displayName) {
    return $.ajax({
      url: this.baseUrl + "/profile/setup",
      method: "POST",
      contentType: "application/json",
      headers: this.authHeader(),
      data: JSON.stringify({ zone_color: zoneColor, display_name: displayName })
    });
  },

  updateProfile: function (fields) {
    return $.ajax({
      url: this.baseUrl + "/profile/update",
      method: "PUT",
      contentType: "application/json",
      headers: this.authHeader(),
      data: JSON.stringify(fields)
    });
  },

  // --- Sensor ---
  getLatestReading: function (deviceId) {
    return $.ajax({
      url: this.baseUrl + "/sensor/latest/" + deviceId,
      method: "GET",
      headers: this.authHeader()
    });
  },

  // --- Alerts ---
  getCurrentAlerts: function (deviceId) {
    return $.ajax({
      url: this.baseUrl + "/alerts/current/" + deviceId,
      method: "GET",
      headers: this.authHeader()
    });
  },

  getAlertHistory: function (deviceId) {
    return $.ajax({
      url: this.baseUrl + "/alerts/history/" + deviceId,
      method: "GET",
      headers: this.authHeader()
    });
  },

  // --- Wellness ---
  getWellnessSummary: function () {
    return $.ajax({
      url: this.baseUrl + "/wellness/summary/today",
      method: "GET",
      headers: this.authHeader()
    });
  },

  // --- Territory ---
  getTerritoryTiles: function (lat, lng, radius) {
    radius = radius || 500;
    return $.ajax({
      url: this.baseUrl + "/territory/tiles?lat=" + lat + "&lng=" + lng + "&radius=" + radius,
      method: "GET",
      headers: this.authHeader()
    });
  },

  getLeaderboard: function () {
    return $.ajax({
      url: this.baseUrl + "/territory/leaderboard",
      method: "GET",
      headers: this.authHeader()
    });
  },

  uploadRun: function (runData) {
    return $.ajax({
      url: this.baseUrl + "/territory/run/upload",
      method: "POST",
      contentType: "application/json",
      headers: this.authHeader(),
      data: JSON.stringify(runData)
    });
  },

  // --- Devices ---
  getMyDevices: function () {
    return $.ajax({
      url: this.baseUrl + "/devices/mine",
      method: "GET",
      headers: this.authHeader()
    });
  },

  pairDevice: function (deviceName) {
    return $.ajax({
      url: this.baseUrl + "/devices/pair",
      method: "POST",
      contentType: "application/json",
      headers: this.authHeader(),
      data: JSON.stringify({ device_name: deviceName })
    });
  }
};
