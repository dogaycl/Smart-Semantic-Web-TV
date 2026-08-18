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
            <span class="eyebrow">Context-aware assistant</span>
            <h2>Ask Vynex AI</h2>
            <small class="muted">Context: <span data-ai-context-label>${routeLabel}</span></small>
          </div>
          <button class="icon-button" data-ai-close aria-label="Close AI assistant">×</button>
        </div>
        <div class="ai-context-strip">
          <button data-ai-prompt="What is this title or program about?">What is this about?</button>
          <button data-ai-prompt="Why might this fit my saved interests?">Why this for me?</button>
          <button data-ai-prompt="Summarize this using only trusted metadata.">Trusted summary</button>
        </div>
        <div class="ai-suggestions">
          <button data-ai-prompt="Who are the main cast, crew, or known contributors here?">Cast or contributors</button>
          <button data-ai-prompt="What is the next program or closest related title?">What is next?</button>
          <button data-ai-prompt="What can you confirm about this content without inventing details?">Stay grounded</button>
        </div>
        <div class="ai-chat">
          <div class="ai-message">I answer from trusted catalog, EPG, and channel metadata for the content you are currently viewing.</div>
        </div>
        <form class="ai-form" data-ai-form>
          <input data-ai-input placeholder="Ask about the current movie, series, or live program..." />
          <button class="primary-button">Ask</button>
        </form>
      </section>
    </aside>
  `;
}
