const navGroups = [
  {
    title: "Watch",
    icon: "▶",
    links: [
      ["/", "Home", "⌂"],
      ["/live-tv", "Live TV", "▶"],
      ["/on-demand", "On Demand", "▥"]
    ]
  },
  {
    title: "AI",
    icon: "AI",
    links: [
      ["/discover", "Smart Search", "⌕"],
      ["/ai", "AI Planner", "✦"],
      { type: "label", text: "Train AI" },
      ["/ai-tuning", "Preference Tuning", "⚙"]
    ]
  },
  {
    title: "Personal",
    icon: "★",
    links: [
      ["/my-list", "My List", "★"],
      ["/history", "Watch History", "◴"],
      ["/social", "Social TV", "☷"]
    ]
  }
];

export function Sidebar(user) {
  const current = location.hash.replace("#", "") || "/";
  const isGroupOpen = (links) => links.some((item) => Array.isArray(item) && current === item[0]);
  const renderNavItem = (item) => {
    if (!Array.isArray(item)) {
      return `<span class="nav-subtitle">${item.text}</span>`;
    }
    const [href, label, icon] = item;
    return `
      <a class="nav-link ${current === href ? "active" : ""}" href="#${href}">
        <b class="nav-icon">${icon}</b><span>${label}</span>
      </a>
    `;
  };
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
        ${navGroups.map((group) => `
          <details class="nav-group" ${isGroupOpen(group.links) ? "open" : ""}>
            <summary><b class="nav-icon">${group.icon}</b><span>${group.title}</span></summary>
            <div class="nav-group-links">
              ${group.links.map(renderNavItem).join("")}
            </div>
          </details>
        `).join("")}
      </nav>
      <div class="sidebar-user">
        <span class="avatar">${user.avatar}</span>
        <div><strong>${user.displayName || user.username}</strong><small>${user.preferredCategories.slice(0, 2).join(", ")}</small></div>
      </div>
    </aside>
  `;
}
