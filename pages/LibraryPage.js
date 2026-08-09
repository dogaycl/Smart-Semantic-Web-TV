import { api } from "../services/api.js";
import { ContentCard } from "../components/ContentCard.js";
import { CategoryFilter } from "../components/CategoryFilter.js";

export function LibraryPage(type) {
  const category = type;
  queueMicrotask(async () => {
    let items = await api.getContentByCategory(category);
    const render = () => {
      const sort = document.querySelector("[data-sort]").value;
      const sorted = [...items].sort((a, b) => sort === "title" ? a.title.localeCompare(b.title) : sort === "newest" ? b.year - a.year : b.relevance - a.relevance);
      document.querySelector("#libraryGrid").innerHTML = sorted.map((item) => ContentCard(item, { tall: type === "Movies" })).join("");
    };
    document.querySelectorAll("[data-category]").forEach((button) => {
      button.addEventListener("click", async () => {
        document.querySelectorAll("[data-category]").forEach((chip) => chip.classList.remove("active"));
        button.classList.add("active");
        items = await api.getContentByCategory(button.dataset.category === "All" ? category : button.dataset.category);
        render();
      });
    });
    document.querySelector("[data-sort]").addEventListener("change", render);
    render();
  });

  return `
    <main class="page">
      <span class="eyebrow">Library</span>
      <h1 class="page-title">${type}</h1>
      ${CategoryFilter(category)}
      <section id="libraryGrid" class="content-grid"></section>
    </main>
  `;
}
