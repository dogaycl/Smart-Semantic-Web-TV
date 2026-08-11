export function StatsPage() {
  return `
    <main class="page">
      <span class="eyebrow">Taste profile analytics</span>
      <h1 class="page-title">What kind of viewer are you?</h1>
      <section class="stats-hero">
        <div>
          <span class="eyebrow">Viewer type</span>
          <h2>The Explorer</h2>
          <p>You tend to explore science fiction, technology documentaries, and immersive drama titles.</p>
        </div>
        <strong>87%</strong>
      </section>
      <section class="metric-grid stats-grid">
        <article><span>Total watched</span><strong>47</strong><small>programs</small></article>
        <article><span>Watch time</span><strong>82h</strong><small>last 90 days</small></article>
        <article><span>Favorite genre</span><strong>Sci-Fi</strong><small>34% share</small></article>
        <article><span>Average rating</span><strong>4.2</strong><small>out of 5</small></article>
        <article><span>This month</span><strong>13</strong><small>titles</small></article>
        <article><span>Favorite channel</span><strong>Vynex Docs</strong><small>semantic profile</small></article>
      </section>
    </main>
  `;
}
