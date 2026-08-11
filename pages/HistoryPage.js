import { content } from "../data/mockData.js";
import { getWatchHistory } from "../services/userDataService.js";

export function HistoryPage() {
  const items = getWatchHistory().map((entry) => ({
    ...entry,
    content: content.find((item) => item.id === entry.contentId)
  })).filter((entry) => entry.content);

  return `
    <main class="page">
      <span class="eyebrow">Viewing history</span>
      <h1 class="page-title">Watch History</h1>
      <section class="history-list">
        ${items.map((entry) => `
          <a class="history-item" href="#/content/${entry.content.id}">
            <img src="${entry.content.poster}" alt="${entry.content.title} poster" />
            <div>
              <h2>${entry.content.title}</h2>
              <p class="muted">${entry.watchedAt} • ${entry.device} • ${entry.content.category}</p>
              <div class="history-progress"><span style="width:${entry.progress}%"></span></div>
            </div>
            <strong>${entry.progress}%</strong>
          </a>
        `).join("")}
      </section>
    </main>
  `;
}
