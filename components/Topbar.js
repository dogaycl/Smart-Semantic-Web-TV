export function Topbar(user) {
  const current = location.hash.replace("#", "") || "/";
  const active = (paths) => paths.includes(current) ? "active" : "";
  return `
    <header class="topbar vynex-topbar">
      <a class="vynex-logo" href="#/" aria-label="Vynex home">
        <span class="vynex-word">vyne</span><span class="vynex-x">x</span>
      </a>
      <label class="semantic-search">
        <span class="search-icon">⌕</span>
        <input data-global-search aria-label="Semantic search" />
      </label>
      <nav class="top-nav" aria-label="Main navigation">
        <a class="${active(["/live-tv"])}" href="#/live-tv">Live TV</a>
        <a class="${active(["/movies", "/series"])}" href="#/movies">On Demand</a>
        <a class="${active(["/discover"])}" href="#/discover">Discover</a>
      </nav>
      <div class="toolbar">
        <a class="media-link ${active(["/my-list"])}" href="#/my-list"><span>▥</span> My Media</a>
        <a class="media-link" href="#/my-list"><span>▰</span> Watchlist</a>
        <a class="signin-pill" href="#/profile">${user.avatar}</a>
        <button class="signin-button" data-logout>Logout</button>
      </div>
    </header>
  `;
}
