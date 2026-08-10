import { register } from "../contexts/authContext.js";
import { gradient } from "../components/ContentCard.js";

export function RegisterPage() {
  queueMicrotask(() => {
    document.querySelector("#registerForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const errorMount = document.querySelector("#registerError");
      const submitButton = document.querySelector("#registerSubmit");
      errorMount.textContent = "";
      submitButton.disabled = true;

      try {
        await register({
          username: document.querySelector("#username").value.trim(),
          display_name: document.querySelector("#displayName").value.trim() || undefined,
          email: document.querySelector("#email").value.trim(),
          password: document.querySelector("#password").value,
          interests: document.querySelector("#interests").value.split(",").map((item) => item.trim()).filter(Boolean),
          preferred_categories: document.querySelector("#preferredCategories").value.split(",").map((item) => item.trim()).filter(Boolean)
        });
        location.hash = "/";
      } catch (error) {
        errorMount.textContent = error.message || "Registration failed.";
      } finally {
        submitButton.disabled = false;
      }
    });
  });

  return `
    <main class="auth-page" style="--hero:${gradient("#08090d,#18281f,#423313")}">
      <section class="auth-card">
        <div class="brand-line"><span class="vynex-logo compact"><span class="vynex-word">vyne</span><span class="vynex-x">x</span></span><div><strong>Vynex</strong><small>Smart Semantic Web TV</small></div></div>
        <h1>Create profile</h1>
        <p>Create a real account backed by the FastAPI authentication service.</p>
        <form id="registerForm" class="form-stack">
          <label class="form-row"><span>Username</span><input id="username" class="input" autocomplete="username" placeholder="rumeysaaksoy" required /></label>
          <label class="form-row"><span>Display name</span><input id="displayName" class="input" placeholder="Rümeysa Aksoy" /></label>
          <label class="form-row"><span>Email</span><input id="email" class="input" type="email" autocomplete="email" required /></label>
          <label class="form-row"><span>Password</span><input id="password" class="input" type="password" autocomplete="new-password" minlength="8" required /></label>
          <label class="form-row"><span>Interests</span><input id="interests" class="input" placeholder="Artificial Intelligence, Sports, Science" /></label>
          <label class="form-row"><span>Preferred categories</span><input id="preferredCategories" class="input" placeholder="Technology, Documentary" /></label>
          <p id="registerError" class="muted" role="alert"></p>
          <button id="registerSubmit" class="primary-button">Register</button>
        </form>
        <div class="auth-switch">Already have an account? <a href="#/login">Login</a></div>
      </section>
    </main>
  `;
}
