import { getCurrentUser } from "../contexts/authContext.js";
import { api } from "../services/api.js?v=26";

const WHEN_OPTIONS = [
  { id: "now", label: "Now" },
  { id: "tonight", label: "Tonight" },
  { id: "tomorrow", label: "Tomorrow" },
  { id: "custom", label: "Custom time" }
];

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

function computeWindow(state) {
  const now = new Date();
  let start;
  if (state.whenMode === "now") {
    start = roundToNext5Minutes(now);
  } else if (state.whenMode === "tonight") {
    const tonight = new Date(now.getFullYear(), now.getMonth(), now.getDate(), 19, 0, 0, 0);
    start = now > tonight ? roundToNext5Minutes(now) : tonight;
  } else if (state.whenMode === "tomorrow") {
    start = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1, 19, 0, 0, 0);
  } else {
    const [year, month, day] = (state.customDate || toDateValue(now)).split("-").map(Number);
    const [hour, minute] = (state.customStart || "19:00").split(":").map(Number);
    start = new Date(year, (month || 1) - 1, day || 1, hour || 0, minute || 0, 0, 0);
  }

  let durationMinutes = state.durationMode === "custom"
    ? Math.max(15, Number(state.customDuration) || 60)
    : Number(state.durationMode);
  let end = addMinutes(start, durationMinutes);

  const endOfDay = new Date(start.getFullYear(), start.getMonth(), start.getDate(), 23, 45, 0, 0);
  if (end > endOfDay) {
    end = endOfDay;
    durationMinutes = Math.max(15, Math.round((end.getTime() - start.getTime()) / 60000));
  }
  if (end <= start) {
    end = addMinutes(start, 15);
    durationMinutes = 15;
  }

  return { start, end, durationMinutes };
}

function formatClock(date, timezone) {
  return new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: timezone }).format(date);
}

function typeInfo(item) {
  const category = (item.category || "").toLowerCase();
  const genres = (item.genres || []).map((genre) => genre.toLowerCase());
  const isDocumentary = category.includes("documentary") || genres.includes("documentary");
  if (item.resultType === "live_program") return { cls: "live", label: "LIVE" };
  if (isDocumentary) return { cls: "documentary", label: "DOCUMENTARY" };
  if (item.resultType === "series") return { cls: "series", label: "SERIES" };
  return { cls: "movie", label: "MOVIE" };
}

function liveTiming(item, now) {
  if (item.resultType !== "live_program") return null;
  const start = new Date(item.availabilityStart || item.plannedStart);
  const end = new Date(item.availabilityEnd || item.plannedEnd);
  if (now >= start && now < end) return "now";
  if (now < start) return "upcoming";
  return "ended";
}

function planItemCard(item, timezone, now) {
  const { cls, label } = typeInfo(item);
  const timing = liveTiming(item, now);
  const badgeLabel = timing === "now" ? "LIVE NOW" : label;
  const badgeClass = timing === "now" ? `${cls} is-now` : cls;
  const timeRange = `${formatClock(new Date(item.plannedStart), timezone)} - ${formatClock(new Date(item.plannedEnd), timezone)}`;

  let statusLine = timeRange;
  let watchAction = `<a class="primary-button" href="${item.routePath}"${item.liveChannelId ? ` data-planner-live-channel="${item.liveChannelId}"` : ""}>${item.resultType === "live_program" ? "Watch Live" : "Watch"}</a>`;

  if (timing === "upcoming") {
    statusLine = `Starts at ${formatClock(new Date(item.plannedStart), timezone)} &middot; ${timeRange}`;
  } else if (timing === "ended") {
    statusLine = `Already ended &middot; ${timeRange}`;
    watchAction = `<a class="ghost-button" href="#/live-tv">Open Live TV</a>`;
  }

  return `
    <article class="planner-plan-item ${timing === "ended" ? "muted" : ""}">
      <div class="planner-plan-time">${statusLine}</div>
      <div class="planner-plan-body">
        <div class="planner-plan-head">
          <span class="planner-type-badge ${badgeClass}">${badgeLabel}</span>
          <strong>${item.title}</strong>
        </div>
        <p class="planner-why-this">Why this? ${item.recommendationReason}</p>
        <div class="planner-plan-meta">
          <span>${item.category}</span>
          <span>${item.runtimeDisplay}</span>
          ${item.channel?.name ? `<span>${item.channel.name}</span>` : ""}
        </div>
        ${watchAction}
      </div>
    </article>
  `;
}

