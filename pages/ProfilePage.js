import { getCurrentUser, updateProfile } from "../contexts/authContext.js";
import { PRESET_AVATARS, avatarMarkup } from "../services/avatar.js?v=55";

export function ProfilePage() {
  const user = getCurrentUser();
  const preferredCategories = user.preferredCategories.join(", ");
  const interests = user.interests.join(", ");
  const flashMessage = sessionStorage.getItem("synapse.profile.feedback") || "";
  if (flashMessage) {
    sessionStorage.removeItem("synapse.profile.feedback");
  }

  // Working copy of the avatar reference. A preset click sets "preset:<id>";
  // typing an image URL overrides it. Saved via the profile PATCH.
  const initialAvatar = user.avatarUrl || "";
  const state = { avatar: initialAvatar };

  const renderPreview = () => {
    const mount = document.querySelector("#profileAvatarPreview");
    if (mount) {
      mount.innerHTML = avatarMarkup(
        { avatarUrl: state.avatar, displayName: user.displayName || user.username },
        { size: 110 }
      );
    }
    document.querySelectorAll("[data-preset-id]").forEach((button) => {
      button.classList.toggle("active", state.avatar === `preset:${button.dataset.presetId}`);
    });
  };

  queueMicrotask(() => {
    renderPreview();

    document.querySelectorAll("[data-preset-id]").forEach((button) => {
      button.addEventListener("click", () => {
        state.avatar = `preset:${button.dataset.presetId}`;
        const urlInput = document.querySelector("#profileAvatarUrl");
        if (urlInput) urlInput.value = "";
        renderPreview();
      });
    });

    document.querySelector("#profileAvatarUrl")?.addEventListener("input", (event) => {
      const value = event.target.value.trim();
      if (value) state.avatar = value;
      else state.avatar = "";
      renderPreview();
    });

    document.querySelector("#profileForm")?.addEventListener("submit", async (event) => {
      event.preventDefault();
      const feedback = document.querySelector("#profileFeedback");
      const submitButton = document.querySelector("#profileSubmit");
      feedback.textContent = "";
      submitButton.disabled = true;

      try {
        await updateProfile({
          display_name: document.querySelector("#profileDisplayName").value.trim(),
          avatar_url: state.avatar || null,
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
          <div id="profileAvatarPreview" class="profile-avatar-preview"></div>
          <h2>${user.displayName || user.username}</h2>
          <p class="muted">${user.email}</p>
          <div class="interest-list">${user.preferredCategories.map((item) => `<span class="chip active">${item}</span>`).join("")}</div>
        </div>
        <form id="profileForm" class="profile-panel form-stack">
          <label class="form-row"><span>Username</span><input class="input" value="${user.username}" readonly /></label>
          <label class="form-row"><span>Email</span><input class="input" value="${user.email}" readonly /></label>
          <label class="form-row"><span>Display name</span><input id="profileDisplayName" class="input" value="${user.displayName || user.username}" /></label>
          <div class="form-row">
            <span>Profile picture</span>
            <div class="avatar-picker" role="group" aria-label="Choose a profile picture">
              ${PRESET_AVATARS.map((preset) => `
                <button type="button" class="avatar-picker-option" data-preset-id="${preset.id}" title="${preset.label}" aria-label="${preset.label}">
                  <span class="avatar-media" style="width:44px;height:44px;font-size:16px;background:linear-gradient(135deg, ${preset.colors[0]}, ${preset.colors[1]});">${(user.displayName || user.username || "TV").slice(0, 2).toUpperCase()}</span>
                </button>
              `).join("")}
            </div>
          </div>
          <label class="form-row"><span>Or paste an image URL</span><input id="profileAvatarUrl" class="input" placeholder="https://..." value="${/^https?:\/\//i.test(initialAvatar) ? initialAvatar : ""}" /></label>
          <label class="form-row"><span>Preferred categories</span><input id="profilePreferredCategories" class="input" value="${preferredCategories}" /></label>
          <label class="form-row"><span>Interests for recommendation engine</span><textarea id="profileInterests" class="textarea">${interests}</textarea></label>
          <p id="profileFeedback" class="muted" role="status">${flashMessage}</p>
          <button id="profileSubmit" class="primary-button" type="submit">Save Profile</button>
        </form>
      </section>
    </main>
  `;
}
