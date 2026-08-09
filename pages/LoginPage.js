import { login } from "../contexts/authContext.js";
import { gradient } from "../components/ContentCard.js";

export function LoginPage() {
  queueMicrotask(() => {
    document.querySelector("#loginForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      await login(document.querySelector("#email").value, document.querySelector("#password").value);
      location.hash = "/";
    });
  });

  return `
    <main class="auth-page" style="--hero:${gradient("#08090d,#1b2330,#3a2309")}">
      <section class="auth-card">
        <div class="brand-line"><span class="vynex-logo compact"><span class="vynex-word">vyne</span><span class="vynex-x">x</span></span><div><strong>Vynex</strong><small>Smart Semantic Web TV</small></div></div>
        <h1>Welcome back</h1>
        <p>Continue your personalized live TV, VoD, semantic search, and Social TV experience.</p>
        <form id="loginForm" class="form-stack">
          <label class="form-row"><span>Email</span><input id="email" class="input" value="rumeysa@university.edu" type="email" required /></label>
          <label class="form-row"><span>Password</span><input id="password" class="input" value="demo1234" type="password" required /></label>
          <button class="primary-button">Login</button>
        </form>
        <div class="auth-switch">New here? <a href="#/register">Create an account</a></div>
      </section>
    </main>
  `;
}
