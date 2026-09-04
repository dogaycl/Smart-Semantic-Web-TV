import { getCurrentUser } from "../contexts/authContext.js";
import { api } from "../services/api.js?v=55";
import { VideoPlayer, cleanupVideoPlayer, mountVideoPlayer } from "../components/VideoPlayer.js?v=55";
import { mountPlayerAdapter, renderPlaybackSurface } from "../components/playerAdapters.js";

let lineupAdapter = null;
let lineupAdvanceTimer = null;

function cleanupLineupPlayer() {
  window.clearTimeout(lineupAdvanceTimer);
  lineupAdvanceTimer = null;
  cleanupVideoPlayer();
  lineupAdapter?.destroy?.();
  lineupAdapter = null;
}

// The "When?" buttons are quick fills for the always-visible date/start/end inputs below them,
// not separate modes. The window is always read from those three fields.
const WHEN_OPTIONS = [
  { id: "now", label: "Now" },
  { id: "tonight", label: "Tonight" },
  { id: "tomorrow", label: "Tomorrow" }
];

const DEFAULT_WINDOW_MINUTES = 180;

const DURATION_OPTIONS = [
  { id: "60", label: "1 hour" },
  { id: "120", label: "2 hours" },
  { id: "180", label: "3 hours" },
  { id: "custom", label: "Custom" }
];

const MOOD_CATEGORIES = [
  "Technology",
  "Sports",
  "Music",
  "Documentary",
  "News",
  "Science Fiction",
  "Drama",
  "Comedy",
  "Entertainment",
  "Youth"
];

function pad(value) {
  return String(value).padStart(2, "0");
}

