const links = [
  ["/", "Home", "⌂"],
  ["/live-tv", "Live TV", "▶"],
  ["/movies", "Movies", "▣"],
  ["/series", "Series", "▤"],
  ["/discover", "Discover / Search", "AI"],
  ["/my-list", "My List / Favorites", "★"],
  ["/profile", "Profile", "◉"],
  ["/settings", "Settings", "⚙"]
];

export function Sidebar(user) {
  const current = location.hash.replace("#", "") || "/";
  return `
    <aside class="sidebar">
      <div class="sidebar-head">
        <a class="brand-line" href="#/">
          <span class="brand-mark">VX</span>
          <span class="brand-text"><strong>Vynex</strong><small>Semantic Web TV</small></span>
        </a>
        <button class="icon-button" data-sidebar-toggle title="Collapse sidebar">≡</button>
      </div>
      <nav class="nav-list">
        ${links.map(([href, label, icon]) => `
          <a class="nav-link ${current === href ? "active" : ""}" href="#${href}">
            <b class="nav-icon">${icon}</b><span>${label}</span>
          </a>
        `).join("")}
        <button class="nav-link danger-button" data-logout><b class="nav-icon">↳</b><span>Logout</span></button>
      </nav>
      <a class="sidebar-user" href="#/profile">
        <span class="avatar">${user.avatar}</span>
        <div><strong>${user.displayName || user.username}</strong><small>${user.preferredCategories.slice(0, 2).join(", ")}</small></div>
      </a>
    </aside>
  `;
}
