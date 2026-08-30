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

function isEntryLiveNow(entry, now) {
  return new Date(entry.start_time) <= now && now < new Date(entry.end_time);
}

function nextEntryAfterNow(entries, now, liveEntry) {
  return entries
    .filter((entry) => entry !== liveEntry && new Date(entry.start_time) >= now)
    .sort((a, b) => new Date(a.start_time) - new Date(b.start_time))[0] || null;
}

function acceptedPlanKeys(activePlan) {
  if (!activePlan?.isAccepted) return new Set();
  return new Set(
    (activePlan.items || [])
      .filter((item) => item.resultType === "live_program")
      .map((item) => item.epgEntryId || item.candidateId)
      .filter(Boolean)
  );
}

function entryPlanKey(entry) {
  return entry.id || `epg:${entry.channel_id}:${entry.source}:${entry.external_id}`;
}

export function EPGGuide(epg, selectedChannelId, activePlan = null) {
  const slots = epg?.slots || [];
  const channels = epg?.channels || [];
  if (!slots.length || !channels.length) {
    return `
      <section class="epg">
        <div class="section-head"><h2>EPG</h2><span class="muted">No real schedule data is available for this selection yet</span></div>
      </section>
    `;
  }

  const now = new Date();
  const nowSlotIndex = slots.findIndex((slot, index) => {
    const slotStart = new Date(slot);
    const slotEnd = new Date(slots[index + 1] || epg.end);
    return now >= slotStart && now < slotEnd;
  });
  const plannedEntryKeys = acceptedPlanKeys(activePlan);

  const gridColumns = `180px repeat(${slots.length}, minmax(150px, 1fr))`;
  return `
    <section class="epg">
      <div class="section-head"><h2>EPG</h2><span class="muted">External XMLTV / YouTube schedule${nowSlotIndex >= 0 ? " &middot; NOW column highlighted" : ""}${plannedEntryKeys.size ? " &middot; My Channel highlighted" : ""}</span></div>
      <div class="epg-grid">
        <div class="epg-grid-inner" style="grid-template-columns:${gridColumns}">
          <div class="epg-cell epg-head">Channel</div>
          ${slots.map((slot, index) => `
            <div class="epg-cell epg-head ${index === nowSlotIndex ? "epg-now-column" : ""}">
              ${index === nowSlotIndex ? '<span class="epg-now-tag">NOW</span><br>' : ""}${formatSlot(slot)}
            </div>
          `).join("")}
          ${channels.map(({ channel, entries }) => {
            const liveEntry = entries.find((entry) => isEntryLiveNow(entry, now)) || null;
            const nextEntry = nextEntryAfterNow(entries, now, liveEntry);
            const channelHasPlan = entries.some((entry) => plannedEntryKeys.has(entryPlanKey(entry)));
            return `
              <div class="epg-cell ${channel.id === selectedChannelId ? "epg-channel-active" : ""} ${channelHasPlan ? "epg-channel-planned" : ""}">
                <strong>${channel.name}</strong><br><small class="muted">${[channel.category || channel.source_type, channel.language ? String(channel.language).toUpperCase() : null, channel.country].filter(Boolean).join(" • ")}</small>
              </div>
              ${slots.map((slot, index) => {
                const slotStart = new Date(slot);
                const slotEnd = new Date(slots[index + 1] || epg.end);
                const entry = findEntryForSlot(entries, slotStart, slotEnd);
                const isNowColumn = index === nowSlotIndex;
                if (!entry) {
                  return `<div class="epg-cell epg-empty ${isNowColumn ? "epg-now-column" : ""}"><strong>Schedule unavailable</strong><br><span class="epg-time">No verified listing for this slot</span></div>`;
                }
                const liveNow = entry === liveEntry;
                const isPlanned = plannedEntryKeys.has(entryPlanKey(entry));
                const badge = liveNow
                  ? '<span class="epg-now-tag">NOW</span><br>'
                  : (entry === nextEntry ? '<span class="epg-next-tag">NEXT</span><br>' : "");
                const planBadge = isPlanned ? '<span class="epg-plan-tag">MY CHANNEL</span><br>' : "";
                return `<div class="epg-cell ${channel.id === selectedChannelId ? "epg-channel-active" : ""} ${liveNow ? "epg-now-column" : ""} ${isPlanned ? "epg-plan-match" : ""}">${planBadge}${badge}<strong>${entry.title}</strong><br><span class="epg-time">${formatEntryTime(entry)}</span></div>`;
              }).join("")}
            `;
          }).join("")}
        </div>
      </div>
    </section>
  `;
}
