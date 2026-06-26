/*
  login.js
  Page-specific logic for index.html (Login screen).
  Handles Google Identity Services sign-in and sends the id_token to our backend.
*/

// If already logged in, skip straight to the dashboard
if (Auth.isLoggedIn()) {
  window.location.href = "dashboard.html";
}

// SanzGo Backend OAuth Web Client ID (Google Cloud Console)
const GOOGLE_CLIENT_ID = "322826306053-717e59d0f20tbag4ckjdgf07so1ccdv9.apps.googleusercontent.com";

window.onload = function () {
  google.accounts.id.initialize({
    client_id: GOOGLE_CLIENT_ID,
    callback: handleGoogleResponse
  });

  google.accounts.id.renderButton(
    document.getElementById("googleSignInButton"),
    { theme: "filled_blue", size: "large", shape: "pill", text: "continue_with", width: 280 }
  );
};

function handleGoogleResponse(response) {
  // response.credential is the Google id_token (a JWT) — send it straight to our backend
  $("#errorMsg").hide();
  $("#loadingMsg").show();

  Api.oauthLogin(response.credential)
    .done(function (data) {
      Auth.saveToken(data.access_token);
      Auth.saveUserId(data.user_id);

      if (data.needs_color_selection) {
        window.location.href = "color-picker.html";
      } else {
        window.location.href = "dashboard.html";
      }
    })
    .fail(function (xhr) {
      $("#loadingMsg").hide();
      const detail = xhr.responseJSON && xhr.responseJSON.detail
        ? xhr.responseJSON.detail
        : "Could not connect to SanzGo server.";
      $("#errorMsg").text(detail).show();
    });
}
