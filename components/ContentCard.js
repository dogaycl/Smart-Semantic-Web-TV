import { isFavorite, toggleFavorite } from "../services/favoritesService.js?v=55";

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
  const href = item.routePath || `#/content/${item.id}`;
  queueMicrotask(() => {
    document.querySelectorAll(`[data-fav="${item.id}"]`).forEach((button) => {
      button.addEventListener("click", async (event) => {
        event.preventDefault();
        event.stopPropagation();
        button.disabled = true;
        try {
          const favorites = await toggleFavorite(item.id);
          const active = favorites.includes(String(item.id));
          button.classList.toggle("active", active);
          button.textContent = active ? "★" : "☆";
        } catch {
          button.classList.toggle("active", isFavorite(item.id));
          button.textContent = isFavorite(item.id) ? "★" : "☆";
        } finally {
          button.disabled = false;
        }
      });
    });
    if (item.liveChannelId) {
      document.querySelectorAll(`[data-live-channel-id="${item.liveChannelId}"]`).forEach((element) => {
        element.addEventListener("click", () => {
          sessionStorage.setItem("synapse.live.channel-id", String(item.liveChannelId));
        });
      });
    }
    // "Full" titles have a real playable source - jump straight into the player instead of
    // making the viewer open the detail page first.
    document.querySelectorAll(`[data-watch-slug="${item.slug || item.id}"]`).forEach((button) => {
      button.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        location.hash = `/watch/${item.slug || item.id}`;
      });
    });
  });

  return `
    <a class="content-card" href="${href}"${item.liveChannelId ? ` data-live-channel-id="${item.liveChannelId}"` : ""}>
      <div class="poster${tall}" style="--poster:${mediaBackground(item, "poster")}">
        ${item.poster ? `<img class="poster-img" src="${item.poster}" alt="${item.title} poster" loading="lazy" />` : ""}
        <div class="poster-topline">
          <span class="badge">${item.category}</span>
          ${item.isPlayable ? `<button type="button" class="relevance playable-badge" data-watch-slug="${item.slug || item.id}" title="Watch now">▶ Watch</button>` : (item.primaryGenre ? `<span class="relevance">${item.primaryGenre}</span>` : "")}
        </div>
        <div class="card-overlay">
          <strong>${item.title}</strong>
          <div class="overlay-actions">
            <span class="imdb-badge">TMDB ${item.imdb || "N/A"}</span>
            <span>${item.popularityValue != null ? `Popularity ${item.popularityValue}` : (item.status || "Catalog")}</span>
          </div>
          <span class="overlay-hint">Open details</span>
        </div>
      </div>
      <div class="card-body">
        <h3>${item.title}</h3>
        ${item.recommendationReason ? `<p class="card-reason">${item.recommendationReason}</p>` : ""}
        <div class="card-footer">
          <span class="content-meta">${item.duration}${item.year ? ` • ${item.year}` : ""}</span>
          ${item.disableFavorite ? "" : `<button class="favorite-button ${isFavorite(item.id) ? "active" : ""}" data-fav="${item.id}" title="Add to My List">${isFavorite(item.id) ? "★" : "☆"}</button>`}
        </div>
      </div>
    </a>
  `;
}
