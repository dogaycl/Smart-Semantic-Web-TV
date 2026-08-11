export function AIAssistant() {
  const route = location.hash.replace("#", "") || "/";
  const routeLabel = route.startsWith("/content/") ? "Content Detail" : route === "/discover" ? "Semantic Search" : route === "/live-tv" ? "Live TV" : route === "/on-demand" ? "On Demand" : "Current Page";
  return `
    <aside class="ai-dock" data-ai-dock aria-label="Vynex AI assistant">
      <button class="ai-fab" data-ai-toggle aria-expanded="false">
        <span>AI</span>
        <strong>Ask Vynex</strong>
      </button>
      <section class="ai-panel" data-ai-panel>
        <div class="ai-panel-head">
          <div>
            <span class="eyebrow">Semantic assistant</span>
            <h2>Ask Vynex AI</h2>
            <small class="muted">Context: ${routeLabel}</small>
          </div>
          <button class="icon-button" data-ai-close aria-label="Close AI assistant">×</button>
        </div>
        <div class="ai-context-strip">
          <button data-ai-prompt="Analyze this page and tell me what I should do next.">Analyze page</button>
          <button data-ai-prompt="Create a smart watchlist from my taste profile.">Smart watchlist</button>
          <button data-ai-prompt="Explain why this recommendation fits me.">Why this?</button>
        </div>
        <div class="ai-suggestions">
          <button data-ai-prompt="Show me AI documentaries from this month.">AI documentaries</button>
          <button data-ai-prompt="Find something like Dune but shorter.">Like Dune</button>
          <button data-ai-prompt="What should I watch with friends tonight?">Watch party</button>
        </div>
        <div class="ai-chat">
          <div class="ai-message">I can search by meaning, explain a program, or recommend what to watch next.</div>
        </div>
        <form class="ai-form" data-ai-form>
          <input data-ai-input placeholder="Ask about a movie, series, channel, or topic..." />
          <button class="primary-button">Ask</button>
        </form>
      </section>
    </aside>
  `;
}
