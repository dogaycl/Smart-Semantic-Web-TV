import { api } from "../services/api.js?v=31";

function progressPercent(entry, item) {
  if (!item?.runtimeMinutes) return 0;
  const durationSeconds = item.runtimeMinutes * 60;
  if (!durationSeconds) return 0;
  return Math.max(0, Math.min(100, Math.round((entry.watchPositionSeconds / durationSeconds) * 100)));
}

export function HistoryPage() {
  queueMicrotask(async () => {
    const mount = document.querySelector("#historyList");
    if (!mount) return;
    try {
      const history = await api.getMyWatchHistory();
      const catalogItems = await api.getCatalogBySlugs(
        history
          .filter((entry) => entry.contentType === "content")
          .map((entry) => entry.contentId)
      );
      const bySlug = new Map(catalogItems.map((item) => [item.id, item]));
      const items = history
        .map((entry) => ({
          ...entry,
          content: bySlug.get(entry.contentId),
          progress: progressPercent(entry, bySlug.get(entry.contentId))
        }))
        .filter((entry) => entry.content);

      mount.innerHTML = items.length
        ? items.map((entry) => `
            <a class="history-item" href="#/content/${entry.content.id}">
              <img src="${entry.content.poster}" alt="${entry.content.title} poster" />
              <div>
                <h2>${entry.content.title}</h2>
                <p class="muted">${new Date(entry.lastWatchedAt).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })} • ${entry.content.category}</p>
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
