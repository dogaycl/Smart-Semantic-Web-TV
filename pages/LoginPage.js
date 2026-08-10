import { login } from "../contexts/authContext.js";
import { gradient } from "../components/ContentCard.js";

export function LoginPage() {
  queueMicrotask(() => {
    document.querySelector("#loginForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      const errorMount = document.querySelector("#loginError");
      const submitButton = document.querySelector("#loginSubmit");
      errorMount.textContent = "";
      submitButton.disabled = true;

      try {
        await login(document.querySelector("#email").value.trim(), document.querySelector("#password").value);
        location.hash = "/";
      } catch (error) {
        errorMount.textContent = error.message || "Login failed.";
      } finally {
        submitButton.disabled = false;
      }
    });
  });

  return `
    <main class="auth-page" style="--hero:${gradient("#08090d,#1b2330,#3a2309")}">
      <section class="auth-card">
        <div class="brand-line"><span class="vynex-logo compact"><span class="vynex-word">vyne</span><span class="vynex-x">x</span></span><div><strong>Vynex</strong><small>Smart Semantic Web TV</small></div></div>
        <h1>Welcome back</h1>
        <p>Continue your personalized live TV, VoD, semantic search, and Social TV experience.</p>
        <form id="loginForm" class="form-stack">
          <label class="form-row"><span>Email</span><input id="email" class="input" type="email" autocomplete="email" required /></label>
          <label class="form-row"><span>Password</span><input id="password" class="input" type="password" autocomplete="current-password" required /></label>
          <p id="loginError" class="muted" role="alert"></p>
          <button id="loginSubmit" class="primary-button">Login</button>
        </form>
        <div class="auth-switch">New here? <a href="#/register">Create an account</a></div>
      </section>
    </main>
  `;
}
