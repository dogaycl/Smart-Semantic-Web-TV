import { isFavorite, toggleFavorite } from "../services/favoritesService.js";

export function gradient(colors) {
  return `linear-gradient(135deg, ${colors})`;
}

export function mediaBackground(item, key = "poster") {
  const fallback = gradient(item.color || "#171a22,#20242f,#c77a11");
  const image = item[key];
  return image ? `linear-gradient(180deg, rgba(0,0,0,0.02), rgba(0,0,0,0.34)), url("${image}"), ${fallback}` : fallback;
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
      <div class="poster${tall}" style="--poster:${mediaBackground(item, "poster")}">
        ${item.poster ? `<img class="poster-img" src="${item.poster}" alt="${item.title} poster" loading="lazy" />` : ""}
        <div class="poster-topline">
          <span class="badge">${item.category}</span>
          ${item.relevance ? `<span class="relevance">${item.relevance}%</span>` : ""}
        </div>
        <div class="card-overlay">
          <strong>${item.title}</strong>
          <div class="overlay-actions">
            <span class="imdb-badge">IMDb ${item.imdb || "N/A"}</span>
            <span>${item.monthlyViews || "New"}</span>
          </div>
          <span class="overlay-hint">Open details</span>
        </div>
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
