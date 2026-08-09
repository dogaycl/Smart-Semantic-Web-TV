export function EPGGuide(channels, slots, programs) {
  return `
    <section class="epg">
      <div class="epg-grid">
        <div class="epg-cell epg-head">Channel</div>
        ${slots.map((slot) => `<div class="epg-cell epg-head">${slot}</div>`).join("")}
        ${channels.map((channel) => `
          <div class="epg-cell"><strong>${channel.name}</strong><br><small class="muted">${channel.category}</small></div>
          ${programs[channel.name].map((program) => `<div class="epg-cell"><strong>${program}</strong><br><span class="epg-time">Program slot</span></div>`).join("")}
        `).join("")}
      </div>
    </section>
  `;
}
