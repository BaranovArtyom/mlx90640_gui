console.log("🔥 notify.js loaded");

const minLimit = 20.0;
const maxLimit = 58.0;
let lastAlert = 0;

document.addEventListener("DOMContentLoaded", () => {
  console.log("📡 DOM loaded, starting temperature checks");

  if (Notification.permission !== "granted") {
    console.log("⚠️ Requesting notification permission...");
    Notification.requestPermission().then(status =>
      console.log("🔔 Permission status:", status)
    );
  }

  setInterval(checkTemp, 5000); // каждые 5 секунд
});

async function checkTemp() {
  console.log("⏱ checkTemp tick");
  try {
    const res = await fetch("/status");
    if (!res.ok) {
      console.warn("⚠️ /status returned:", res.status);
      return;
    }

    const data = await res.json();
    console.log("🌡️ Current:", data.tmin, data.tmax);

    const now = Date.now();
    if (now - lastAlert < 60000) return;

    if (data.tmax > maxLimit) {
      console.log("🚨 Tmax over limit, sending notification...");
      new Notification("⚠️ Перегрев!", {
        body: `Tmax = ${data.tmax.toFixed(1)}°C`,
        icon: "/static/hot.png",
      });
      lastAlert = now;
    } else if (data.tmin < minLimit) {
      console.log("🥶 Tmin under limit, sending notification...");
      new Notification("❄️ Слишком холодно!", {
        body: `Tmin = ${data.tmin.toFixed(1)}°C`,
        icon: "/static/cold.png",
      });
      lastAlert = now;
    }
  } catch (err) {
    console.error("❌ Error in checkTemp:", err);
  }
}
