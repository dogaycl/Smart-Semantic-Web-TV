export function AdminPage() {
  queueMicrotask(() => {
    document.querySelector("[data-admin-form]")?.addEventListener("submit", (event) => {
      event.preventDefault();
      document.querySelector("[data-admin-feedback]").textContent = "Demo content queued for backend CRUD endpoint.";
      event.currentTarget.reset();
    });
  });

  return `
    <main class="page">
      <span class="eyebrow">Administrative dashboard</span>
      <h1 class="page-title">Content Control Center</h1>
      <section class="admin-grid">
        <article><h2>Content Management</h2><p>Add, remove, and edit movies or series with poster and trailer fields.</p><button class="primary-button">Add Content</button></article>
        <article><h2>Season & Episodes</h2><p>Create seasons, add episodes, and manage runtime and release dates.</p><button class="ghost-button">Manage Episodes</button></article>
        <article><h2>Categories</h2><p>Manage genres, categories, age limits, and child-profile compatibility.</p><button class="ghost-button">Edit Categories</button></article>
        <article><h2>Users & Comments</h2><p>Manage user roles, comment moderation, spoiler labels, and likes.</p><button class="ghost-button">Moderate</button></article>
      </section>
      <section class="admin-workbench">
        <form data-admin-form class="admin-form">
          <span class="eyebrow">CRUD demo</span>
          <h2>Add / Edit Content</h2>
          <input class="input" placeholder="Title" required />
          <select class="select"><option>Movies</option><option>Series</option><option>Documentaries</option><option>Sports</option></select>
          <input class="input" placeholder="Poster URL" />
          <textarea class="textarea" placeholder="Description"></textarea>
          <button class="primary-button">Save Content</button>
          <p class="muted" data-admin-feedback></p>
        </form>
        <div class="admin-table">
          <span class="eyebrow">User management</span>
          <h2>Users</h2>
          <div><strong>Admin User</strong><span>Admin</span><button>Manage</button></div>
          <div><strong>Ece</strong><span>User</span><button>Manage</button></div>
          <div><strong>Kids</strong><span>Child profile</span><button>Restrict</button></div>
        </div>
        <div class="admin-table">
          <span class="eyebrow">Comment moderation</span>
          <h2>Queue</h2>
          <div><strong>Spoiler comment</strong><span>Pending</span><button>Approve</button></div>
          <div><strong>Reported review</strong><span>Flagged</span><button>Hide</button></div>
        </div>
      </section>
      <section class="content-row">
        <div class="section-head"><h2>Platform Metrics</h2></div>
        <div class="metric-grid stats-grid">
          <article><span>Active users</span><strong>128K</strong><small>+18.4%</small></article>
          <article><span>Content library</span><strong>41K</strong><small>VoD + live</small></article>
          <article><span>Most watched</span><strong>Dune</strong><small>18.4M</small></article>
          <article><span>Pending comments</span><strong>246</strong><small>moderation queue</small></article>
        </div>
      </section>
    </main>
  `;
}
