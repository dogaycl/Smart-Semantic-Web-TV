import { getCurrentUser, updateProfile } from "../contexts/authContext.js";

export function ProfilePage() {
  const user = getCurrentUser();
  const preferredCategories = user.preferredCategories.join(", ");
  const interests = user.interests.join(", ");
  const flashMessage = sessionStorage.getItem("synapse.profile.feedback") || "";
  if (flashMessage) {
    sessionStorage.removeItem("synapse.profile.feedback");
  }

  queueMicrotask(() => {
    document.querySelector("#profileForm")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const feedback = document.querySelector("#profileFeedback");
      const submitButton = document.querySelector("#profileSubmit");
      feedback.textContent = "";
      submitButton.disabled = true;

      try {
        await updateProfile({
          display_name: document.querySelector("#profileDisplayName").value.trim(),
          avatar_url: document.querySelector("#profileAvatarUrl").value.trim() || null,
          preferred_categories: document.querySelector("#profilePreferredCategories").value.split(",").map((item) => item.trim()).filter(Boolean),
          interests: document.querySelector("#profileInterests").value.split(",").map((item) => item.trim()).filter(Boolean)
        });
        sessionStorage.setItem("synapse.profile.feedback", "Profile saved.");
        document.dispatchEvent(new CustomEvent("auth:changed"));
      } catch (error) {
        feedback.textContent = error.message || "Profile update failed.";
      } finally {
        submitButton.disabled = false;
      }
    });
  });

  return `
    <main class="page">
      <span class="eyebrow">Personalization profile</span>
      <h1 class="page-title">Profile & Settings</h1>
      <section class="profile-grid content-row">
        <div class="profile-panel">
          <span class="avatar big-avatar">${user.avatar}</span>
          <h2>${user.displayName || user.username}</h2>
          <p class="muted">${user.email}</p>
          <div class="interest-list">${user.preferredCategories.map((item) => `<span class="chip active">${item}</span>`).join("")}</div>
        </div>
        <form id="profileForm" class="profile-panel form-stack">
          <label class="form-row"><span>Username</span><input class="input" value="${user.username}" readonly /></label>
          <label class="form-row"><span>Email</span><input class="input" value="${user.email}" readonly /></label>
          <label class="form-row"><span>Display name</span><input id="profileDisplayName" class="input" value="${user.displayName || user.username}" /></label>
          <label class="form-row"><span>Avatar URL</span><input id="profileAvatarUrl" class="input" value="${user.avatarUrl || ""}" /></label>
          <label class="form-row"><span>Preferred categories</span><input id="profilePreferredCategories" class="input" value="${preferredCategories}" /></label>
          <label class="form-row"><span>Interests for recommendation engine</span><textarea id="profileInterests" class="textarea">${interests}</textarea></label>
          <p id="profileFeedback" class="muted" role="status">${flashMessage}</p>
          <button id="profileSubmit" class="primary-button" type="submit">Save Profile</button>
        </form>
      </section>
    </main>
  `;
}
