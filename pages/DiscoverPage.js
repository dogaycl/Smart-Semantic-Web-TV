import { api } from "../services/api.js?v=31";

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

const moods = [
  ["😄", "Fun", "Recommend fun, fast-paced content that works well with friends."],
  ["😢", "Emotional", "Recommend emotional films or series that are moving but not too heavy."],
  ["😱", "Thrilling", "Recommend tense, dark, and immersive content."],
  ["🧠", "Thoughtful", "Recommend thoughtful sci-fi and technology-focused content."],
  ["🔥", "Action", "Recommend high-energy action movies with strong IMDb scores."]
];

export function DiscoverPage() {
  queueMicrotask(async () => {
    const input = document.querySelector("#semanticInput");
    const resultsMount = document.querySelector("#discoverResults");
    const countMount = document.querySelector("#discoverCount");
    const globalQuery = sessionStorage.getItem("synapse.semantic.query");
    if (globalQuery) input.value = globalQuery;

    const render = async () => {
      resultsMount.innerHTML = `<div class="empty-state">Running semantic search...</div>`;
      try {
        const results = await api.searchSemantic(input.value);
        countMount.textContent = `${results.length} smart matches`;
        resultsMount.innerHTML = results.length ? results.map(compactResult).join("") : `<div class="empty-state">No matching live or on-demand titles were found.</div>`;
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

    document.querySelectorAll("[data-mood-query]").forEach((button) => {
      button.addEventListener("click", () => {
        document.querySelectorAll("[data-mood-query]").forEach((item) => item.classList.remove("active"));
        button.classList.add("active");
        input.value = button.dataset.moodQuery;
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
            ${moods.map(([icon, label, query]) => `
              <button data-mood-query="${query}">
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
          <div id="discoverResults" class="discover-results-grid"></div>
        </section>
      </section>
    </main>
  `;
}
