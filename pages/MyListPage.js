import { content } from "../data/mockData.js";
import { getFavorites } from "../services/favoritesService.js";
import { ContentCard } from "../components/ContentCard.js";

export function MyListPage() {
  const render = () => {
    const items = content.filter((item) => getFavorites().includes(item.id));
    const mount = document.querySelector("#myListGrid");
    if (!mount) return;
    mount.innerHTML = items.length ? items.map((item) => ContentCard(item)).join("") : `<div class="empty-state">Your saved list is empty.</div>`;
  };
  queueMicrotask(() => {
    render();
    document.addEventListener("favorites:changed", render, { once: true });
  });

  return `
    <main class="page">
      <span class="eyebrow">Saved content</span>
      <h1 class="page-title">My List / Favorites</h1>
      <section id="myListGrid" class="content-grid"></section>
    </main>
  `;
}
