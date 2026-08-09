import { api } from "../services/api.js";
import { ContentCard, gradient } from "../components/ContentCard.js";
import { isFavorite } from "../services/favoritesService.js";
import { content } from "../data/mockData.js";

export function ContentDetailPage(id) {
  queueMicrotask(async () => {
    const item = await api.getContentById(id);
    if (!item) return;
    document.querySelector("#detailMount").innerHTML = detail(item);
    document.querySelector("#related").innerHTML = content.filter((entry) => entry.category === item.category && entry.id !== item.id).slice(0, 4).map((entry) => ContentCard(entry)).join("");
  });

  return `<main class="page"><div id="detailMount"></div><section class="content-row"><div class="section-head"><h2>Similar programs</h2></div><div id="related" class="row-scroll"></div></section></main>`;
}

function detail(item) {
  return `
    <section class="detail-hero" style="--hero:${gradient(item.backdrop)}">
      <div class="detail-poster" style="--poster:${gradient(item.color)}"></div>
      <div class="detail-copy">
        <span class="eyebrow">${item.category}</span>
        <h1>${item.title}</h1>
        <p class="detail-meta">${item.year} • ${item.duration} • ${item.channel}</p>
        <p>${item.description}</p>
        <div class="detail-actions">
          <button class="primary-button">Watch</button>
          <button class="ghost-button ${isFavorite(item.id) ? "active" : ""}" data-fav="${item.id}">Add to Favorites / My List</button>
        </div>
      </div>
    </section>
    <section class="ai-reserve">
      <span class="eyebrow">Future AI Conversational Assistant</span>
      <h2>Ask AI about this program</h2>
      <p class="muted">Reserved for backend integration: plot summary, similar programs, speakers, actors, directors, and context-aware answers.</p>
      <button class="ghost-button">Ask AI about this program</button>
    </section>
  `;
}
