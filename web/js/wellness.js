/*
  wellness.js
  - Live sensor readings refresh every 5 seconds
  - Today's wellness summary loads once
  - Water intake tracker persists in localStorage
  - Hourly reminder uses browser Notification API
  - Back pain video search + filter
  - Accordion expand/collapse toggle
*/

const DEVICE_ID = 2;
const WATER_GOAL = 8;
const WATER_KEY = "sanzgo_water_" + new Date().toDateString();
let reminderInterval = null;

// ─── Live Reading ────────────────────────────────────────────────────────────

function loadLiveReading() {
  Api.getLatestReading(DEVICE_ID)
    .done(function (data) {
      const r = data.reading;
      $("#liveHr").text(r.heart_rate != null ? Math.round(r.heart_rate) : "--");
      $("#liveSpo2").text(r.spo2 != null ? r.spo2.toFixed(1) + "%" : "--");
      $("#liveTemp").text(r.temperature != null ? r.temperature.toFixed(1) + "°" : "--");
      $("#liveAqi").text(r.aqi != null ? r.aqi : "--");
      $("#liveUpdated").text("Updated " + new Date().toLocaleTimeString());
    })
    .fail(function () {
      $("#liveHr, #liveSpo2, #liveTemp, #liveAqi").text("--");
      $("#livePill").text("Offline").removeClass("ok").addClass("bad");
    });
}

// ─── Today's Summary ─────────────────────────────────────────────────────────

function loadWellnessSummary() {
  Api.getWellnessSummary()
    .done(function (data) {
      const count = data.total_readings;
      $("#readingsCount").text(count === 0 ? "No readings yet today" : count + " readings today");
      const a = data.averages;
      if (!a || Object.keys(a).length === 0) return;
      $("#avgHr").text(a.heart_rate != null ? a.heart_rate.toFixed(1) : "--");
      $("#avgSpo2").text(a.spo2 != null ? a.spo2.toFixed(1) : "--");
      $("#avgTemp").text(a.temperature != null ? a.temperature.toFixed(1) : "--");
      $("#avgAqi").text(a.aqi != null ? a.aqi.toFixed(0) : "--");
      $("#avgHumidity").text(a.humidity != null ? a.humidity.toFixed(1) : "--");
      $("#avgEco2").text(a.eco2 != null ? a.eco2.toFixed(0) : "--");
    })
    .fail(function () {
      $("#readingsCount").text("Could not load summary.");
    });
}

// ─── Water Tracker ───────────────────────────────────────────────────────────

function getWaterCount() {
  return parseInt(localStorage.getItem(WATER_KEY) || "0");
}

function setWaterCount(n) {
  localStorage.setItem(WATER_KEY, Math.max(0, Math.min(n, WATER_GOAL)));
  renderWater();
}

function renderWater() {
  const count = getWaterCount();
  const pct = Math.round((count / WATER_GOAL) * 100);
  $("#waterCount").text(count + " of " + WATER_GOAL + " glasses today");
  $("#waterPill").text(count + " / " + WATER_GOAL);
  $("#waterBar").css("width", pct + "%");
  let html = "";
  for (let i = 0; i < WATER_GOAL; i++) {
    html += '<div class="glass-icon ' + (i < count ? "filled" : "") + '">🥛</div>';
  }
  $("#glassGrid").html(html);
  $("#waterPill").removeClass("ok warn bad neutral")
    .addClass(count >= WATER_GOAL ? "ok" : count >= 4 ? "warn" : "neutral");
}

function logGlass() {
  const count = getWaterCount();
  if (count >= WATER_GOAL) { alert("You've hit your goal today! 🎉"); return; }
  setWaterCount(count + 1);
  if (getWaterCount() === WATER_GOAL) {
    showNotification("SanzGo 💧", "Goal reached! " + WATER_GOAL + " glasses done.");
  }
}

function resetWater() {
  if (confirm("Reset today's water count?")) setWaterCount(0);
}

// ─── Hourly Reminder ─────────────────────────────────────────────────────────

function requestNotificationPermission(cb) {
  if (!("Notification" in window)) { $("#reminderStatus").text("Browser doesn't support notifications."); return; }
  if (Notification.permission === "granted") { cb(); }
  else if (Notification.permission !== "denied") {
    Notification.requestPermission().then(function(p) {
      if (p === "granted") cb();
      else $("#reminderStatus").text("Permission denied — enable in browser settings.");
    });
  } else { $("#reminderStatus").text("Notifications blocked — enable in browser settings."); }
}

function showNotification(title, body) {
  if (Notification.permission === "granted") new Notification(title, { body: body });
}

