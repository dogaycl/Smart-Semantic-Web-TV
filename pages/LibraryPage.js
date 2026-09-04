import { api } from "../services/api.js?v=55";
import { ContentCard } from "../components/ContentCard.js";
import { CategoryFilter } from "../components/CategoryFilter.js";

export function LibraryPage(type) {
  queueMicrotask(async () => {
    let activeCategory = "All";
    let activeSearch = "";

    const grid = document.querySelector("#libraryGrid");
    const sortSelect = document.querySelector("[data-sort]");
    const searchInput = document.querySelector("[data-title-search]");

    const render = async () => {
      grid.innerHTML = `<div class="empty-state">Loading real catalog...</div>`;
      try {
        const sort = sortSelect.value;
        const response = await api.getCatalog({
          contentType: type === "Movies" ? "movie" : "tv",
          category: activeCategory === "All" ? null : activeCategory,
          search: activeSearch || null,
          sort: sort === "newest" ? "release_date_desc" : sort === "title" ? "title_asc" : sort,
          limit: 300
        });
        grid.innerHTML = response.items.length
          ? response.items.map((item) => ContentCard(item, { tall: type === "Movies" })).join("")
          : `<div class="empty-state">No titles matched this filter.</div>`;
      } catch (error) {
        grid.innerHTML = `<div class="empty-state">${error.message || "Catalog could not be loaded."}</div>`;
      }
    };

    document.querySelectorAll("[data-category]").forEach((button) => {
      button.addEventListener("click", () => {
        document.querySelectorAll("[data-category]").forEach((chip) => chip.classList.remove("active"));
        button.classList.add("active");
        activeCategory = button.dataset.category;
        render();
      });
    });

    let searchTimer = null;
    searchInput?.addEventListener("input", () => {
      window.clearTimeout(searchTimer);
      searchTimer = window.setTimeout(() => {
        activeSearch = searchInput.value.trim();
        render();
      }, 180);
    });

    sortSelect.addEventListener("change", render);
    render();
  });

  return `
    <main class="page">
      <span class="eyebrow">Library</span>
      <h1 class="page-title">${type}</h1>
      ${CategoryFilter(type)}
      <section id="libraryGrid" class="content-grid"></section>
    </main>
  `;
}
