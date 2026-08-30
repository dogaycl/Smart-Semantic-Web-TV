import { router } from "./router.js?v=32";

router.start().catch((error) => {
  console.error("Router bootstrap failed.", error);
  document.querySelector("#app").innerHTML = `
    <main class="auth-page">
      <section class="auth-card">
        <h1>App failed to start</h1>
        <p>Please make sure the backend is running and reachable.</p>
      </section>
    </main>
  `;
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.getRegistrations()
    .then((registrations) => registrations.forEach((registration) => registration.unregister()))
    .catch(() => {});
}

if ("caches" in window) {
  caches.keys()
    .then((keys) => keys.forEach((key) => caches.delete(key)))
    .catch(() => {});
}
