const timeFormatter = new Intl.DateTimeFormat("en-GB", {
  hour: "2-digit",
  minute: "2-digit"
});

function formatSlot(slot) {
  return timeFormatter.format(new Date(slot));
}

function formatEntryTime(entry) {
  return `${timeFormatter.format(new Date(entry.start_time))} - ${timeFormatter.format(new Date(entry.end_time))}`;
}

function findEntryForSlot(entries, slotStart, slotEnd) {
  return entries.find((entry) => new Date(entry.end_time) > slotStart && new Date(entry.start_time) < slotEnd) || null;
}

export function EPGGuide(epg, selectedChannelId) {
  const slots = epg?.slots || [];
  const channels = epg?.channels || [];
  if (!slots.length || !channels.length) {
    return `
      <section class="epg">
        <div class="section-head"><h2>EPG</h2><span class="muted">No guide data yet</span></div>
      </section>
    `;
  }

  const gridColumns = `180px repeat(${slots.length}, minmax(150px, 1fr))`;
  return `
    <section class="epg">
      <div class="section-head"><h2>EPG</h2><span class="muted">External XMLTV / YouTube schedule</span></div>
      <div class="epg-grid">
        <div class="epg-grid-inner" style="grid-template-columns:${gridColumns}">
          <div class="epg-cell epg-head">Channel</div>
          ${slots.map((slot) => `<div class="epg-cell epg-head">${formatSlot(slot)}</div>`).join("")}
          ${channels.map(({ channel, entries }) => `
            <div class="epg-cell ${channel.id === selectedChannelId ? "epg-channel-active" : ""}">
              <strong>${channel.name}</strong><br><small class="muted">${channel.category || channel.source_type}</small>
            </div>
            ${slots.map((slot, index) => {
              const slotStart = new Date(slot);
              const slotEnd = new Date(slots[index + 1] || epg.end);
              const entry = findEntryForSlot(entries, slotStart, slotEnd);
              if (!entry) {
                return `<div class="epg-cell epg-empty"><strong>No guide</strong><br><span class="epg-time">Unavailable</span></div>`;
              }
              return `<div class="epg-cell ${channel.id === selectedChannelId ? "epg-channel-active" : ""}"><strong>${entry.title}</strong><br><span class="epg-time">${formatEntryTime(entry)}</span></div>`;
            }).join("")}
          `).join("")}
        </div>
      </div>
    </section>
  `;
}
