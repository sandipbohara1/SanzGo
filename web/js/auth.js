/*
  auth.js
  Handles JWT storage and login state for the SanzGo web app.
  Uses localStorage instead of MAUI SecureStorage — fine for this stage of the project,
  not production-hardened (a real production app would use httpOnly cookies instead).
*/

const Auth = {
  TOKEN_KEY: "sanzgo_jwt",
  USER_ID_KEY: "sanzgo_user_id",
  DEVICE_ID_KEY: "sanzgo_device_id",

  saveToken: function (token) {
    localStorage.setItem(this.TOKEN_KEY, token);
  },

  getToken: function () {
    return localStorage.getItem(this.TOKEN_KEY);
  },

  saveUserId: function (userId) {
    localStorage.setItem(this.USER_ID_KEY, userId);
  },

  getUserId: function () {
    return localStorage.getItem(this.USER_ID_KEY);
  },

  saveDeviceId: function (deviceId) {
    localStorage.setItem(this.DEVICE_ID_KEY, deviceId);
  },

  getDeviceId: function () {
    return localStorage.getItem(this.DEVICE_ID_KEY);
  },

  isLoggedIn: function () {
    return !!this.getToken();
  },

  logout: function () {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.USER_ID_KEY);
    localStorage.removeItem(this.DEVICE_ID_KEY);
    window.location.href = "index.html";
  },

  // Call at the top of every protected page — bounces back to login if no token
  requireLogin: function () {
    if (!this.isLoggedIn()) {
      window.location.href = "index.html";
    }
  }
};
