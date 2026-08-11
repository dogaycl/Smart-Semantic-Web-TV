import { mediaBackground } from "./ContentCard.js";
import { isFavorite } from "../services/favoritesService.js";

export function HeroBanner(item) {
  return `
    <section class="hero" style="--hero:${mediaBackground(item, "backdrop")}">
      <div class="hero-copy">
        <div class="hero-trend-note">
          <span>Trending now</span>
          <strong>${item.monthlyViews || "Live"} monthly views</strong>
        </div>
        <span class="eyebrow">${item.category} • ${item.channel}</span>
        <h1>${item.title}</h1>
        <p>${item.description}</p>
        <p class="content-meta">${item.year} • ${item.duration} • 4K Semantic Stream</p>
        <div class="hero-actions">
          <a class="primary-button" href="#/content/${item.id}">Watch Now</a>
          <button class="ghost-button ${isFavorite(item.id) ? "active" : ""}" data-fav="${item.id}">Add to My List</button>
        </div>
      </div>
      ${item.poster ? `<a class="hero-poster-card" href="#/content/${item.id}" aria-label="Open ${item.title}">
        <img src="${item.poster}" alt="${item.title} poster" />
        <div>
          <span class="imdb-badge">IMDb ${item.imdb || "N/A"}</span>
          <strong>Most popular right now</strong>
        </div>
      </a>` : ""}
    </section>
  `;
}
