import { getCurrentUser } from "../contexts/authContext.js";
import { api } from "../services/api.js";

const DEFAULT_PLAN_DATE = "2026-08-15";

const plannerPresets = [
  {
    label: "Tonight 19:00-23:00",
    start: "19:00",
    end: "23:00",
    duration: "240",
    categories: "Documentary, Technology",
    preference: "Use live TV first, then add something about science or AI."
  },
  {
    label: "Two-hour science block",
    start: "20:00",
    end: "22:00",
    duration: "120",
    categories: "Documentary, Science",
    preference: "I want science or technology content only."
  },
  {
    label: "Saturday mix",
    start: "18:30",
    end: "22:30",
    duration: "210",
    categories: "Documentary, Drama",
    preference: "Plan my Saturday evening using live TV and one strong movie."
  }
];

function currentDateValue() {
  return DEFAULT_PLAN_DATE;
}

function formatDateTime(value, timezone) {
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone
  }).format(new Date(value));
}

function formatRange(item, timezone) {
  const formatter = new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: timezone
  });
  return `${formatter.format(new Date(item.plannedStart))} - ${formatter.format(new Date(item.plannedEnd))}`;
}

function typeClass(resultType) {
  if (resultType === "live_program") return "live";
  if (resultType === "series") return "series";
  return "movie";
}

function typeLabel(resultType) {
  if (resultType === "live_program") return "LIVE";
  if (resultType === "series") return "SERIES";
  return "MOVIE";
}

function plannerItemCard(item, timezone) {
  return `
    <a class="planner-plan-item" href="${item.routePath}"${item.liveChannelId ? ` data-planner-live-channel="${item.liveChannelId}"` : ""}>
      <div class="planner-plan-time">${formatRange(item, timezone)}</div>
      <div class="planner-plan-body">
        <div class="planner-plan-head">
          <span class="planner-type-badge ${typeClass(item.resultType)}">${typeLabel(item.resultType)}</span>
          <strong>${item.title}</strong>
        </div>
        <p>${item.recommendationReason}</p>
        <div class="planner-plan-meta">
          <span>${item.category}</span>
          <span>${item.runtimeDisplay}</span>
          ${item.channel?.name ? `<span>${item.channel.name}</span>` : ""}
        </div>
      </div>
    </a>
  `;
}

function savedPlanRow(plan, timezone) {
  return `
    <button class="planner-saved-button" data-plan-id="${plan.id}">
      <strong>${formatDateTime(plan.availableStart, timezone)}</strong>
      <span>${plan.summary}</span>
      <small>${plan.items.length} items • ${plan.generationSource === "gemini" ? "Gemini" : "Fallback"}</small>
    </button>
  `;
}

function renderPlan(plan, timezone) {
  if (!plan) {
    return `
      <div class="planner-empty">
        <strong>No generated plan yet.</strong>
        <span>Choose a window, add optional preferences, and generate a real schedule from live TV and catalog candidates.</span>
      </div>
    `;
  }

  return `
    <div class="planner-result-summary">
      <span class="eyebrow">Saved plan #${plan.id}</span>
      <h2>${plan.summary}</h2>
      <div class="planner-plan-meta">
        <span>${formatDateTime(plan.availableStart, timezone)} - ${formatDateTime(plan.availableEnd, timezone)}</span>
        <span>${plan.generationSource === "gemini" ? "Gemini plan" : "Deterministic fallback"}</span>
        ${plan.llmRepairApplied ? "<span>Validated after repair</span>" : ""}
      </div>
    </div>
    <div class="planner-plan-list">
      ${plan.items.map((item) => plannerItemCard(item, timezone)).join("")}
    </div>
  `;
}

