export function SocialPage() {
  queueMicrotask(() => {
    document.querySelector("[data-watch-party-join-form]")?.addEventListener("submit", (event) => {
      event.preventDefault();
      const input = document.querySelector("[data-watch-party-code]");
      const code = input.value.trim().toUpperCase();
      if (!code) return;
      location.hash = `/watch-party/${code}`;
    });
  });

  return `
    <main class="page">
      <span class="eyebrow">Social TV</span>
      <h1 class="page-title">Friends & Shared Lists</h1>
      <section class="social-grid">
        <article class="social-card">
          <h2>Watch Room</h2>
          <p>Watch the same content with friends, chat in sync, and share reactions together.</p>
          <form class="form-stack" data-watch-party-join-form>
            <label class="form-row">
              <span>Join code</span>
              <input class="input" data-watch-party-code maxlength="6" placeholder="AB12CD" />
            </label>
            <button class="primary-button">Join Room</button>
          </form>
        </article>
        <article class="social-card"><h2>Shared Watchlist</h2><p>Build a shared weekend list, such as three movies under two hours.</p><button class="ghost-button">Open List</button></article>
        <article class="social-card"><h2>Recommendations</h2><p>Recommend movies or series to friends, leave spoiler-tagged comments, and like reviews.</p><button class="ghost-button">Recommend</button></article>
      </section>
      <section class="content-row">
        <div class="section-head"><h2>Friends Activity</h2></div>
        <div class="activity-list">
          <div><strong>Ece</strong><span>rated Interstellar five stars.</span></div>
          <div><strong>Mert</strong><span>added Dune: Part Two to the shared list.</span></div>
          <div><strong>Ali</strong><span>posted a spoiler-tagged comment about Black Mirror.</span></div>
        </div>
      </section>
    </main>
  `;
}
