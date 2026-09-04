function channelInitials(name = "") {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() || "")
    .join("");
}

function statusLabel(channel) {
  if (channel.live_status === "live") return "Live";
  if (channel.live_status === "upcoming") return "Upcoming";
  if (channel.stream_status === "healthy") return "Playable";
  return "Unavailable";
}

function localeLabel(channel) {
  const parts = [];
  if (channel.language) parts.push(String(channel.language).toUpperCase());
  if (channel.country) parts.push(channel.country);
  return parts.join(" • ") || "Region metadata unavailable";
}

function currentLabel(channel) {
  if (channel.current_program?.title) return channel.current_program.title;
  if (channel.live_title) return channel.live_title;
  if (channel.guide_entries > 0) return "Guide loaded for this channel";
  return "Schedule unavailable";
}

function nextLabel(channel) {
  if (channel.next_program?.title) return channel.next_program.title;
  if (channel.guide_entries > 0) return "No later slot in the current guide window";
  return "Schedule unavailable";
}

export function ChannelList(channels, selectedChannelId) {
  if (!channels.length) {
    return `
      <aside class="panel page-panel channel-panel">
        <div class="section-head"><h2>Channels</h2><span class="muted">Real live sources</span></div>
        <div class="live-fallback">
          <span class="live-badge">Empty</span>
          <strong>No channels matched this filter</strong>
          <small class="muted">Try another category to see the curated English live catalog.</small>
        </div>
      </aside>
    `;
  }

  return `
    <aside class="panel page-panel channel-panel">
      <div class="section-head"><h2>Channels</h2><span class="muted">Real live sources</span></div>
      <div class="channel-list">
        ${channels.map((channel) => `
          <button class="channel-row ${channel.id === selectedChannelId ? "selected" : ""}" data-channel-id="${channel.id}" type="button">
            <span class="channel-logo">
              ${channel.logo_url
                ? `<img src="${channel.logo_url}" alt="${channel.name} logo" loading="lazy" referrerpolicy="no-referrer" onerror="this.hidden=true" />`
                : ""}
              <span class="channel-logo-fallback" aria-hidden="true">${channelInitials(channel.name)}</span>
            </span>
            <div>
              <strong>${channel.name}</strong>
              <div class="channel-meta">
                <span class="live-badge">${statusLabel(channel)}</span>
                <span class="channel-source">${channel.source_type === "youtube" ? "YouTube" : "HLS"}</span>
                ${localeLabel(channel)}
              </div>
              <small class="muted">${currentLabel(channel)}</small>
              <small class="muted">Next: ${nextLabel(channel)}${channel.category ? ` • ${channel.category}` : ""}${channel.guide_entries > 0 ? ` • ${channel.guide_entries} guide items` : " • Schedule unavailable"}</small>
            </div>
          </button>
        `).join("")}
      </div>
    </aside>
  `;
}
