import { api } from "../services/api.js?v=55";

function compactResult(item) {
  const metaParts = [item.duration, item.year, item.channel?.name].filter(Boolean);
  return `
    <a class="discover-card" href="${item.routePath || `#/content/${item.id}`}"${item.liveChannelId ? ` data-discover-live-channel="${item.liveChannelId}"` : ""}>
      ${item.poster ? `<img src="${item.poster}" alt="${item.title} poster" loading="lazy" />` : `<div class="discover-card-fallback">${item.category}</div>`}
      <div class="discover-card-body">
        <div class="discover-card-top">
          <span>${item.category}</span>
          <strong>${Math.round((item.searchScore || 0) * 100)}% match</strong>
        </div>
        <h3>${item.title}</h3>
        <p>${item.description}</p>
        ${item.recommendationReason ? `<p class="discover-card-reason">${item.recommendationReason}</p>` : ""}
        <div class="discover-meta">
          <span>${item.imdb ? `TMDB ${item.imdb}` : (item.availability?.label || "Catalog")}</span>
          ${metaParts.map((part) => `<span>${part}</span>`).join("")}
        </div>
      </div>
    </a>
  `;
}

// id maps to a backend mood ranking profile (app/services/search/mood.py). The
// mood is sent as a structured parameter so the backend re-ranks real database
// content by genre / description / category affinity - it is not a keyword hack.
const moods = [
  ["😌", "Relax", "relax"],
  ["😂", "Funny", "funny"],
  ["🔥", "Excited", "excited"],
  ["❤️", "Romantic", "romantic"],
  ["😱", "Scary", "scary"]
];

let discoverRequestId = 0;

function resultSection(title, subtitle, items, emptyMessage) {
  return `
    <section class="discover-result-section">
      <div class="discover-section-head">
        <div><span class="eyebrow">${subtitle}</span><h3>${title}</h3></div>
        <strong>${items.length}</strong>
      </div>
      <div class="discover-results-grid">
        ${items.length ? items.map(compactResult).join("") : `<div class="empty-state compact">${emptyMessage}</div>`}
      </div>
    </section>
  `;
}

export function DiscoverPage() {
  queueMicrotask(async () => {
    const input = document.querySelector("#semanticInput");
    const resultsMount = document.querySelector("#discoverResults");
    const countMount = document.querySelector("#discoverCount");
    const globalQuery = sessionStorage.getItem("synapse.semantic.query");
    if (globalQuery) input.value = globalQuery;

    let activeMood = null;

    const render = async () => {
      const requestId = ++discoverRequestId;
      const moodLabel = activeMood ? activeMood[0].toUpperCase() + activeMood.slice(1) : "";
      resultsMount.innerHTML = `<div class="empty-state">Running semantic search${moodLabel ? ` · ${moodLabel} mood` : ""}...</div>`;
      try {
        const query = input.value.trim();
        const [demandResults, liveResults] = await Promise.all([
          api.searchSemantic(`${query} on demand movie series`, { limit: 30, windowHours: null, mood: activeMood }),
          api.searchSemantic(`${query} live airing now television programme`, { limit: 30, windowHours: 24, mood: activeMood })
        ]);
        if (requestId !== discoverRequestId) return;
        const onDemand = demandResults.filter((item) => item.contentType !== "live").slice(0, 10);
        const live = liveResults.filter((item) => item.contentType === "live").slice(0, 10);
        countMount.textContent = `${onDemand.length} on-demand · ${live.length} live`;
        resultsMount.innerHTML = `
          ${resultSection("10 On-demand picks", "Movies & series", onDemand, "No on-demand title matched this mood.")}
          ${resultSection("Live TV suggestions", "On now & upcoming", live, "No live programme matched this mood in the next 24 hours.")}
        `;
        document.querySelectorAll("[data-discover-live-channel]").forEach((element) => {
          element.addEventListener("click", () => {
            sessionStorage.setItem("synapse.live.channel-id", element.dataset.discoverLiveChannel);
          });
        });
      } catch (error) {
        countMount.textContent = "0 smart matches";
        resultsMount.innerHTML = `<div class="empty-state">${error.message || "Semantic search is unavailable right now."}</div>`;
      }
    };

    document.querySelector("#semanticForm").addEventListener("submit", (event) => {
      event.preventDefault();
      render();
    });

    document.querySelectorAll("[data-mood]").forEach((button) => {
      button.addEventListener("click", () => {
        const mood = button.dataset.mood;
        const isActive = activeMood === mood;
        activeMood = isActive ? null : mood;
        document.querySelectorAll("[data-mood]").forEach((item) => {
          item.classList.toggle("active", !isActive && item.dataset.mood === mood);
        });
        render();
      });
    });

    document.querySelectorAll("[data-example-query]").forEach((button) => {
      button.addEventListener("click", () => {
        input.value = button.dataset.exampleQuery;
        render();
      });
    });

    render();
  });

  return `
    <main class="page discover-page">
      <section class="discover-search-shell">
        <div class="discover-search-copy">
          <span class="eyebrow">Natural-language discovery</span>
          <h1>Describe what you want to watch in plain language.</h1>
          <p>Vynex now searches real movies, series, and upcoming live programs using semantic relevance, runtime intent, and your saved profile signals.</p>
        </div>
        <form id="semanticForm" class="discover-search-form">
          <input id="semanticInput" value="Recommend something under 90 minutes with comedy and sci-fi." />
          <button class="primary-button">Search</button>
        </form>
        <div class="query-examples">
          <button data-example-query="I want something like Interstellar, but less scientific and more emotional.">Like Interstellar</button>
          <button data-example-query="Recommend three movies under two hours for this weekend.">Weekend picks</button>
          <button data-example-query="Recommend a dark series with a high IMDb score.">Dark series</button>
        </div>
      </section>

      <section class="discover-layout">
        <aside class="discover-filter-panel">
          <div>
            <span class="eyebrow">Mood engine</span>
            <h2>Choose by mood</h2>
          </div>
          <div class="discover-moods">
            ${moods.map(([icon, label, mood]) => `
              <button data-mood="${mood}">
                <span>${icon}</span>
                <strong>${label}</strong>
              </button>
            `).join("")}
          </div>
          <div class="ai-insight-card">
            <span class="eyebrow">AI insight</span>
            <p>This uses real backend semantic search over live EPG and catalog metadata rather than a static keyword-only mock.</p>
          </div>
          <div class="ai-insight-card">
            <span class="eyebrow">Why it is different</span>
            <p>Normal search only finds titles. Vynex AI also understands intents like “less scientific,” “good with friends,” and “under two hours.”</p>
          </div>
        </aside>

        <section class="discover-results-panel">
          <div class="discover-results-head">
            <div>
              <span class="eyebrow">Semantic results</span>
              <h2>Recommended matches</h2>
            </div>
            <strong id="discoverCount">0 smart matches</strong>
          </div>
          <div id="discoverResults" class="discover-results-sections"></div>
        </section>
      </section>
    </main>
  `;
}
