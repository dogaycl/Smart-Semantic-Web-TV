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

function currentLabel(channel) {
  return channel.current_program?.title || channel.live_title || "No live program metadata";
}

function nextLabel(channel) {
  return channel.next_program?.title || "No upcoming guide data";
}

export function ChannelList(channels, selectedChannelId) {
  return `
    <aside class="panel page-panel">
      <div class="section-head"><h2>Channels</h2><span class="muted">Real live sources</span></div>
      <div class="channel-list">
        ${channels.map((channel) => `
          <button class="channel-row ${channel.id === selectedChannelId ? "selected" : ""}" data-channel-id="${channel.id}" type="button">
            <span class="channel-logo">
              ${channel.logo_url
                ? `<img src="${channel.logo_url}" alt="${channel.name} logo" loading="lazy" referrerpolicy="no-referrer" />`
                : `<span>${channelInitials(channel.name)}</span>`}
            </span>
            <div>
              <strong>${channel.name}</strong>
              <div class="channel-meta">
                <span class="live-badge">${statusLabel(channel)}</span>
                <span class="channel-source">${channel.source_type === "youtube" ? "YouTube" : "HLS"}</span>
                ${currentLabel(channel)}
              </div>
              <small class="muted">Next: ${nextLabel(channel)}${channel.category ? ` • ${channel.category}` : ""}</small>
            </div>
          </button>
        `).join("")}
      </div>
    </aside>
  `;
}
