import { getCurrentUser } from "../contexts/authContext.js";

export function ProfilePage() {
  const user = getCurrentUser();
  return `
    <main class="page">
      <span class="eyebrow">Personalization profile</span>
      <h1 class="page-title">Profile & Settings</h1>
      <section class="profile-grid content-row">
        <div class="profile-panel">
          <span class="avatar big-avatar">${user.avatar}</span>
          <h2>${user.username}</h2>
          <p class="muted">${user.email}</p>
          <div class="interest-list">${user.preferredCategories.map((item) => `<span class="chip active">${item}</span>`).join("")}</div>
        </div>
        <form class="profile-panel form-stack">
          <label class="form-row"><span>Username</span><input class="input" value="${user.username}" /></label>
          <label class="form-row"><span>Email</span><input class="input" value="${user.email}" /></label>
          <label class="form-row"><span>Preferred categories</span><input class="input" value="${user.preferredCategories.join(", ")}" /></label>
          <label class="form-row"><span>Interests for recommendation engine</span><textarea class="textarea">${user.interests.join(", ")}</textarea></label>
          <button class="primary-button" type="button">Save Mock Profile</button>
        </form>
      </section>
    </main>
  `;
}
