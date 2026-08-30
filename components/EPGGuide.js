// Proportional TV-guide grid.
//
// Programme blocks are absolutely positioned on a fixed pixels-per-minute scale, so a 60-minute
// programme is exactly twice the width of a 30-minute one. This replaces the previous fixed
// slot matrix, which rendered one cell per (channel x slot): every programme looked identical
// in width, long programmes were duplicated across cells, and short ones were hidden entirely
// whenever a longer programme also overlapped the slot.

const PX_PER_MINUTE = 4; // a 30-minute column is 120px wide
const CHANNEL_COLUMN_PX = 220;
const TICK_MINUTES = 30;
const MIN_GAP_MINUTES = 3; // shorter gaps are not worth rendering as their own block
const MS_PER_MINUTE = 60000;

const timeFormatter = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit" });
const dayFormatter = new Intl.DateTimeFormat("en-GB", { weekday: "short", day: "numeric", month: "short" });

function escapeHtml(value) {
  // EPG titles and descriptions come from third-party XMLTV feeds, so they are untrusted input
  // being written into innerHTML.
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatTime(value) {
  return timeFormatter.format(new Date(value));
}

function channelInitials(name = "") {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]?.toUpperCase() || "").join("");
}

export function dayKeyOf(date) {
  const d = new Date(date);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/**
 * Slice one channel's entries into positioned segments, clamped to the visible window.
 *
 * The repository returns entries that straddle the window edges (overlap semantics), so a
 * programme running 22:00-01:30 must be clipped at midnight while still reporting its real
 * times. The `cursor` clamp also de-overlaps dirty source data, which does occur in real feeds
 * and would otherwise stack blocks on top of each other.
 */
export function layoutRow(entries, windowStartMs, windowEndMs) {
  const segments = [];
  let cursor = windowStartMs;
  const ordered = [...entries].sort((a, b) => Date.parse(a.start_time) - Date.parse(b.start_time));

  for (const entry of ordered) {
    const rawStart = Date.parse(entry.start_time);
    const rawEnd = Date.parse(entry.end_time);
    if (!Number.isFinite(rawStart) || !Number.isFinite(rawEnd)) continue;

    const start = Math.max(rawStart, windowStartMs, cursor);
    const end = Math.min(rawEnd, windowEndMs);
    if (end - start < MS_PER_MINUTE) continue; // sub-minute slivers are not renderable

    if (start - cursor >= MIN_GAP_MINUTES * MS_PER_MINUTE) {
      segments.push({ kind: "gap", start: cursor, end: start });
    }
    segments.push({
      kind: "entry",
      entry,
      start,
      end,
      clippedStart: rawStart < windowStartMs,
      clippedEnd: rawEnd > windowEndMs
    });
    cursor = end;
  }

  if (windowEndMs - cursor >= MIN_GAP_MINUTES * MS_PER_MINUTE) {
    segments.push({ kind: "gap", start: cursor, end: windowEndMs });
  }
  return segments;
}

function planIndexFor(activePlan) {
  // Three tiers so a highlight survives an EPG row being pruned and recreated with a new
  // primary key: real FK first, then the durable natural key, then channel + exact start time.
  const byEntryId = new Map();
  const byCandidateId = new Map();
  const byChannelStart = new Map();
  for (const item of activePlan?.items || []) {
    if (item.resultType !== "live_program") continue;
    if (item.epgEntryId != null) byEntryId.set(item.epgEntryId, item);
    if (item.candidateId?.startsWith("epg:")) byCandidateId.set(item.candidateId, item);
    if (item.channelId && item.availabilityStart) {
      byChannelStart.set(`${item.channelId}@${Date.parse(item.availabilityStart)}`, item);
    }
  }
  return { byEntryId, byCandidateId, byChannelStart };
}

function matchPlanItem(index, channel, entry) {
  return (
    index.byEntryId.get(entry.id) ||
    index.byCandidateId.get(`epg:${channel.id}:${entry.source}:${entry.external_id}`) ||
    index.byChannelStart.get(`${channel.id}@${Date.parse(entry.start_time)}`) ||
    null
  );
}

function renderChannelCell(channel, isSelected) {
  const logo = channel.logo_url
    ? `<img src="${escapeHtml(channel.logo_url)}" alt="${escapeHtml(channel.name)} logo" loading="lazy" referrerpolicy="no-referrer" />`
    : `<span>${escapeHtml(channelInitials(channel.name))}</span>`;
  const meta = [channel.category, channel.language ? String(channel.language).toUpperCase() : null, channel.country]
    .filter(Boolean)
    .join(" • ");
  return `
    <div class="epg-channel ${isSelected ? "is-selected" : ""}" data-epg-channel-id="${channel.id}">
      <span class="channel-logo">${logo}</span>
      <div class="epg-channel-text">
        <strong>${escapeHtml(channel.name)}</strong>
        <small class="muted">${escapeHtml(meta)}</small>
      </div>
    </div>
  `;
}

function renderBlock(segment, channel, planItem, nowMs) {
  const { entry, start, end } = segment;
  const left = ((start - segment.windowStartMs) / MS_PER_MINUTE) * PX_PER_MINUTE;
  const width = ((end - start) / MS_PER_MINUTE) * PX_PER_MINUTE;
  const realStart = Date.parse(entry.start_time);
  const realEnd = Date.parse(entry.end_time);
  const isLive = realStart <= nowMs && nowMs < realEnd;

  // Narrow blocks cannot fit every element; degrade rather than overflow.
  const density = width < 56 ? "is-micro" : width < 108 ? "is-tight" : "";
  const pills = [
    isLive ? '<span class="epg-now-tag">NOW</span>' : "",
    planItem ? '<span class="epg-plan-tag">&#9733; My Channel</span>' : ""
  ].filter(Boolean).join("");

  // Always label the real broadcast times, even when the block itself is clipped by the window.
  const label = `${formatTime(entry.start_time)} - ${formatTime(entry.end_time)}`;
  const tooltip = [
    `${entry.title} · ${label}`,
    channel.name,
    isLive ? "On air now" : "",
    planItem ? `My Channel: ${planItem.recommendationReason || "part of your accepted lineup"}` : ""
  ].filter(Boolean).join(" — ");

  return `
    <button type="button"
      class="epg-block ${isLive ? "is-live" : ""} ${planItem ? "is-planned" : ""} ${density} ${segment.clippedStart ? "is-clipped-start" : ""} ${segment.clippedEnd ? "is-clipped-end" : ""}"
      style="left:${left.toFixed(2)}px;width:${Math.max(width, 2).toFixed(2)}px"
      data-epg-entry-id="${entry.id}"
      data-epg-block-channel-id="${channel.id}"
      data-epg-start="${realStart}"
      data-epg-end="${realEnd}"
      title="${escapeHtml(tooltip)}"
      aria-label="${escapeHtml(tooltip)}">
      ${pills ? `<span class="epg-block-pills">${pills}</span>` : ""}
      <strong class="epg-block-title">${escapeHtml(entry.title)}</strong>
      <span class="epg-time">${escapeHtml(label)}</span>
    </button>
  `;
}

function renderGap(segment) {
  const left = ((segment.start - segment.windowStartMs) / MS_PER_MINUTE) * PX_PER_MINUTE;
  const width = ((segment.end - segment.start) / MS_PER_MINUTE) * PX_PER_MINUTE;
  return `<div class="epg-block epg-gap" style="left:${left.toFixed(2)}px;width:${width.toFixed(2)}px"><span>Schedule unavailable</span></div>`;
}

function renderDatebar(selectedDate, canGoBack, canGoForward) {
  const isToday = dayKeyOf(selectedDate) === dayKeyOf(new Date());
  return `
    <div class="epg-datebar">
      <button type="button" class="chip" data-epg-day="-1" ${canGoBack ? "" : "disabled"}>&lsaquo; Prev</button>
      <button type="button" class="chip ${isToday ? "active" : ""}" data-epg-day="today">Today</button>
      <button type="button" class="chip" data-epg-day="1" ${canGoForward ? "" : "disabled"}>Next &rsaquo;</button>
      <input class="input epg-date-input" type="date" value="${dayKeyOf(selectedDate)}" data-epg-date aria-label="Guide date" />
      <span class="muted epg-datebar-label">${escapeHtml(dayFormatter.format(selectedDate))} &middot; 30-minute grid</span>
    </div>
  `;
}

export function EPGGuide({ epg, selectedChannelId = null, activePlan = null, selectedDate = new Date(), loading = false } = {}) {
  const channels = epg?.channels || [];
  const datebar = renderDatebar(selectedDate, true, true);

  if (loading) {
    return `
      <section class="epg" data-epg>
        <div class="section-head"><div><span class="eyebrow">Live TV</span><h2>TV Guide</h2></div>${datebar}</div>
        <div class="epg-placeholder">Loading the schedule for ${escapeHtml(dayFormatter.format(selectedDate))}...</div>
      </section>
    `;
  }

  if (!channels.length || !epg?.start || !epg?.end) {
    return `
      <section class="epg" data-epg>
        <div class="section-head"><div><span class="eyebrow">Live TV</span><h2>TV Guide</h2></div>${datebar}</div>
        <div class="epg-placeholder">No verified schedule data is published for this selection.</div>
      </section>
    `;
  }

  const windowStartMs = Date.parse(epg.start);
  const windowEndMs = Date.parse(epg.end);
  const totalMinutes = (windowEndMs - windowStartMs) / MS_PER_MINUTE;
  const canvasWidth = totalMinutes * PX_PER_MINUTE;
  const nowMs = Date.now();
  const planIndex = planIndexFor(activePlan);
  const isToday = nowMs >= windowStartMs && nowMs < windowEndMs;

  const ticks = [];
  for (let minute = 0; minute < totalMinutes; minute += TICK_MINUTES) {
    const tickTime = new Date(windowStartMs + minute * MS_PER_MINUTE);
    const isHour = tickTime.getMinutes() === 0;
    ticks.push(
      `<span class="epg-tick ${isHour ? "is-hour" : ""}" style="left:${(minute * PX_PER_MINUTE).toFixed(2)}px">${formatTime(tickTime)}</span>`
    );
  }

  let plannedOnThisDay = 0;
  const rows = channels.map(({ channel, entries }) => {
    const segments = layoutRow(entries || [], windowStartMs, windowEndMs).map((segment) => ({ ...segment, windowStartMs }));
    const blocks = segments
      .map((segment) => {
        if (segment.kind === "gap") return renderGap(segment);
        const planItem = matchPlanItem(planIndex, channel, segment.entry);
        if (planItem) plannedOnThisDay += 1;
        return renderBlock(segment, channel, planItem, nowMs);
      })
      .join("");
    const trackBody = segments.length
      ? blocks
      : `<div class="epg-block epg-gap" style="left:0px;width:${canvasWidth.toFixed(2)}px"><span>Schedule unavailable</span></div>`;
    return `
      <div class="epg-row" data-epg-row-channel-id="${channel.id}">
        ${renderChannelCell(channel, channel.id === selectedChannelId)}
        <div class="epg-track">${trackBody}</div>
      </div>
    `;
  }).join("");

  const nowOffsetPx = isToday ? ((nowMs - windowStartMs) / MS_PER_MINUTE) * PX_PER_MINUTE : 0;
  const planNote = plannedOnThisDay
    ? `<span class="epg-plan-note">&#9733; ${plannedOnThisDay} My Channel ${plannedOnThisDay === 1 ? "programme" : "programmes"} on this day</span>`
    : "";

  return `
    <section class="epg" data-epg>
      <div class="section-head">
        <div>
          <span class="eyebrow">Live TV</span>
          <h2>TV Guide</h2>
        </div>
        ${datebar}
      </div>
      ${planNote ? `<div class="epg-plan-strip">${planNote}</div>` : ""}
      <div class="epg-viewport" data-epg-viewport>
        <div class="epg-canvas ${isToday ? "" : "is-other-day"}"
             style="--epg-ppm:${PX_PER_MINUTE}px;--epg-width:${canvasWidth.toFixed(2)}px;--epg-channel-col:${CHANNEL_COLUMN_PX}px;--epg-now-x:${nowOffsetPx.toFixed(2)}px"
             data-epg-canvas
             data-epg-day="${dayKeyOf(selectedDate)}"
             data-epg-window-start="${windowStartMs}"
             data-epg-window-end="${windowEndMs}">
          <div class="epg-timeline">
            <div class="epg-corner">Channel</div>
            <div class="epg-ticks" style="width:${canvasWidth.toFixed(2)}px">${ticks.join("")}</div>
          </div>
          <div class="epg-rows">${rows}</div>
          <div class="epg-nowline" aria-hidden="true"></div>
        </div>
      </div>
      <div data-epg-detail></div>
    </section>
  `;
}

// ---------------------------------------------------------------------------
// Lifecycle. LiveTvPage re-creates #epgMount via innerHTML on every render, which destroys the
// viewport element, so scroll position and the current-time timer must be re-established after
// each render and torn down when the page goes away.
// ---------------------------------------------------------------------------

const scrollMemory = new Map(); // dayKey -> scrollLeft
let nowTimer = null;
let blockClock = [];
let boundRoot = null;
let boundClickHandler = null;

function defaultScrollLeft(canvas) {
  const windowStart = Number(canvas.dataset.epgWindowStart);
  const windowEnd = Number(canvas.dataset.epgWindowEnd);
  const now = Date.now();
  // Today: put "now" about a quarter in. Other days: open at prime time rather than 00:00.
  const anchor = now >= windowStart && now < windowEnd ? now : windowStart + 18 * 60 * MS_PER_MINUTE;
  const anchorPx = ((anchor - windowStart) / MS_PER_MINUTE) * PX_PER_MINUTE;
  return Math.max(0, anchorPx - 240);
}

export function captureEPGScroll(root) {
  const viewport = root?.querySelector("[data-epg-viewport]");
  const canvas = root?.querySelector("[data-epg-canvas]");
  if (viewport && canvas) scrollMemory.set(canvas.dataset.epgDay, viewport.scrollLeft);
}

export function cleanupEPGGuide() {
  if (nowTimer) window.clearInterval(nowTimer);
  nowTimer = null;
  blockClock = [];
  // The mount element itself survives innerHTML re-renders, so a delegated listener left
  // attached would stack up: after N renders one click fired the handler N times, which made
  // "Next day" jump several days at once.
  if (boundRoot && boundClickHandler) {
    boundRoot.removeEventListener("click", boundClickHandler);
  }
  boundRoot = null;
  boundClickHandler = null;
}

export function mountEPGGuide(root, { onSelectDate, onSelectEntry, onSelectChannel } = {}) {
  cleanupEPGGuide();
  if (!root) return;
  boundRoot = root;

  const viewport = root.querySelector("[data-epg-viewport]");
  const canvas = root.querySelector("[data-epg-canvas]");

  if (viewport && canvas) {
    const dayKey = canvas.dataset.epgDay;
    const remembered = scrollMemory.get(dayKey);
    viewport.scrollLeft = remembered ?? defaultScrollLeft(canvas);

    let queued = false;
    viewport.addEventListener("scroll", () => {
      if (queued) return;
      queued = true;
      window.requestAnimationFrame(() => {
        queued = false;
        scrollMemory.set(dayKey, viewport.scrollLeft);
      });
    }, { passive: true });

    blockClock = Array.from(root.querySelectorAll(".epg-block[data-epg-start]")).map((element) => ({
      element,
      startMs: Number(element.dataset.epgStart),
      endMs: Number(element.dataset.epgEnd)
    }));

    const tick = () => {
      // innerHTML wipes fire no lifecycle event, so self-terminate if this canvas is orphaned.
      if (!document.body.contains(canvas)) {
        cleanupEPGGuide();
        return;
      }
      if (document.hidden) return;
      const now = Date.now();
      const windowStart = Number(canvas.dataset.epgWindowStart);
      const windowEnd = Number(canvas.dataset.epgWindowEnd);
      if (now >= windowStart && now < windowEnd) {
        canvas.classList.remove("is-other-day");
        canvas.style.setProperty("--epg-now-x", `${(((now - windowStart) / MS_PER_MINUTE) * PX_PER_MINUTE).toFixed(2)}px`);
      } else {
        canvas.classList.add("is-other-day");
      }
      for (const { element, startMs, endMs } of blockClock) {
        element.classList.toggle("is-live", now >= startMs && now < endMs);
      }
    };
    tick();
    // A minute is only 4px at this scale, so sub-minute precision is invisible.
    nowTimer = window.setInterval(tick, 30000);
  }

  boundClickHandler = (event) => {
    const dayButton = event.target.closest("[data-epg-day]");
    if (dayButton && onSelectDate) {
      onSelectDate(dayButton.dataset.epgDay);
      return;
    }
    const block = event.target.closest(".epg-block[data-epg-entry-id]");
    if (block && onSelectEntry) {
      onSelectEntry(Number(block.dataset.epgEntryId), Number(block.dataset.epgBlockChannelId));
      return;
    }
    const channelCell = event.target.closest(".epg-channel[data-epg-channel-id]");
    if (channelCell && onSelectChannel) {
      onSelectChannel(Number(channelCell.dataset.epgChannelId));
    }
  };
  root.addEventListener("click", boundClickHandler);

  const dateInput = root.querySelector("[data-epg-date]");
  if (dateInput && onSelectDate) {
    dateInput.addEventListener("change", () => onSelectDate(dateInput.value));
  }
}

export function renderEPGDetail(root, { entry, channel, planItem, isPlayable }) {
  const mount = root?.querySelector("[data-epg-detail]");
  if (!mount) return;
  if (!entry) {
    mount.innerHTML = "";
    return;
  }
  const now = Date.now();
  const isLive = Date.parse(entry.start_time) <= now && now < Date.parse(entry.end_time);
  mount.innerHTML = `
    <article class="epg-detail">
      <div class="epg-detail-head">
        <div>
          <span class="eyebrow">${escapeHtml(channel?.name || "Programme")}</span>
          <h3>${escapeHtml(entry.title)}</h3>
        </div>
        <button type="button" class="ghost-button" data-epg-detail-close>Close</button>
      </div>
      <div class="epg-detail-meta">
        <span class="live-badge ${isLive ? "is-live" : ""}">${isLive ? "Live now" : "Scheduled"}</span>
        <span>${escapeHtml(formatTime(entry.start_time))} - ${escapeHtml(formatTime(entry.end_time))}</span>
        ${entry.category ? `<span>${escapeHtml(entry.category)}</span>` : ""}
      </div>
      ${planItem ? `<p class="epg-detail-plan">&#9733; This programme is part of your accepted My Channel lineup.${planItem.recommendationReason ? ` ${escapeHtml(planItem.recommendationReason)}` : ""}</p>` : ""}
      <p class="epg-detail-description">${escapeHtml(entry.description || "No description is published for this programme.")}</p>
      ${isLive && isPlayable
        ? `<button type="button" class="primary-button" data-epg-watch-channel="${channel.id}">Watch Live</button>`
        : `<span class="muted">${isLive ? "This channel is not currently playable." : "Not on air yet."}</span>`}
    </article>
  `;
}
