export function ChannelList(channels) {
  return `
    <aside class="panel page-panel">
      <div class="section-head"><h2>Channels</h2><span class="muted">Now / Next</span></div>
      <div class="channel-list">
        ${channels.map((channel) => `
          <article class="channel-row">
            <span class="channel-logo">${channel.logo}</span>
            <div>
              <strong>${channel.name}</strong>
              <div class="channel-meta"><span class="live-badge">Live</span> ${channel.current}</div>
              <small class="muted">Next: ${channel.next} • ${channel.category}</small>
            </div>
          </article>
        `).join("")}
      </div>
    </aside>
  `;
}
