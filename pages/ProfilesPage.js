import { getActiveProfile, setActiveProfile } from "../services/userDataService.js";

const profiles = [
  { name: "Main", type: "Main", avatar: "MN", language: "English", limit: "18+", tastes: ["Sci-Fi", "Sports", "Drama"] },
  { name: "Family", type: "Shared", avatar: "FM", language: "English", limit: "13+", tastes: ["Comedy", "Documentary", "News"] },
  { name: "Kids", type: "Child", avatar: "KD", language: "English", limit: "7+", tastes: ["Kids", "Animation", "Science"] }
];

export function ProfilesPage() {
  const active = getActiveProfile();
  queueMicrotask(() => {
    document.querySelectorAll("[data-select-profile]").forEach((button) => {
      button.addEventListener("click", () => {
        setActiveProfile(button.dataset.selectProfile);
        location.hash = "/";
      });
    });
  });

  return `
    <main class="page">
      <span class="eyebrow">Multi profile account</span>
      <h1 class="page-title">Who is watching?</h1>
      <section class="profile-switcher">
        ${profiles.map((profile) => `
          <article class="profile-tile ${active === profile.name ? "active" : ""}">
            <span class="avatar big-avatar">${profile.avatar}</span>
            <h2>${profile.name}</h2>
            <p class="muted">${profile.type} profile • ${profile.language} • ${profile.limit}</p>
            <div class="interest-list">${profile.tastes.map((taste) => `<span class="chip">${taste}</span>`).join("")}</div>
            <button class="ghost-button" data-select-profile="${profile.name}">${active === profile.name ? "Active Profile" : "Use Profile"}</button>
          </article>
        `).join("")}
        <article class="profile-tile add-profile">
          <span class="add-mark">+</span>
          <h2>Add Profile</h2>
          <p class="muted">Child mode, language, avatar, age limit, and taste preferences.</p>
        </article>
      </section>
    </main>
  `;
}
