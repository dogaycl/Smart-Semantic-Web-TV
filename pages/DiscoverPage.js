import { api } from "../services/api.js";

function compactResult(item) {
  return `
    <a class="discover-card" href="#/content/${item.id}">
      <img src="${item.poster}" alt="${item.title} poster" loading="lazy" />
      <div class="discover-card-body">
        <div class="discover-card-top">
          <span>${item.category}</span>
          <strong>${item.relevance}% match</strong>
        </div>
        <h3>${item.title}</h3>
        <p>${item.description}</p>
        <div class="discover-meta">
          <span>IMDb ${item.imdb || "N/A"}</span>
          <span>${item.duration}</span>
          <span>${item.year}</span>
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
      const results = await api.searchSemantic(input.value);
      countMount.textContent = `${results.length} smart matches`;
      resultsMount.innerHTML = results.map(compactResult).join("");
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
          <p>Vynex ranks results by combining genre, runtime, IMDb score, mood, and your personal interests.</p>
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
            <p>This is not classic keyword search; it simulates meaning, runtime intent, genres, and user taste together.</p>
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