export function AIHubPage() {
  const user = getCurrentUser();
  const defaultCategories = user?.preferredCategories?.join(", ") || "Documentary, Technology";
  const defaultPreference = user?.interests?.length
    ? `Use my interests: ${user.interests.join(", ")}.`
    : "Mix live TV with one strong movie or series.";

  queueMicrotask(async () => {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
    const form = document.querySelector("[data-planner-form]");
    const resultMount = document.querySelector("[data-planner-result]");
    const savedMount = document.querySelector("[data-planner-saved]");
    const statusMount = document.querySelector("[data-planner-status]");

    const bindLiveLinks = () => {
      document.querySelectorAll("[data-planner-live-channel]").forEach((element) => {
        element.addEventListener("click", () => {
          sessionStorage.setItem("synapse.live.channel-id", element.dataset.plannerLiveChannel);
        });
      });
    };

    let savedPlans = [];
    let activePlan = null;

    const draw = () => {
      resultMount.innerHTML = renderPlan(activePlan, timezone);
      savedMount.innerHTML = savedPlans.length
        ? savedPlans.map((plan) => savedPlanRow(plan, timezone)).join("")
        : `<div class="planner-empty"><strong>No saved plans yet.</strong><span>Your generated viewing plans will appear here.</span></div>`;

      document.querySelectorAll("[data-plan-id]").forEach((button) => {
        button.addEventListener("click", async () => {
          statusMount.textContent = "Loading saved plan...";
          try {
            activePlan = await api.getViewingPlan(button.dataset.planId);
            draw();
            statusMount.textContent = "";
          } catch (error) {
            statusMount.textContent = error.message || "Saved plan could not be loaded.";
          }
        });
      });

      bindLiveLinks();
    };

    const reloadPlans = async () => {
      savedPlans = await api.getViewingPlans().catch(() => []);
      activePlan = activePlan || savedPlans[0] || null;
      draw();
    };

    const readPayload = () => ({
      plan_date: form.planDate.value,
      available_start: form.availableStart.value,
      available_end: form.availableEnd.value,
      timezone,
      max_duration_minutes: form.maxDuration.value ? Number(form.maxDuration.value) : null,
      preferred_categories: form.categories.value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
      include_live: form.includeLive.checked,
      include_vod: form.includeVod.checked,
      preference_text: form.preferenceText.value.trim() || null
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      statusMount.textContent = "Generating your real viewing plan...";
      resultMount.innerHTML = `<div class="planner-empty"><strong>Planner is working.</strong><span>Gemini is selecting from real EPG and VOD candidates only.</span></div>`;
      try {
        activePlan = await api.generateViewingPlan(readPayload());
        statusMount.textContent = "Plan saved successfully.";
        await reloadPlans();
      } catch (error) {
        resultMount.innerHTML = `<div class="planner-empty"><strong>Planner error</strong><span>${error.message || "The viewing plan could not be generated."}</span></div>`;
        statusMount.textContent = "Planner request failed.";
      }
    });

    document.querySelectorAll("[data-planner-preset]").forEach((button) => {
      button.addEventListener("click", () => {
        const preset = plannerPresets.find((item) => item.label === button.dataset.plannerPreset);
        if (!preset) return;
        form.availableStart.value = preset.start;
        form.availableEnd.value = preset.end;
        form.maxDuration.value = preset.duration;
        form.categories.value = preset.categories;
        form.preferenceText.value = preset.preference;
      });
    });

    await reloadPlans();
  });

  return `
    <main class="page ai-hub-page">
      <section class="ai-hub-hero">
        <div class="ai-hub-hero-copy">
          <span class="eyebrow">Gemini-powered planner</span>
          <h1>Plan My Evening with real live TV and real on-demand titles.</h1>
          <p>The planner now builds a candidate set from the actual EPG, live channels, catalog metadata, and your saved profile. Gemini can only choose from those real candidates, and the backend validates every schedule before saving it.</p>
          <div class="ai-hub-prompts">
            ${plannerPresets.map((preset) => `<button type="button" data-planner-preset="${preset.label}">${preset.label}</button>`).join("")}
          </div>
        </div>
        <aside class="ai-hub-status">
          <span class="eyebrow">Current profile signals</span>
          <h2>${user?.displayName || "Viewer"}</h2>
          <ul>
            <li>${user?.preferredCategories?.length ? user.preferredCategories.join(", ") : "No preferred categories saved yet"}</li>
            <li>${user?.interests?.length ? user.interests.join(", ") : "No interests saved yet"}</li>
            <li>Planner uses recommendations, favorites, history, and real availability windows.</li>
          </ul>
          <a class="ghost-button" href="#/profile">Update profile signals</a>
        </aside>
      </section>

      <section class="planner-studio">
        <article class="ai-workbench-card planner-form-card">
          <div class="planner-form-head">
            <span class="eyebrow">Plan request</span>
            <h2>Build a real viewing schedule</h2>
          </div>
          <form class="planner-form" data-planner-form>
            <div class="planner-form-grid">
              <label>
                <span>Date</span>
                <input class="input" name="planDate" type="date" value="${currentDateValue()}" />
              </label>
              <label>
                <span>Start</span>
                <input class="input" name="availableStart" type="time" value="19:00" />
              </label>
              <label>
                <span>End</span>
                <input class="input" name="availableEnd" type="time" value="23:00" />
              </label>
              <label>
                <span>Max duration / min</span>
                <input class="input" name="maxDuration" type="number" min="15" max="720" value="180" />
              </label>
            </div>
            <label>
              <span>Preferred categories</span>
              <input class="input" name="categories" value="${defaultCategories}" />
            </label>
            <label>
              <span>Extra preference</span>
              <textarea class="input planner-textarea" name="preferenceText">${defaultPreference}</textarea>
            </label>
            <div class="planner-checkbox-row">
              <label><input name="includeLive" type="checkbox" checked /> Include live TV</label>
              <label><input name="includeVod" type="checkbox" checked /> Include movies / series</label>
            </div>
            <button class="primary-button">Generate My Plan</button>
            <p class="muted" data-planner-status></p>
          </form>
        </article>

        <article class="ai-workbench-card planner-result-card">
          <div class="planner-form-head">
            <span class="eyebrow">Generated plan</span>
            <h2>Validated schedule</h2>
          </div>
          <div data-planner-result></div>
        </article>
      </section>

      <section class="ai-workbench">
        <article class="ai-workbench-card">
          <span class="eyebrow">Saved history</span>
          <h2>Recent viewing plans</h2>
          <div class="planner-saved-list" data-planner-saved></div>
        </article>
        <article class="ai-workbench-card">
          <span class="eyebrow">Why it is trustworthy</span>
          <h2>Planner guardrails</h2>
          <p>This planner does not invent channels, broadcasts, or movies. The backend first builds a real candidate pool from the database, sends only candidate IDs and metadata to Gemini, validates the returned schedule, and falls back deterministically if the AI output is invalid.</p>
          <div class="planner-chip-row">
            <span>Real EPG</span>
            <span>Real catalog</span>
            <span>Saved profile</span>
            <span>Validation</span>
            <span>Fallback plan</span>
          </div>
        </article>
      </section>

      <section class="ai-training-callout">
        <div>
          <span class="eyebrow">Tune future plans</span>
          <h2>Profile signals still shape the planner.</h2>
          <p>Your saved interests, preferred categories, favorites, watch history, and recommendation scores feed the planner before Gemini sees any candidates.</p>
        </div>
        <a class="primary-button" href="#/ai-tuning">Open AI Training</a>
      </section>
    </main>
  `;
}
