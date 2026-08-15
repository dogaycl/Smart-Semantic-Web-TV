import { getWatchHistory } from "../services/userDataService.js";
import { api } from "../services/api.js";

export function HistoryPage() {
  queueMicrotask(async () => {
    const mount = document.querySelector("#historyList");
    if (!mount) return;
    try {
      const history = getWatchHistory();
      const catalogItems = await api.getCatalogBySlugs(history.map((entry) => entry.contentId));
      const bySlug = new Map(catalogItems.map((item) => [item.id, item]));
      const items = history
        .map((entry) => ({
          ...entry,
          content: bySlug.get(entry.contentId)
        }))
        .filter((entry) => entry.content);

      mount.innerHTML = items.length
        ? items.map((entry) => `
            <a class="history-item" href="#/content/${entry.content.id}">
              <img src="${entry.content.poster}" alt="${entry.content.title} poster" />
              <div>
                <h2>${entry.content.title}</h2>
                <p class="muted">${entry.watchedAt} • ${entry.device} • ${entry.content.category}</p>
                <div class="history-progress"><span style="width:${entry.progress}%"></span></div>
              </div>
              <strong>${entry.progress}%</strong>
            </a>
          `).join("")
        : `<div class="empty-state">No watch history yet.</div>`;
    } catch (error) {
      mount.innerHTML = `<div class="empty-state">${error.message || "Watch history could not be loaded."}</div>`;
    }
  });

  return `
    <main class="page">
      <span class="eyebrow">Viewing history</span>
      <h1 class="page-title">Watch History</h1>
      <section class="history-list" id="historyList">
        <div class="empty-state">Loading history...</div>
      </section>
    </main>
  `;
}
