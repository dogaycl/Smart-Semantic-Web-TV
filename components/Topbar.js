import { avatarMarkup } from "../services/avatar.js?v=55";

export function Topbar(user) {
  const current = location.hash.replace("#", "") || "/";
  const active = (paths) => paths.includes(current) ? "active" : "";
  const avatar = avatarMarkup(user || {}, { size: 34 });
  return `
    <header class="topbar vynex-topbar">
      <div class="topbar-main">
        <a class="vynex-logo" href="#/" aria-label="Vynex home">
          <span class="vynex-word">vyne</span><span class="vynex-x">x</span>
        </a>
        <label class="semantic-search">
          <span class="search-icon">⌕</span>
          <input data-global-search aria-label="Semantic search" placeholder="Search movies, channels, AI documentaries..." />
        </label>
        <nav class="top-nav" aria-label="Main navigation">
          <a class="${active(["/live-tv"])}" href="#/live-tv">Live TV</a>
          <a class="${active(["/on-demand", "/movies", "/series"])}" href="#/on-demand">On Demand</a>
          <a class="${active(["/discover"])}" href="#/discover">Discover</a>
          <a class="${active(["/ai", "/my-channel"])}" href="#/my-channel">My Channel</a>
        </nav>
        <div class="toolbar">
          <button class="command-trigger" data-command-open><span>⌘</span> Search</button>
          <a class="profile-chip" href="#/profile" title="Profile settings">${avatar}</a>
          <button class="more-button" data-menu-toggle aria-label="Open account menu" aria-expanded="false">•••</button>
          <div class="account-menu" data-account-menu>
            <small class="menu-section-label">Personal</small>
            <a class="${active(["/profiles"])}" href="#/profiles"><span>◉</span><strong>Profiles</strong></a>
            <a class="${active(["/profile", "/settings"])}" href="#/profile"><span>⚙</span><strong>Profile Settings</strong></a>
            <a class="${active(["/stats"])}" href="#/stats"><span>▧</span><strong>Viewing Stats</strong></a>
            <small class="menu-section-label">System</small>
            <a class="${active(["/admin"])}" href="#/admin"><span>▦</span><strong>Admin Dashboard</strong></a>
            <button data-logout><span>↳</span><strong>Logout</strong></button>
          </div>
        </div>
      </div>
    </header>
  `;
}
