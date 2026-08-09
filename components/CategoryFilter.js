import { categories } from "../data/mockData.js";

export function CategoryFilter(active = "All") {
  return `
    <div class="filter-bar">
      ${categories.map((category) => `<button class="chip ${category === active ? "active" : ""}" data-category="${category}">${category}</button>`).join("")}
      <select class="select" data-sort>
        <option value="recommended">Sort: Recommended</option>
        <option value="newest">Sort: Newest</option>
        <option value="title">Sort: Title</option>
      </select>
    </div>
  `;
}
