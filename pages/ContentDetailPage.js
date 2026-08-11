import { api } from "../services/api.js";
import { ContentCard, mediaBackground } from "../components/ContentCard.js";
import { isFavorite } from "../services/favoritesService.js";
import { content } from "../data/mockData.js";
import { addComment, addHistory, getComments, getRatings, likeComment, rateContent } from "../services/userDataService.js";

export function ContentDetailPage(id) {
  queueMicrotask(async () => {
    const item = await api.getContentById(id);
    if (!item) return;
    document.querySelector("#detailMount").innerHTML = detail(item);
    document.querySelector("#related").innerHTML = content.filter((entry) => entry.category === item.category && entry.id !== item.id).slice(0, 4).map((entry) => ContentCard(entry)).join("");
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
    document.querySelectorAll("[data-user-rating]").forEach((button) => {
      button.addEventListener("click", () => {
        rateContent(item.id, button.dataset.userRating);
        document.querySelector("[data-rating-status]").textContent = `You rated this ${button.dataset.userRating}/5.`;
        document.querySelectorAll("[data-user-rating]").forEach((star) => star.classList.toggle("active", Number(star.dataset.userRating) <= Number(button.dataset.userRating)));
      });
    });
    const renderComments = () => {
      document.querySelector("[data-comments]").innerHTML = getComments(item.id).map((comment, index) => `
        <article class="comment-card ${comment.spoiler ? "spoiler" : ""}">
          <div><strong>${comment.author}</strong><span>${comment.spoiler ? "Spoiler" : "No spoiler"}</span></div>
          <p>${comment.text}</p>
          <button data-like-comment="${index}">Like • ${comment.likes}</button>
        </article>
      `).join("");
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
  });

  return `<main class="page"><div id="detailMount"></div><section class="content-row"><div class="section-head"><h2>Similar programs</h2></div><div id="related" class="row-scroll"></div></section></main>`;
}

function detail(item) {
  const userRating = getRatings()[item.id] || 0;
  return `
    <section class="detail-hero" style="--hero:${mediaBackground(item, "backdrop")}">
      <div class="detail-poster" style="--poster:${mediaBackground(item, "poster")}">
        ${item.poster ? `<img src="${item.poster}" alt="${item.title} poster" />` : ""}
      </div>
      <div class="detail-copy">
        <span class="eyebrow">${item.category}</span>
        <h1>${item.title}</h1>
        <p class="detail-meta">${item.year} • ${item.duration} • ${item.channel}</p>
        <div class="detail-stats">
          ${item.imdb ? `<span class="imdb-badge large">IMDb ${item.imdb}</span>` : ""}
          ${item.monthlyViews ? `<span>${item.monthlyViews} views this month</span>` : ""}
          ${item.relevance ? `<span>${item.relevance}% match</span>` : ""}
        </div>
        <div class="detail-actions">
          <button class="primary-button" data-watch-now>Watch</button>
          <button class="ghost-button ${isFavorite(item.id) ? "active" : ""}" data-fav="${item.id}">Add to Favorites / My List</button>
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
        <h2>Content Details</h2>
        <div class="info-grid">
          <div><span>Category</span><strong>${item.category}</strong></div>
          <div><span>Channel</span><strong>${item.channel}</strong></div>
          <div><span>Year</span><strong>${item.year}</strong></div>
          <div><span>Runtime</span><strong>${item.duration}</strong></div>
        </div>
      </div>
      <div class="story-panel" data-detail-panel="trailer">
        <span class="eyebrow">Trailer preview</span>
        <h2>Trailer Preview Area</h2>
        <div class="trailer-frame">
          <span>▶</span>
          <strong>${item.title} Trailer</strong>
          <small>Demo player: real video service integration will be connected later.</small>
        </div>
      </div>
      <div class="story-panel" data-detail-panel="episodes">
        <span class="eyebrow">Season system</span>
        <h2>Season and Episode Structure</h2>
        <div class="episode-list">
          <article><strong>S1:E1</strong><span>The Beginning</span><small>48m</small></article>
          <article><strong>S1:E2</strong><span>The Story Deepens</span><small>51m</small></article>
          <article><strong>S1:E3</strong><span>The Turning Point</span><small>46m</small></article>
        </div>
      </div>
      <div class="story-panel" data-detail-panel="ai">
        <span class="eyebrow">Future AI Conversational Assistant</span>
        <h2>Ask AI about this program</h2>
        <p>This title scores highly because it matches ${item.category}, ${item.duration}, IMDb ${item.imdb || "N/A"}, and your profile's science-fiction and technology signals.</p>
        <div class="ai-detail-grid">
          <div><strong>Semantic tags</strong><span>${item.category}, ${item.channel}, ${item.year}</span></div>
          <div><strong>Recommendation reason</strong><span>Similar genre + high IMDb + profile match</span></div>
          <div><strong>Smart prompt</strong><span>“What can I watch that is similar but shorter?”</span></div>
        </div>
        <button class="ghost-button" data-ai-prompt="Explain ${item.title} and recommend similar content.">Ask AI about this program</button>
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
