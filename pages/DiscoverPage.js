import { api } from "../services/api.js";
import { ContentCard, gradient } from "../components/ContentCard.js";

function resultCard(item) {
  return `
    <article class="result-card">
      <div class="poster" style="--poster:${gradient(item.color)}"><span class="relevance">${item.relevance}%</span></div>
      <div>
        <h3>${item.title}</h3>
        <p>${item.description}</p>
        <p class="content-meta">${item.category} • ${item.duration} • ${item.channel}</p>
        <p class="result-reason">Semantic match: topic meaning, broadcast metadata, and your interests.</p>
        <a class="text-link" href="#/content/${item.id}">Open details</a>
      </div>
    </article>
  `;
}

export function DiscoverPage() {
  queueMicrotask(async () => {
    const input = document.querySelector("#semanticInput");
    const globalQuery = sessionStorage.getItem("synapse.semantic.query");
    if (globalQuery) input.value = globalQuery;
    const render = async () => {
      const results = await api.searchSemantic(input.value);
      document.querySelector("#semanticResults").innerHTML = results.map(resultCard).join("");
      document.querySelector("#semanticSuggestions").innerHTML = results.slice(0, 4).map((item) => ContentCard(item)).join("");
    };
    document.querySelector("#semanticForm").addEventListener("submit", (event) => {
      event.preventDefault();
      render();
    });
    render();
  });

  return `
    <main class="page">
      <section class="discover-hero">
        <span class="eyebrow">AI-powered semantic discovery</span>
        <h1 class="page-title">Search by meaning, not just title.</h1>
        <form id="semanticForm" class="semantic-box">
          <input id="semanticInput" class="input" value="Find technology documentaries about robotics and artificial intelligence." />
          <button class="primary-button">Search</button>
        </form>
      </section>
      <section class="content-row"><div class="section-head"><h2>Semantic Results</h2></div><div id="semanticResults" class="result-grid"></div></section>
      <section class="content-row"><div class="section-head"><h2>Because of your interests</h2></div><div id="semanticSuggestions" class="row-scroll"></div></section>
    </main>
  `;
}