function savedPlanRow(plan, timezone) {
  return `
    <button class="planner-saved-button" data-plan-id="${plan.id}" type="button">
      <strong>${new Intl.DateTimeFormat("en-GB", { weekday: "short", hour: "2-digit", minute: "2-digit", timeZone: timezone }).format(new Date(plan.availableStart))}</strong>
      <span>${plan.summary}</span>
      <small>${plan.items.length} items &middot; ${plan.generationSource === "gemini" ? "Gemini" : "Fallback"}</small>
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
  return `
    <div class="planner-result-summary">
      <span class="eyebrow">My Channel</span>
      <h2>${plan.summary}</h2>
      <div class="planner-plan-meta">
        <span>${formatClock(new Date(plan.availableStart), timezone)} - ${formatClock(new Date(plan.availableEnd), timezone)}</span>
        <span>${plan.generationSource === "gemini" ? "Gemini plan" : "Deterministic fallback"}</span>
        ${plan.llmRepairApplied ? "<span>Validated after repair</span>" : ""}
      </div>
    </div>
    <div class="planner-plan-list">
      ${plan.items.map((item) => planItemCard(item, timezone, now)).join("")}
    </div>
  `;
}

export function MyChannelPage() {
  const user = getCurrentUser();
  const savedCategories = (user?.preferredCategories?.length ? user.preferredCategories : ["Technology", "Sports", "Music"]);
  const moodChips = Array.from(new Set([...savedCategories, ...MOOD_CATEGORIES])).slice(0, 10);

  const state = {
    whenMode: "tonight",
    customDate: toDateValue(new Date()),
    customStart: "19:00",
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
    const customWhenMount = document.querySelector("[data-when-custom]");
    const customDurationMount = document.querySelector("[data-duration-custom]");

    const bindLiveLinks = () => {
      document.querySelectorAll("[data-planner-live-channel]").forEach((element) => {
        element.addEventListener("click", () => {
          sessionStorage.setItem("synapse.live.channel-id", element.dataset.plannerLiveChannel);
        });
      });
    };

    let savedPlans = [];
    let activePlan = null;

    const drawResult = () => {
      resultMount.innerHTML = renderPlan(activePlan, timezone);
      bindLiveLinks();
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
      activePlan = activePlan || savedPlans[0] || null;
      drawResult();
      drawSaved();
    };

    const syncControlVisibility = () => {
      customWhenMount.hidden = state.whenMode !== "custom";
      customDurationMount.hidden = state.durationMode !== "custom";
    };

    const drawControls = () => {
      document.querySelectorAll("[data-when-option]").forEach((button) => {
        button.classList.toggle("active", button.dataset.whenOption === state.whenMode);
      });
      document.querySelectorAll("[data-duration-option]").forEach((button) => {
        button.classList.toggle("active", button.dataset.durationOption === state.durationMode);
      });
      document.querySelectorAll("[data-mood-chip]").forEach((button) => {
        button.classList.toggle("active", state.selectedCategories.has(button.dataset.moodChip));
      });
      syncControlVisibility();
    };

    controlsMount.querySelectorAll("[data-when-option]").forEach((button) => {
      button.addEventListener("click", () => {
        state.whenMode = button.dataset.whenOption;
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
    });
    document.querySelector("[name=customStart]")?.addEventListener("change", (event) => {
      state.customStart = event.target.value;
    });
    document.querySelector("[name=customDuration]")?.addEventListener("change", (event) => {
      state.customDuration = event.target.value;
    });
    document.querySelector("[name=moodText]")?.addEventListener("input", (event) => {
      state.moodText = event.target.value;
    });

    document.querySelector("[data-my-channel-form]").addEventListener("submit", async (event) => {
      event.preventDefault();
      const { start, end, durationMinutes } = computeWindow(state);
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
                <span>When?</span>
                <div class="my-channel-quick-row">
                  ${WHEN_OPTIONS.map((option) => `<button type="button" class="chip" data-when-option="${option.id}">${option.label}</button>`).join("")}
                </div>
                <div class="planner-form-grid" data-when-custom hidden>
                  <label>
                    <span>Date</span>
                    <input class="input" name="customDate" type="date" value="${toDateValue(new Date())}" />
                  </label>
                  <label>
                    <span>Start time</span>
                    <input class="input" name="customStart" type="time" value="19:00" />
                  </label>
                </div>
              </label>
              <label>
                <span>How much time?</span>
                <div class="my-channel-quick-row">
                  ${DURATION_OPTIONS.map((option) => `<button type="button" class="chip" data-duration-option="${option.id}">${option.label}</button>`).join("")}
                </div>
                <div class="planner-form-grid" data-duration-custom hidden>
                  <label>
                    <span>Minutes</span>
                    <input class="input" name="customDuration" type="number" min="15" max="720" value="180" />
                  </label>
                </div>
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
