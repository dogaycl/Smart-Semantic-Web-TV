import { isFavorite, toggleFavorite } from "../services/favoritesService.js";

export function gradient(colors) {
  return `linear-gradient(135deg, ${colors})`;
}

export function ContentCard(item, options = {}) {
  const tall = options.tall ? " tall" : "";
  queueMicrotask(() => {
    document.querySelectorAll(`[data-fav="${item.id}"]`).forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        toggleFavorite(item.id);
        button.classList.toggle("active");
        button.textContent = button.classList.contains("active") ? "★" : "☆";
      });
    });
  });

  return `
    <a class="content-card" href="#/content/${item.id}">
      <div class="poster${tall}" style="--poster:${gradient(item.color)}">
        <span class="badge">${item.category}</span>
        ${item.relevance ? `<span class="relevance">${item.relevance}%</span>` : ""}
      </div>
      <div class="card-body">
        <h3>${item.title}</h3>
        <div class="card-footer">
          <span class="content-meta">${item.duration} • ${item.year}</span>
          <button class="favorite-button ${isFavorite(item.id) ? "active" : ""}" data-fav="${item.id}" title="Add to My List">${isFavorite(item.id) ? "★" : "☆"}</button>
        </div>
      </div>
    </a>
  `;
}
