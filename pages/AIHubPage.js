import { content } from "../data/mockData.js";
import { getActiveProfile, getAiPreferences } from "../services/userDataService.js";

const quickPrompts = [
  "Find a mind-bending movie under two hours.",
  "Build a weekend watchlist for three friends.",
  "Recommend a high IMDb documentary about technology.",
  "Show me something like Dune but shorter.",
  "Pick a cozy series for tonight."
];

export function AIHubPage() {
  const profile = getActiveProfile();
  const prefs = getAiPreferences();
  const topAiPicks = content
    .filter((item) => prefs.contentTypes.includes(item.category))
    .sort((a, b) => Number(b.imdb || 0) - Number(a.imdb || 0))
    .slice(0, 3);

  queueMicrotask(() => {
    const form = document.querySelector("[data-ai-hub-form]");
    const input = document.querySelector("[data-ai-hub-input]");
    form?.addEventListener("submit", (event) => {
      event.preventDefault();
      const query = input.value.trim();
      if (!query) return;
      sessionStorage.setItem("synapse.semantic.query", query);
      location.hash = "/discover";
    });
    document.querySelectorAll("[data-ai-hub-prompt]").forEach((button) => {
      button.addEventListener("click", () => {
        input.value = button.dataset.aiHubPrompt;
        input.focus();
      });
    });
  });

  return `
    <main class="page ai-hub-page">
      <section class="ai-hub-hero">
        <div class="ai-hub-hero-copy">
          <span class="eyebrow">AI-native streaming layer</span>
          <h1>Vynex AI is more than chat. It is the viewing decision engine.</h1>
          <p>Start a natural-language search, tune recommendation behavior, inspect your active AI rules, or jump into AI-powered viewing flows from one place.</p>
          <form class="ai-hub-command" data-ai-hub-form>
            <input data-ai-hub-input placeholder="Ask Vynex for something to watch..." />
            <button class="primary-button">Run Search</button>
          </form>
          <div class="ai-hub-prompts">
            ${quickPrompts.map((prompt) => `<button type="button" data-ai-hub-prompt="${prompt}">${prompt}</button>`).join("")}
          </div>
        </div>
        <aside class="ai-hub-status">
          <span class="eyebrow">Current AI profile</span>
          <h2>${profile}</h2>
          <ul>
            <li>${prefs.useMinImdb ? `IMDb ${prefs.minImdb}+` : "IMDb filter off"}</li>
            <li>${prefs.useMood ? prefs.preferredMood : "Mood filter off"}</li>
            <li>${prefs.useMaxDuration ? `Max ${prefs.maxDurationMinutes} min` : "Runtime filter off"}</li>
          </ul>
          <a class="ghost-button" href="#/ai-tuning">Edit AI Training</a>
        </aside>
      </section>

      <section class="ai-training-callout">
        <div>
          <span class="eyebrow">Train AI</span>
          <h2>Adjust what future recommendations prioritize.</h2>
          <p>Use IMDb quality, popularity, runtime, release year, mood, novelty appetite, content types, spoiler safety, and family-safe rules to shape your personal AI.</p>
        </div>
        <a class="primary-button" href="#/ai-tuning">Open AI Training</a>
      </section>

      <section class="ai-workbench">
        <article class="ai-workbench-card">
          <span class="eyebrow">Suggested by your AI rules</span>
          <h2>Top matches to inspect</h2>
          <div class="ai-pick-list">
            ${topAiPicks.map((item) => `
              <a href="#/content/${item.id}">
                <strong>${item.title}</strong>
                <span>IMDb ${item.imdb || "N/A"} • ${item.category} • ${item.duration}</span>
              </a>
            `).join("")}
          </div>
        </article>
        <article class="ai-workbench-card">
          <span class="eyebrow">What makes it different</span>
          <h2>AI is connected to the product flow</h2>
          <p>The assistant is available globally, Smart Search carries natural-language intent, AI Training changes recommendation rules, and title pages explain why each recommendation appears.</p>
          <div class="planner-filters">
            <span>Global assistant</span>
            <span>Semantic search</span>
            <span>Trainable taste</span>
            <span>Explainable results</span>
          </div>
        </article>
      </section>

      <section class="ai-flow">
        <div class="section-head"><h2>AI Flow</h2></div>
        <div class="flow-steps">
          <div><strong>Profile</strong><span>Interests, age limit, language, and viewing history</span></div>
          <div><strong>Intent</strong><span>Natural-language request and mood selection</span></div>
          <div><strong>Semantic Match</strong><span>Content metadata plus description meaning</span></div>
          <div><strong>Explain</strong><span>Shows the user why each recommendation appears</span></div>
        </div>
      </section>
    </main>
  `;
}