function startReminder() {
  requestNotificationPermission(function() {
    if (reminderInterval) clearInterval(reminderInterval);
    reminderInterval = setInterval(function() {
      const c = getWaterCount();
      if (c < WATER_GOAL) showNotification("SanzGo 💧", "You've had " + c + " of " + WATER_GOAL + " glasses. Drink up!");
    }, 60 * 60 * 1000);
    $("#reminderStatus").text("Reminders active — every 60 minutes");
    localStorage.setItem("sanzgo_reminder", "on");
  });
}

function stopReminder() {
  if (reminderInterval) clearInterval(reminderInterval);
  reminderInterval = null;
  $("#reminderStatus").text("Reminders off");
  localStorage.removeItem("sanzgo_reminder");
}

// ─── Accordion toggle ────────────────────────────────────────────────────────

function toggleSection(id) {
  const acc = document.getElementById(id);
  const details = acc.querySelectorAll("details");
  const anyOpen = Array.from(details).some(d => d.open);
  details.forEach(d => d.open = !anyOpen);
}

// ─── Back Pain Videos ────────────────────────────────────────────────────────

const backVideos = [
  { title: "NHS: Back stretches", channel: "NHS", tag: "stretches", id: "VDf43fOTH1E", note: "Gentle mobility and stretch routine." },
  { title: "NHS: Back care – Class 1", channel: "NHS", tag: "stretches", id: "E2VEV505574", note: "Low-impact exercises for everyday back care." },
  { title: "McGill Big 3 – Lower Back Pain Exercises", channel: "McGill-style stability", tag: "core", id: "b2F4yMDyy_U", note: "Core stability routine (curl-up, side plank, bird dog)." },
  { title: "Mayo Clinic: Core Strength & Back Pain", channel: "Mayo Clinic Health System", tag: "core", id: "Uo8HIYI6ohs", note: "Why core strength matters and how it supports the spine." },
  { title: "NHS: Exercises for sciatica", channel: "NHS", tag: "sciatica", id: "QNer7Rl2R2Y", note: "Gentle exercises for sciatica-type symptoms." },
  { title: "Mayo Clinic: 4 tips for alleviating back pain", channel: "Mayo Clinic", tag: "tips", id: "N8Z_vX6sZO0", note: "Practical self-care tips for common back pain." },
  { title: "6 Exercises to Relieve Back Pain in 9 Minutes", channel: "Physical Therapist", tag: "stretches", id: "DxIeqiyYZkQ", note: "Follow-along routine for lower back relief." },
  { title: "TEN Best Stretches For Lower Back Pain", channel: "Physical Therapist", tag: "stretches", id: "0wAw1-1MHa4", note: "Stop doing the wrong stretches — correct ones here." }
];

function renderBackVideos(list) {
  const grid = $("#backVideoGrid");
  grid.empty();
  if (!list.length) {
    grid.html('<div class="muted">No videos match your filter. Try different keywords.</div>');
    return;
  }
  list.forEach(function(v) {
    const thumb = "https://img.youtube.com/vi/" + v.id + "/hqdefault.jpg";
    const url = "https://www.youtube.com/watch?v=" + v.id;
    grid.append(
      '<div class="video">' +
        '<img class="video__thumb" src="' + thumb + '" alt="' + v.title + '" loading="lazy">' +
        '<div class="video__body">' +
          '<div class="video__title">' + v.title + '</div>' +
          '<div class="video__meta">' + v.channel + ' · ' + v.tag + '</div>' +
          '<div class="muted" style="font-size:13px;">' + v.note + '</div>' +
          '<div class="video__actions">' +
            '<a class="btn" href="' + url + '" target="_blank" rel="noopener">Watch on YouTube</a>' +
          '</div>' +
        '</div>' +
      '</div>'
    );
  });
}

function applyBackFilters() {
  const q = ($("#backSearch").val() || "").trim().toLowerCase();
  const tag = $("#backTag").val();
  const filtered = backVideos.filter(function(v) {
    const matchTag = tag === "all" || v.tag === tag;
    const matchQ = !q || v.title.toLowerCase().includes(q) || v.note.toLowerCase().includes(q) || v.channel.toLowerCase().includes(q);
    return matchTag && matchQ;
  });
  renderBackVideos(filtered);
}

// ─── Init ────────────────────────────────────────────────────────────────────

$(document).ready(function () {
  loadLiveReading();
  loadWellnessSummary();
  renderWater();
  renderBackVideos(backVideos);

  if (localStorage.getItem("sanzgo_reminder") === "on") startReminder();

  setInterval(loadLiveReading, 5000);
});