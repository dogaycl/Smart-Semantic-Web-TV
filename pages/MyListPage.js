import { ensureFavoritesLoaded } from "../services/favoritesService.js?v=55";
import { ContentCard } from "../components/ContentCard.js?v=55";
import { api } from "../services/api.js?v=55";

export function MyListPage() {
  queueMicrotask(() => {
    const render = async () => {
      const mount = document.querySelector("#myListGrid");
      if (!mount) return;
      try {
        const favorites = await ensureFavoritesLoaded();
        const items = await api.getCatalogBySlugs(favorites);
        mount.innerHTML = items.length ? items.map((item) => ContentCard(item)).join("") : `<div class="empty-state">Your saved list is empty.</div>`;
      } catch (error) {
        mount.innerHTML = `<div class="empty-state">${error.message || "Favorites could not be loaded."}</div>`;
      }
    };
    const handleFavoritesChanged = () => {
      void render();
    };
    void render();
    document.addEventListener("favorites:changed", handleFavoritesChanged);
    window.addEventListener("hashchange", () => {
      document.removeEventListener("favorites:changed", handleFavoritesChanged);
    }, { once: true });
  });

  return `
    <main class="page">
      <span class="eyebrow">Saved content</span>
      <h1 class="page-title">My List / Favorites</h1>
      <section id="myListGrid" class="content-grid"><div class="empty-state">Loading saved catalog items...</div></section>
    </main>
  `;
}
