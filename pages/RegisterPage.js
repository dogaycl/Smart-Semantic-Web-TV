import { register } from "../contexts/authContext.js";
import { gradient } from "../components/ContentCard.js";

export function RegisterPage() {
  queueMicrotask(() => {
    document.querySelector("#registerForm").addEventListener("submit", async (event) => {
      event.preventDefault();
      await register({
        username: document.querySelector("#username").value,
        email: document.querySelector("#email").value,
        interests: document.querySelector("#interests").value.split(",").map((item) => item.trim()).filter(Boolean)
      });
      location.hash = "/";
    });
  });

  return `
    <main class="auth-page" style="--hero:${gradient("#08090d,#18281f,#423313")}">
      <section class="auth-card">
        <div class="brand-line"><span class="vynex-logo compact"><span class="vynex-word">vyne</span><span class="vynex-x">x</span></span><div><strong>Vynex</strong><small>Smart Semantic Web TV</small></div></div>
        <h1>Create profile</h1>
        <p>Mock registration is local for now, but the auth layer is ready for JWT endpoints later.</p>
        <form id="registerForm" class="form-stack">
          <label class="form-row"><span>Username</span><input id="username" class="input" value="Rümeysa Aksoy" required /></label>
          <label class="form-row"><span>Email</span><input id="email" class="input" value="rumeysa@university.edu" type="email" required /></label>
          <label class="form-row"><span>Interests</span><input id="interests" class="input" value="Artificial Intelligence, Sports, Science" /></label>
          <button class="primary-button">Register</button>
        </form>
        <div class="auth-switch">Already have an account? <a href="#/login">Login</a></div>
      </section>
    </main>
  `;
}
