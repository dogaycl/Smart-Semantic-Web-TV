import { gradient } from "./ContentCard.js";
import { isFavorite } from "../services/favoritesService.js";

export function HeroBanner(item) {
  return `
    <section class="hero" style="--hero:${gradient(item.backdrop)}">
      <div class="hero-copy">
        <span class="eyebrow">${item.category} • ${item.channel}</span>
        <h1>${item.title}</h1>
        <p>${item.description}</p>
        <p class="content-meta">${item.year} • ${item.duration} • 4K Semantic Stream</p>
        <div class="hero-actions">
          <a class="primary-button" href="#/content/${item.id}">Watch Now</a>
          <button class="ghost-button ${isFavorite(item.id) ? "active" : ""}" data-fav="${item.id}">Add to My List</button>
        </div>
      </div>
    </section>
  `;
}
