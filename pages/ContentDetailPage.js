import { api } from "../services/api.js?v=55";
import { ContentCard, mediaBackground } from "../components/ContentCard.js?v=55";
import { isFavorite, toggleFavorite } from "../services/favoritesService.js?v=55";
import { addComment, getComments, getRatings, likeComment, rateContent } from "../services/userDataService.js";
import { startCatalogWatchParty } from "./WatchPartyPage.js";

export function ContentDetailPage(id) {
  queueMicrotask(async () => {
    const mount = document.querySelector("#detailMount");

    try {
      const [item, playback] = await Promise.all([
        api.getContentById(id),
        api.getContentPlayback(id)
      ]);
      if (!item) {
        mount.innerHTML = emptyState("Catalog item not found.");
        return;
      }

      mount.innerHTML = detail(item, playback);
      const assistantContext = mount.querySelector("[data-assistant-context]");
      assistantContext?.setAttribute("data-context-type", "catalog");
      assistantContext?.setAttribute("data-content-slug", item.slug);
      assistantContext?.setAttribute("data-context-label", item.title);
      document.dispatchEvent(new CustomEvent("assistant:context-changed"));
      document.querySelector("#related").innerHTML = item.relatedItems.length
        ? item.relatedItems.map((entry) => ContentCard(entry)).join("")
        : `<div class="empty-state">No related titles found.</div>`;

      const setDetailTab = (tabName) => {
        document.querySelectorAll("[data-detail-tab]").forEach((tab) => {
          tab.classList.toggle("active", tab.dataset.detailTab === tabName);
        });
        document.querySelectorAll("[data-detail-panel]").forEach((panel) => {
          panel.classList.toggle("active", panel.dataset.detailPanel === tabName);
        });
      };

      document.querySelectorAll("[data-detail-tab]").forEach((button) => {
        button.addEventListener("click", () => {
          setDetailTab(button.dataset.detailTab);
        });
      });

      document.querySelector("[data-watch-now]")?.addEventListener("click", () => {
        const statusMount = document.querySelector("[data-watch-status]");
        if (playback.watchAction === "watch_now") {
          location.hash = `/watch/${item.slug}`;
          return;
        }
        if (playback.watchAction === "watch_trailer") {
          setDetailTab("trailer");
          statusMount.textContent = playback.message || "Playing trailer instead because no legal full source is currently configured.";
          return;
        }
        statusMount.textContent = playback.message || "This title is not currently available for in-app playback.";
      });

      document.querySelector("[data-watch-together]")?.addEventListener("click", async () => {
        const button = document.querySelector("[data-watch-together]");
        const statusMount = document.querySelector("[data-watch-status]");
        if (playback.watchAction !== "watch_now") {
          statusMount.textContent = "Only titles with a real playable source can start a watch room.";
          return;
        }
        button.disabled = true;
        statusMount.textContent = "Creating a watch room...";
        try {
          await startCatalogWatchParty(item.slug);
        } catch (error) {
          statusMount.textContent = error.message || "The watch room could not be created.";
          button.disabled = false;
        }
      });

      document.querySelector("[data-detail-favorite]")?.addEventListener("click", async (event) => {
        event.preventDefault();
        const button = event.currentTarget;
        button.disabled = true;
        try {
          const favorites = await toggleFavorite(item.id);
          button.classList.toggle("active", favorites.includes(String(item.id)));
        } catch {
          button.classList.toggle("active", isFavorite(item.id));
        } finally {
          button.disabled = false;
        }
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

function detail(item, playback) {
  const userRating = getRatings()[item.id] || 0;
  const genres = item.genres.length ? item.genres.join(", ") : item.primaryGenre;
  const watchButtonLabel = playback.watchAction === "watch_now"
    ? (playback.watchProgress?.watchPositionSeconds ? "Resume Watching" : "Watch Now")
    : playback.watchAction === "watch_trailer"
      ? "Watch Trailer"
      : "Not Available";
  const watchStatus = playback.watchAction === "watch_now"
    ? (playback.watchProgress?.watchPositionSeconds
      ? `Resume is available at ${Math.floor(playback.watchProgress.watchPositionSeconds / 60)} min. ${playback.message}`
      : playback.message)
    : playback.message;
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
          ${playback.primarySource ? `<span>${playback.primarySource.type.toUpperCase()} via ${playback.primarySource.providerName || "configured source"}</span>` : ""}
        </div>
        <div class="detail-actions">
          <button class="primary-button" data-watch-now>${watchButtonLabel}</button>
          <button class="ghost-button" data-watch-together ${playback.watchAction !== "watch_now" ? "disabled" : ""}>Watch Together</button>
          <button class="ghost-button ${isFavorite(item.id) ? "active" : ""}" data-detail-favorite>Add to Favorites / My List</button>
        </div>
        <p class="muted" data-watch-status>${watchStatus}</p>
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
      <div hidden data-assistant-context></div>
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
        <span class="eyebrow">Grounded content assistant</span>
        <h2>Ask AI about ${item.title}</h2>
        <p>Vynex can now answer from trusted catalog metadata for this title. It will not invent scene-level details when that context is unavailable.</p>
        <div class="ai-detail-grid">
          <div><strong>Available today</strong><span>Real title metadata, credits, genres, season data, and related catalog context.</span></div>
          <div><strong>Grounding rule</strong><span>Answers stay limited to trusted backend context instead of acting like a generic chatbot.</span></div>
          <div><strong>Metadata source</strong><span>${item.attribution?.source || "TMDB"}</span></div>
        </div>
        <div class="ai-suggestions">
          <button data-ai-prompt="What is this title about?">What is this about?</button>
          <button data-ai-prompt="Who are the main cast and crew for this title?">Cast and crew</button>
          <button data-ai-prompt="Why might this title fit my saved interests?">Why it fits me</button>
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