function toDateValue(date) {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function toTimeValue(date) {
  return `${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function addMinutes(date, minutes) {
  return new Date(date.getTime() + minutes * 60000);
}

function roundToNext5Minutes(date) {
  const stepMs = 5 * 60000;
  return new Date(Math.ceil(date.getTime() / stepMs) * stepMs);
}

// Quick-fill values for the date/start/end inputs. "Now"/"Tonight" late in the evening produce
// an end time past midnight, which computeWindow and the backend both read as a next-day window.
function presetWindow(mode) {
  const now = new Date();
  let start;
  if (mode === "now") {
    start = roundToNext5Minutes(now);
  } else if (mode === "tomorrow") {
    start = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 19, 0, 0, 0);
  } else {
    const tonight = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 19, 0, 0, 0);
    start = now > tonight ? roundToNext5Minutes(now) : tonight;
  }
  const end = addMinutes(start, DEFAULT_WINDOW_MINUTES);
  return { date: toDateValue(start), start: toTimeValue(start), end: toTimeValue(end) };
}

function computeWindow(state) {
  const now = new Date();
  const [year, month, day] = (state.customDate || toDateValue(now)).split("-").map(Number);
  const [startHour, startMinute] = (state.customStart || "19:00").split(":").map(Number);
  const [endHour, endMinute] = (state.customEnd || "22:00").split(":").map(Number);

  const start = new Date(year, (month || 1) - 1, day || 1, startHour || 0, startMinute || 0, 0, 0);
  const end = new Date(year, (month || 1) - 1, day || 1, endHour || 0, endMinute || 0, 0, 0);
  // An end time at or before the start time means the window runs past midnight into the next
  // day. The EPG feed covers 48h ahead, so a cross-midnight window is fine.
  if (end <= start) {
    end.setDate(end.getDate() + 1);
  }

  const windowMinutes = Math.round((end.getTime() - start.getTime()) / 60000);
  const desiredMinutes = state.durationMode === "custom"
    ? Math.max(15, Number(state.customDuration) || 60)
    : Number(state.durationMode);
  // "How much time?" is a cap on how much content to schedule inside the window; it can never
  // exceed the window itself (the backend rejects that).
  const durationMinutes = Math.max(15, Math.min(desiredMinutes, windowMinutes));

  return { start, end, windowMinutes, durationMinutes };
}

function formatClock(date, timezone) {
  return new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: timezone }).format(date);
}

function formatWindow(dateStart, dateEnd, timezone) {
  const dateLabel = new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    day: "2-digit",
    month: "short",
    timeZone: timezone
  }).format(dateStart);
  return `${dateLabel} • ${formatClock(dateStart, timezone)} - ${formatClock(dateEnd, timezone)}`;
}

function liveTiming(item, now) {
  if (item.resultType !== "live_program") return null;
  const start = new Date(item.availabilityStart || item.plannedStart);
  const end = new Date(item.availabilityEnd || item.plannedEnd);
  if (now >= start && now < end) return "now";
  if (now < start) return "upcoming";
  return "ended";
}

// The lineup plays like a channel: start on the item scheduled for "now", or - if the whole
// lineup is still ahead or already finished - the first or last item respectively.
function pickNowPlayingIndex(items, now = new Date()) {
  if (!items.length) return 0;
  const running = items.findIndex((item) => {
    const end = new Date(item.plannedEnd);
    return now < end;
  });
  return running === -1 ? items.length - 1 : running;
}

function playableItem(item) {
  if (!item) return false;
  if (item.resultType === "live_program") return Boolean(item.liveChannelId);
  return Boolean(item.contentSlug);
}

// Simplify the type badge to the three states the timeline shows: LIVE / MOVIE / SERIES.
function timelineBadge(item) {
  if (item.resultType === "live_program") return { cls: "live", label: "LIVE" };
  if (item.resultType === "series") return { cls: "series", label: "SERIES" };
  return { cls: "movie", label: "MOVIE" };
}

function planItemCard(item, timezone, now, index = 0) {
  const { cls, label } = timelineBadge(item);
  const timing = liveTiming(item, now);
  const isLive = item.resultType === "live_program";
  const badgeLabel = timing === "now" ? "LIVE NOW" : label;
  const badgeClass = timing === "now" && isLive ? `${cls} is-now` : cls;
  const startClock = formatClock(new Date(item.plannedStart), timezone);
  const endClock = formatClock(new Date(item.plannedEnd), timezone);

  let statusNote = "";
  if (timing === "upcoming") statusNote = `Starts ${startClock}`;
  else if (timing === "ended") statusNote = "Already ended";
  else if (timing === "now") statusNote = "On now";

  // A playable item plays inside the My Channel player at the top; anything else keeps the
  // normal link to its detail/live page.
  let watchAction = playableItem(item)
    ? `<button class="primary-button" type="button" data-planner-play-index="${index}">${isLive ? "Watch Live" : "Watch"}</button>`
    : `<a class="primary-button" href="${item.routePath}">Watch</a>`;
  if (timing === "ended" && !playableItem(item)) {
    watchAction = `<a class="ghost-button" href="#/live-tv">Open Live TV</a>`;
  }

  return `
    <article class="planner-plan-item planner-timeline-item ${timing === "ended" ? "muted" : ""}" data-planner-item-index="${index}">
      <div class="planner-timeline-slot">
        <span class="planner-timeline-clock">${startClock} &ndash; ${endClock}</span>
        ${statusNote ? `<span class="planner-timeline-note">${statusNote}</span>` : ""}
      </div>
      <div class="planner-timeline-head">
        <span class="planner-type-badge ${badgeClass}">${badgeLabel}</span>
        <span class="planner-timeline-runtime">${item.runtimeDisplay}</span>
      </div>
      <strong class="planner-timeline-title">${item.title}</strong>
      ${isLive && item.channel?.name ? `<span class="planner-timeline-channel">${item.channel.name}</span>` : `<span class="planner-timeline-channel muted">${item.category}</span>`}
      <p class="planner-why-this">${item.recommendationReason || "Matched to your profile."}</p>
      <div class="planner-timeline-action">${watchAction}</div>
    </article>
  `;
}

function savedPlanRow(plan, timezone) {
  return `
    <button class="planner-saved-button ${plan.isAccepted ? "is-accepted" : ""}" data-plan-id="${plan.id}" type="button">
      <strong>${new Intl.DateTimeFormat("en-GB", { weekday: "short", hour: "2-digit", minute: "2-digit", timeZone: timezone }).format(new Date(plan.availableStart))}</strong>
      <span>${plan.summary}</span>
      <small>${plan.items.length} items &middot; ${plan.generationSource === "gemini" ? "Gemini" : "Fallback"}${plan.isAccepted ? " &middot; Accepted" : ""}</small>
    </button>
  `;
}

function renderPlan(plan, timezone) {
  if (!plan) {
    return `
      <div class="planner-empty">
        <strong>Your personalized lineup will appear here.</strong>
        <span>Choose when you're free and for how long, then create your channel.</span>
      </div>
    `;
  }

  const now = new Date();
  const hasPlayable = plan.items.some(playableItem);
  return `
    ${hasPlayable ? `
    <div class="planner-now-playing" data-planner-player-shell>
      <div class="planner-player-surface" data-planner-player>
        <div class="planner-player-loading">Tuning your channel&hellip;</div>
      </div>
      <div class="planner-player-bar">
        <button class="ghost-button" type="button" data-planner-prev>&#9664; Prev</button>
        <div class="planner-player-now" data-planner-now></div>
        <button class="ghost-button" type="button" data-planner-next>Next &#9654;</button>
      </div>
    </div>
    ` : ""}
    <div class="planner-result-summary">
      <span class="eyebrow">My Channel</span>
      <h2>${plan.summary}</h2>
      <div class="planner-plan-meta">
        <span>${formatWindow(new Date(plan.availableStart), new Date(plan.availableEnd), timezone)}</span>
        <span>${plan.generationSource === "gemini" ? "Gemini plan" : "Deterministic fallback"}</span>
        ${plan.llmRepairApplied ? "<span>Validated after repair</span>" : ""}
        ${plan.isAccepted ? `<span class="planner-status-pill accepted">Accepted${plan.acceptedAt ? ` ${formatClock(new Date(plan.acceptedAt), timezone)}` : ""}</span>` : ""}
      </div>
      <div class="planner-result-actions">
        ${plan.isAccepted
          ? `<span class="planner-result-note">This is your active My Channel plan for ${plan.planDate}.</span>`
          : `<button class="primary-button" type="button" data-accept-plan-id="${plan.id}">Accept This Lineup</button>`}
      </div>
    </div>
  `;
}

// The lineup itself renders as a full-width horizontal strip below the two side-by-side cards,
// so it always has room to scroll horizontally regardless of the studio column widths.
function renderPlanStrip(plan, timezone) {
  if (!plan || !plan.items?.length) return "";
  const now = new Date();
  return `
    <div class="planner-lineup-head">
      <span class="eyebrow">Your lineup</span>
      <h3>${plan.items.length} ${plan.items.length === 1 ? "programme" : "programmes"} &middot; scroll to browse</h3>
    </div>
    <div class="planner-timeline-scroll">
      <ol class="planner-timeline">
        ${plan.items.map((item, index) => planItemCard(item, timezone, now, index)).join("")}
      </ol>
    </div>
  `;
}

export function MyChannelPage() {
  const user = getCurrentUser();
  const savedCategories = (user?.preferredCategories?.length ? user.preferredCategories : ["Technology", "Sports", "Music"]);
  const moodChips = Array.from(new Set([...savedCategories, ...MOOD_CATEGORIES])).slice(0, 10);

  const initialWindow = presetWindow("tonight");
  const state = {
    customDate: initialWindow.date,
    customStart: initialWindow.start,
    customEnd: initialWindow.end,
    durationMode: "180",
    customDuration: 180,
    selectedCategories: new Set(savedCategories),
    moodText: ""
  };

  queueMicrotask(async () => {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    const controlsMount = document.querySelector("[data-my-channel-controls]");
    const resultMount = document.querySelector("[data-planner-result]");
    const savedMount = document.querySelector("[data-planner-saved]");
    const statusMount = document.querySelector("[data-planner-status]");
    const customDurationMount = document.querySelector("[data-duration-custom]");
    const windowPreviewMount = document.querySelector("[data-my-channel-window]");
    const dateInput = document.querySelector("[name=customDate]");
    const startInput = document.querySelector("[name=customStart]");
    const endInput = document.querySelector("[name=customEnd]");

    // Stop the lineup player when leaving the page so a stream does not keep running in the background.
    window.addEventListener("hashchange", cleanupLineupPlayer, { once: true });

    let savedPlans = [];
    let activePlan = null;
    let lineupToken = 0;

    // Plays the accepted/generated lineup like a channel: the item scheduled for "now" starts
    // automatically, and playback rolls on to the next item when a live programme's slot ends or
    // an on-demand title finishes.
    const lineupPlayer = {
      index: 0,
      async load(index) {
        const items = activePlan?.items || [];
        if (!items.length) return;
        this.index = Math.max(0, Math.min(index, items.length - 1));
        const item = items[this.index];
        const token = ++lineupToken;

        cleanupLineupPlayer();
        const surface = document.querySelector("[data-planner-player]");
        const nowBar = document.querySelector("[data-planner-now]");
        if (!surface) return;

        document.querySelectorAll("[data-planner-item-index]").forEach((node) => {
          node.classList.toggle("is-playing", Number(node.dataset.plannerItemIndex) === this.index);
        });
        if (nowBar) {
          nowBar.innerHTML = `<span class="planner-now-label">Now playing</span> <strong>${item.title}</strong>${item.channel?.name ? ` &middot; ${item.channel.name}` : ""}`;
        }
        surface.innerHTML = `<div class="planner-player-loading">Tuning your channel&hellip;</div>`;

        try {
          if (item.resultType === "live_program" && item.liveChannelId) {
            const live = await api.getChannelLive(item.liveChannelId);
            if (token !== lineupToken) return;
            if (!live || !live.playback || live.playback.type === "unavailable") {
              throw new Error(live?.stream_error || "This channel is not available right now.");
            }
            surface.innerHTML = VideoPlayer(live);
            await mountVideoPlayer(live, {
              onPlaybackFailure: () => this.showUnplayable(item, "This live stream could not start in the browser.")
            });
            // Roll to the next item when this programme's scheduled slot ends.
            const msToEnd = new Date(item.plannedEnd).getTime() - Date.now();
            if (msToEnd > 0 && msToEnd < 6 * 60 * 60 * 1000 && this.index < items.length - 1) {
              lineupAdvanceTimer = window.setTimeout(() => this.load(this.index + 1), msToEnd + 1000);
            }
          } else if (item.contentSlug) {
            const playback = await api.getContentPlayback(item.contentSlug);
            if (token !== lineupToken) return;
            const source = playback?.primarySource || playback?.sources?.[0] || null;
            if (!playback?.playbackAvailable || !source) {
              throw new Error(playback?.message || "No playable source for this title yet.");
            }
            surface.innerHTML = `<div class="planner-player-surface-inner">${renderPlaybackSurface(source, item.title)}</div>`;
            lineupAdapter = await mountPlayerAdapter({
              source,
              root: surface.querySelector(".planner-player-surface-inner"),
              onStateChange: ({ state: playerState }) => {
                if (playerState === "ended" && this.index < items.length - 1) {
                  this.load(this.index + 1);
                }
              },
              onError: () => this.showUnplayable(item, "This title could not be played in the browser.")
            });
            await lineupAdapter?.play?.().catch(() => {});
          } else {
            this.showUnplayable(item, "This item has no in-page player.");
          }
        } catch (error) {
          if (token !== lineupToken) return;
          this.showUnplayable(item, error?.message || "This item could not be played.");
        }
      },
      showUnplayable(item, message) {
        const surface = document.querySelector("[data-planner-player]");
        if (!surface) return;
        surface.innerHTML = `
          <div class="planner-player-fallback">
            <strong>${item.title}</strong>
            <p>${message}</p>
            <a class="ghost-button" href="${item.routePath || "#/live-tv"}">Open ${item.resultType === "live_program" ? "Live TV" : "watch page"}</a>
          </div>
        `;
      },
      bind() {
        const shell = document.querySelector("[data-planner-player-shell]");
        if (!shell) return;
        shell.querySelector("[data-planner-prev]")?.addEventListener("click", () => this.load(this.index - 1));
        shell.querySelector("[data-planner-next]")?.addEventListener("click", () => this.load(this.index + 1));
        document.querySelectorAll("[data-planner-play-index]").forEach((button) => {
          button.addEventListener("click", () => this.load(Number(button.dataset.plannerPlayIndex)));
        });
      },
      start() {
        if (!document.querySelector("[data-planner-player-shell]")) return;
        this.bind();
        this.load(pickNowPlayingIndex(activePlan?.items || []));
      }
    };

    const drawResult = () => {
      cleanupLineupPlayer();
      lineupToken += 1;
      resultMount.innerHTML = renderPlan(activePlan, timezone);
      const stripMount = document.querySelector("[data-planner-lineup-strip]");
      if (stripMount) stripMount.innerHTML = renderPlanStrip(activePlan, timezone);
      lineupPlayer.start();
      document.querySelector("[data-accept-plan-id]")?.addEventListener("click", async (event) => {
        const button = event.currentTarget;
        button.disabled = true;
        statusMount.textContent = "Saving this lineup as your active My Channel plan...";
        try {
          activePlan = await api.acceptMyChannelPlan(button.dataset.acceptPlanId);
          await reloadPlans();
          statusMount.textContent = "Accepted. Live TV EPG will highlight this plan.";
        } catch (error) {
          button.disabled = false;
          statusMount.textContent = error.message || "This plan could not be accepted.";
        }
      });
    };

    const drawSaved = () => {
      savedMount.innerHTML = savedPlans.length
        ? savedPlans.map((plan) => savedPlanRow(plan, timezone)).join("")
        : `<div class="planner-empty"><strong>No saved plans yet.</strong><span>Your generated My Channel lineups will appear here.</span></div>`;

      document.querySelectorAll("[data-plan-id]").forEach((button) => {
        button.addEventListener("click", async () => {
          statusMount.textContent = "Loading saved plan...";
          try {
            activePlan = await api.getMyChannelPlan(button.dataset.planId);
            drawResult();
            statusMount.textContent = "";
          } catch (error) {
            statusMount.textContent = error.message || "Saved plan could not be loaded.";
          }
        });
      });
    };

    const reloadPlans = async () => {
      savedPlans = await api.getMyChannelPlans().catch(() => []);
      const acceptedPlan = savedPlans.find((plan) => plan.isAccepted) || null;
      if (activePlan) {
        activePlan = savedPlans.find((plan) => plan.id === activePlan.id) || acceptedPlan || savedPlans[0] || null;
      } else {
        activePlan = acceptedPlan || savedPlans[0] || null;
      }
      drawResult();
      drawSaved();
    };

    const syncControlVisibility = () => {
      customDurationMount.hidden = state.durationMode !== "custom";
    };

    const drawControls = () => {
      const { start, end, windowMinutes, durationMinutes } = computeWindow(state);
      document.querySelectorAll("[data-duration-option]").forEach((button) => {
        button.classList.toggle("active", button.dataset.durationOption === state.durationMode);
      });
      document.querySelectorAll("[data-mood-chip]").forEach((button) => {
        button.classList.toggle("active", state.selectedCategories.has(button.dataset.moodChip));
      });
      syncControlVisibility();
      if (windowPreviewMount) {
        const capNote = durationMinutes < windowMinutes ? ` • plan up to ${durationMinutes} min` : "";
        windowPreviewMount.textContent = `Window: ${formatWindow(start, end, timezone)} • ${windowMinutes} min${capNote}`;
      }
    };

    controlsMount.querySelectorAll("[data-when-option]").forEach((button) => {
      button.addEventListener("click", () => {
        const filled = presetWindow(button.dataset.whenOption);
        state.customDate = filled.date;
        state.customStart = filled.start;
        state.customEnd = filled.end;
        if (dateInput) dateInput.value = filled.date;
        if (startInput) startInput.value = filled.start;
        if (endInput) endInput.value = filled.end;
        drawControls();
      });
    });
    controlsMount.querySelectorAll("[data-duration-option]").forEach((button) => {
      button.addEventListener("click", () => {
        state.durationMode = button.dataset.durationOption;
        drawControls();
      });
    });
    controlsMount.querySelectorAll("[data-mood-chip]").forEach((button) => {
      button.addEventListener("click", () => {
        const value = button.dataset.moodChip;
        if (state.selectedCategories.has(value)) {
          state.selectedCategories.delete(value);
        } else {
          state.selectedCategories.add(value);
        }
        drawControls();
      });
    });

    document.querySelector("[name=customDate]")?.addEventListener("change", (event) => {
      state.customDate = event.target.value;
      drawControls();
    });
    document.querySelector("[name=customStart]")?.addEventListener("change", (event) => {
      state.customStart = event.target.value;
      drawControls();
    });
    document.querySelector("[name=customEnd]")?.addEventListener("change", (event) => {
      state.customEnd = event.target.value;
      drawControls();
    });
    document.querySelector("[name=customDuration]")?.addEventListener("change", (event) => {
      state.customDuration = event.target.value;
      drawControls();
    });
    document.querySelector("[name=moodText]")?.addEventListener("input", (event) => {
      state.moodText = event.target.value;
    });

    document.querySelector("[data-my-channel-form]").addEventListener("submit", async (event) => {
      event.preventDefault();
      const { start, end, durationMinutes } = computeWindow(state);
      if (end <= start) {
        statusMount.textContent = "End time must be later than start time.";
        return;
      }
      const payload = {
        plan_date: toDateValue(start),
        available_start: toTimeValue(start),
        available_end: toTimeValue(end),
        timezone,
        max_duration_minutes: durationMinutes,
        preferred_categories: Array.from(state.selectedCategories),
        include_live: true,
        include_vod: true,
        preference_text: state.moodText.trim() || null
      };

      statusMount.textContent = "Building your channel from real EPG and on-demand candidates...";
      resultMount.innerHTML = `<div class="planner-empty"><strong>My Channel is being built.</strong><span>Selecting only from real, currently available live programs and on-demand titles.</span></div>`;
      try {
        activePlan = await api.generateMyChannel(payload);
        statusMount.textContent = "";
        await reloadPlans();
      } catch (error) {
        resultMount.innerHTML = `<div class="planner-empty"><strong>Could not build My Channel.</strong><span>${error.message || "Please try a different time window."}</span></div>`;
        statusMount.textContent = "";
      }
    });

    drawControls();
    await reloadPlans();
  });

  const interestsLine = user?.interests?.length || user?.preferredCategories?.length
    ? `Using your interests: <strong>${[...new Set([...(user.interests || []), ...(user.preferredCategories || [])])].join(", ")}</strong>`
    : "Add interests on your profile so My Channel can personalize your lineup automatically.";

  return `
    <main class="page ai-hub-page" data-my-channel-page>
      <section class="ai-hub-hero">
        <div class="ai-hub-hero-copy">
          <span class="eyebrow">My Channel</span>
          <h1>Your personalized live + on-demand lineup.</h1>
          <p>My Channel builds a real schedule from currently airing and upcoming live programs on your channels, plus movies and series you can actually watch right now &mdash; matched to your interests, favorites, and watch history.</p>
        </div>
        <aside class="ai-hub-status">
          <span class="eyebrow">Current profile signals</span>
          <h2>${user?.displayName || "Viewer"}</h2>
          <ul>
            <li>${user?.preferredCategories?.length ? user.preferredCategories.join(", ") : "No preferred categories saved yet"}</li>
            <li>${user?.interests?.length ? user.interests.join(", ") : "No interests saved yet"}</li>
            <li>My Channel uses recommendations, favorites, history, and real availability windows.</li>
          </ul>
          <a class="ghost-button" href="#/profile">Update profile signals</a>
        </aside>
      </section>

      <section class="planner-studio">
        <article class="ai-workbench-card planner-form-card">
          <div class="planner-form-head">
            <span class="eyebrow">Build your lineup</span>
            <h2>My Channel &mdash; Tonight</h2>
          </div>
          <form class="planner-form" data-my-channel-form>
            <div class="my-channel-quick-controls" data-my-channel-controls>
              <label>
                <span>When are you free?</span>
                <div class="my-channel-quick-row">
                  ${WHEN_OPTIONS.map((option) => `<button type="button" class="chip" data-when-option="${option.id}">${option.label}</button>`).join("")}
                </div>
                <div class="planner-form-grid" data-when-fields>
                  <label>
                    <span>Date</span>
                    <input class="input" name="customDate" type="date" value="${state.customDate}" />
                  </label>
                  <label>
                    <span>Start time</span>
                    <input class="input" name="customStart" type="time" value="${state.customStart}" />
                  </label>
                  <label>
                    <span>End time</span>
                    <input class="input" name="customEnd" type="time" value="${state.customEnd}" />
                  </label>
                </div>
              </label>
              <label>
                <span>How much of it do you want to fill?</span>
                <div class="my-channel-quick-row">
                  ${DURATION_OPTIONS.map((option) => `<button type="button" class="chip" data-duration-option="${option.id}">${option.label}</button>`).join("")}
                </div>
                <div class="planner-form-grid" data-duration-custom hidden>
                  <label>
                    <span>Minutes</span>
                    <input class="input" name="customDuration" type="number" min="15" max="720" value="${state.customDuration}" />
                  </label>
                </div>
                <p class="my-channel-window-preview" data-my-channel-window></p>
              </label>
              <label>
                <span>What do you feel like watching?</span>
                <div class="my-channel-quick-row">
                  ${moodChips.map((category) => `<button type="button" class="chip" data-mood-chip="${category}">${category}</button>`).join("")}
                </div>
                <p class="my-channel-interests-line">${interestsLine}</p>
                <textarea class="input planner-textarea" name="moodText" placeholder="Optional: describe a mood, e.g. &quot;something calm before bed&quot;"></textarea>
              </label>
            </div>
            <button class="primary-button">Create My Channel</button>
            <p class="muted" data-planner-status></p>
          </form>
        </article>

        <article class="ai-workbench-card planner-result-card">
          <div class="planner-form-head">
            <span class="eyebrow">Your lineup</span>
            <h2>Validated schedule</h2>
          </div>
          <div data-planner-result></div>
        </article>
      </section>

      <section class="planner-lineup-strip" data-planner-lineup-strip></section>

      <section class="ai-workbench">
        <article class="ai-workbench-card">
          <span class="eyebrow">Saved history</span>
          <h2>Recent My Channel lineups</h2>
          <div class="planner-saved-list" data-planner-saved></div>
        </article>
        <article class="ai-workbench-card">
          <span class="eyebrow">Why it is trustworthy</span>
          <h2>My Channel guardrails</h2>
          <p>My Channel does not invent channels, broadcasts, or movies. The backend first builds a real candidate pool from the database (live EPG that is still airing or upcoming on a healthy channel, and on-demand titles you can actually play), sends only candidate IDs and metadata to Gemini, validates the returned schedule, and falls back to a deterministic planner if the AI output is unavailable or invalid.</p>
          <div class="planner-chip-row">
            <span>Real EPG</span>
            <span>Real catalog</span>
            <span>Saved profile</span>
            <span>Validation</span>
            <span>Fallback plan</span>
          </div>
        </article>
      </section>
    </main>
  `;
}
