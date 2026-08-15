import { api } from "../services/api.js";
import { ContentCard, mediaBackground } from "../components/ContentCard.js";
import { isFavorite, toggleFavorite } from "../services/favoritesService.js";
import { addComment, addHistory, getComments, getRatings, likeComment, rateContent } from "../services/userDataService.js";

export function ContentDetailPage(id) {
  queueMicrotask(async () => {
    const mount = document.querySelector("#detailMount");

    try {
      const item = await api.getContentById(id);
      if (!item) {
        mount.innerHTML = emptyState("Catalog item not found.");
        return;
      }

      mount.innerHTML = detail(item);
      document.querySelector("#related").innerHTML = item.relatedItems.length
        ? item.relatedItems.map((entry) => ContentCard(entry)).join("")
        : `<div class="empty-state">No related titles found.</div>`;

      document.querySelectorAll("[data-detail-tab]").forEach((button) => {
        button.addEventListener("click", () => {
          document.querySelectorAll("[data-detail-tab]").forEach((tab) => tab.classList.remove("active"));
          document.querySelectorAll("[data-detail-panel]").forEach((panel) => panel.classList.remove("active"));
          button.classList.add("active");
          document.querySelector(`[data-detail-panel="${button.dataset.detailTab}"]`)?.classList.add("active");
        });
      });

      document.querySelector("[data-watch-now]")?.addEventListener("click", () => {
        addHistory(item.id, 8);
        document.querySelector("[data-watch-status]").textContent = "Added to watch history. Continue Watching updated.";
      });

      document.querySelector("[data-detail-favorite]")?.addEventListener("click", (event) => {
        event.preventDefault();
        toggleFavorite(item.id);
        event.currentTarget.classList.toggle("active");
      });

      document.querySelectorAll("[data-user-rating]").forEach((button) => {
        button.addEventListener("click", () => {
          rateContent(item.id, button.dataset.userRating);
          document.querySelector("[data-rating-status]").textContent = `You rated this ${button.dataset.userRating}/5.`;
          document.querySelectorAll("[data-user-rating]").forEach((star) => {
            star.classList.toggle("active", Number(star.dataset.userRating) <= Number(button.dataset.userRating));
          });
        });
      });

      const renderComments = () => {
        const comments = getComments(item.id);
        document.querySelector("[data-comments]").innerHTML = comments.length
          ? comments.map((comment, index) => `
              <article class="comment-card ${comment.spoiler ? "spoiler" : ""}">
                <div><strong>${comment.author}</strong><span>${comment.spoiler ? "Spoiler" : "No spoiler"}</span></div>
                <p>${comment.text}</p>
                <button data-like-comment="${index}">Like • ${comment.likes}</button>
              </article>
            `).join("")
          : `<div class="empty-state">No comments yet.</div>`;

        document.querySelectorAll("[data-like-comment]").forEach((button) => {
          button.addEventListener("click", () => {
            likeComment(item.id, Number(button.dataset.likeComment));
            renderComments();
          });
        });
      };

      document.querySelector("[data-comment-form]")?.addEventListener("submit", (event) => {
        event.preventDefault();
        addComment(item.id, {
          author: "You",
          text: document.querySelector("[data-comment-text]").value.trim(),
          spoiler: document.querySelector("[data-comment-spoiler]").checked
        });
        document.querySelector("[data-comment-text]").value = "";
        renderComments();
      });

      renderComments();
    } catch (error) {
      mount.innerHTML = emptyState(error.message || "Content details could not be loaded.");
    }
  });

  return `<main class="page"><div id="detailMount"><div class="empty-state">Loading content details...</div></div><section class="content-row"><div class="section-head"><h2>Similar programs</h2></div><div id="related" class="row-scroll"></div></section></main>`;
}

function emptyState(message) {
  return `<section class="story-shell"><div class="empty-state">${message}</div></section>`;
}

function detail(item) {
  const userRating = getRatings()[item.id] || 0;
  const genres = item.genres.length ? item.genres.join(", ") : item.primaryGenre;
  const trailerMarkup = item.trailer?.embedUrl
    ? `<iframe class="trailer-embed" src="${item.trailer.embedUrl}" title="${item.title} trailer" allow="autoplay; encrypted-media; picture-in-picture" allowfullscreen loading="lazy"></iframe>`
    : `<div class="trailer-frame"><span>▶</span><strong>No official trailer available</strong><small>TMDB did not return an embeddable trailer for this title.</small></div>`;
  const seasonMarkup = item.seasons.length
    ? `<div class="episode-list">${item.seasons.map((season) => `
        <article>
          <strong>${season.name}</strong>
          <span>${season.airDate || "Date unavailable"}</span>
          <small>${season.episodeCount ? `${season.episodeCount} episodes` : "Episode count unavailable"}</small>
        </article>
      `).join("")}</div>`
    : `<div class="empty-state">No season structure is available for this title.</div>`;

  return `
    <section class="detail-hero" style="--hero:${mediaBackground(item, "backdrop")}">
      <div class="detail-poster" style="--poster:${mediaBackground(item, "poster")}">
        ${item.poster ? `<img src="${item.poster}" alt="${item.title} poster" />` : ""}
      </div>
      <div class="detail-copy">
        <span class="eyebrow">${item.category} • ${item.primaryGenre}</span>
        <h1>${item.title}</h1>
        <p class="detail-meta">${[item.year, item.duration, item.language].filter(Boolean).join(" • ")}</p>
        <div class="detail-stats">
          ${item.imdb ? `<span class="imdb-badge large">TMDB ${item.imdb}</span>` : ""}
          ${item.popularityValue != null ? `<span>Popularity ${item.popularityValue}</span>` : ""}
          ${item.status ? `<span>${item.status}</span>` : ""}
        </div>
        <div class="detail-actions">
          <button class="primary-button" data-watch-now>Watch</button>
          <button class="ghost-button ${isFavorite(item.id) ? "active" : ""}" data-detail-favorite>Add to Favorites / My List</button>
        </div>
        <p class="muted" data-watch-status></p>
      </div>
    </section>
    <section class="story-shell">
      <div class="story-tabs" role="tablist" aria-label="Content information">
        <button class="active" data-detail-tab="story">Story</button>
        <button data-detail-tab="trailer">Trailer</button>
        <button data-detail-tab="episodes">Seasons / Episodes</button>
        <button data-detail-tab="cast">Cast & Genre</button>
        <button data-detail-tab="rating">Ratings & Comments</button>
        <button data-detail-tab="ai">AI Insight</button>
      </div>
      <div class="story-panel active" data-detail-panel="story">
        <span class="eyebrow">Storyline</span>
        <h2>About ${item.title}</h2>
        <p>${item.description}</p>
      </div>
      <div class="story-panel" data-detail-panel="cast">
        <span class="eyebrow">Metadata</span>
        <h2>Credits and Details</h2>
        <div class="info-grid">
          <div><span>Category</span><strong>${item.category}</strong></div>
          <div><span>Genres</span><strong>${genres}</strong></div>
          <div><span>Year</span><strong>${item.year || "Unknown"}</strong></div>
          <div><span>Runtime</span><strong>${item.duration}</strong></div>
          <div><span>Language</span><strong>${item.language || "Unknown"}</strong></div>
          <div><span>Status</span><strong>${item.status || "Unknown"}</strong></div>
        </div>
        <div class="credit-list">
          <div>
            <span class="eyebrow">Top cast</span>
            <p>${item.topCast.length ? item.topCast.join(", ") : "Cast data unavailable."}</p>
          </div>
          <div>
            <span class="eyebrow">Top crew</span>
            <p>${item.topCrew.length ? item.topCrew.join(", ") : "Crew data unavailable."}</p>
          </div>
        </div>
        ${item.attribution ? `
          <div class="attribution-card">
            <img src="${item.attribution.logo_url}" alt="TMDB logo" loading="lazy" />
            <div>
              <strong>${item.attribution.source} Attribution</strong>
              <p>${item.attribution.notice}</p>
              <a href="${item.attribution.url}" target="_blank" rel="noreferrer">Open TMDB source page</a>
            </div>
          </div>
        ` : ""}
      </div>
      <div class="story-panel" data-detail-panel="trailer">
        <span class="eyebrow">Official trailer metadata</span>
        <h2>Trailer</h2>
        ${trailerMarkup}
      </div>
      <div class="story-panel" data-detail-panel="episodes">
        <span class="eyebrow">Season system</span>
        <h2>Season and Episode Structure</h2>
        ${seasonMarkup}
      </div>
      <div class="story-panel" data-detail-panel="ai">
        <span class="eyebrow">Future AI Conversational Assistant</span>
        <h2>AI is not connected for this title yet</h2>
        <p>The AI planner and conversational explanation layer will be implemented in a later phase. This page already uses real catalog metadata from TMDB.</p>
        <div class="ai-detail-grid">
          <div><strong>Available today</strong><span>Real title metadata, images, genres, seasons, and trailers.</span></div>
          <div><strong>Planned later</strong><span>Semantic explanation, recommendation reasoning, and viewing planner logic.</span></div>
          <div><strong>Metadata source</strong><span>${item.attribution?.source || "TMDB"}</span></div>
        </div>
      </div>
      <div class="story-panel" data-detail-panel="rating">
        <span class="eyebrow">Community layer</span>
        <h2>Ratings and Comments</h2>
        <div class="rating-control">
          ${[1, 2, 3, 4, 5].map((value) => `<button class="${value <= userRating ? "active" : ""}" data-user-rating="${value}">★</button>`).join("")}
          <span data-rating-status>${userRating ? `You rated this ${userRating}/5.` : "Rate this content."}</span>
        </div>
        <form class="comment-form" data-comment-form>
          <input data-comment-text placeholder="Write a comment..." required />
          <label><input type="checkbox" data-comment-spoiler /> Contains spoilers</label>
          <button class="primary-button">Send</button>
        </form>
        <div class="comments-list" data-comments></div>
      </div>
    </section>
  `;
}
