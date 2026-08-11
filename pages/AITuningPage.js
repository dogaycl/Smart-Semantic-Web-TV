import { getAiPreferences, saveAiPreferences } from "../services/userDataService.js";

const types = ["Movies", "Series", "Documentaries", "Science", "Technology", "Sports", "Kids", "Entertainment"];
const moods = ["Feel-good", "Emotional", "Suspense", "Mind-bending", "Action Rush", "Cozy Night", "Dark & Gritty", "Family Night", "Documentary Mode", "Critically Acclaimed"];
const presets = {
  Quality: { minImdb: 8.2, popularity: 55, maxDurationMinutes: 180, releaseAfter: 2000, discoveryLevel: 35, preferredMood: "Critically Acclaimed", useMood: true },
  Trending: { minImdb: 7.0, popularity: 92, maxDurationMinutes: 210, releaseAfter: 2018, discoveryLevel: 25, preferredMood: "Action Rush", useMood: true },
  Explorer: { minImdb: 7.3, popularity: 45, maxDurationMinutes: 190, releaseAfter: 1990, discoveryLevel: 82, preferredMood: "Mind-bending", useMood: true },
  Weekend: { minImdb: 7.0, popularity: 70, maxDurationMinutes: 125, releaseAfter: 2010, discoveryLevel: 45, preferredMood: "Feel-good", useMood: true }
};

export function AITuningPage() {
  const prefs = getAiPreferences();
  if (!moods.includes(prefs.preferredMood)) prefs.preferredMood = moods[0];
  const tuningStateClass = (enabled) => enabled ? "is-active" : "is-muted";

  queueMicrotask(() => {
    const form = document.querySelector("[data-ai-tuning-form]");
    const preview = document.querySelector("[data-ai-tuning-preview]");
    const rules = document.querySelector("[data-ai-rules]");
    const payload = document.querySelector("[data-ai-payload]");
    const syncTuningControls = () => {
      form.querySelectorAll("[data-toggle-control]").forEach((control) => {
        const useInput = control.querySelector("input[type='checkbox']");
        const valueInputs = [...control.querySelectorAll("input:not([type='checkbox']), select")];
        const isActive = Boolean(useInput?.checked);
        control.classList.toggle("is-active", isActive);
        control.classList.toggle("is-muted", !isActive);
        control.setAttribute("aria-disabled", String(!isActive));
        valueInputs.forEach((input) => {
          input.disabled = !isActive;
        });
      });
    };
    const updatePreview = () => {
      syncTuningControls();
      const data = readForm();
      const activeRules = [
        data.useMinImdb && `Prioritize titles rated IMDb ${data.minImdb}+`,
        data.usePopularity && `Consider popularity at ${data.popularity}% strength`,
        data.useDiscoveryLevel && `Keep novelty appetite around ${data.discoveryLevel}%`,
        data.useMaxDuration && `Avoid titles longer than ${data.maxDurationMinutes} minutes`,
        data.useReleaseAfter && `Prefer releases after ${data.releaseAfter}`,
        data.useMood && `Match the ${data.preferredMood} mood`,
        data.contentTypes.length && `Limit recommendations to ${data.contentTypes.join(", ")}`,
        data.avoidSpoilers && "Avoid spoilers in AI answers",
        data.familySafe && "Prefer family-safe recommendations"
      ].filter(Boolean);
      preview.innerHTML = `
        <strong>AI Recommendation Profile</strong>
        <span>${data.useMinImdb ? `IMDb ${data.minImdb}+` : "IMDb off"} • ${data.usePopularity ? `popularity ${data.popularity}%` : "popularity off"} • ${data.useMaxDuration ? `max ${data.maxDurationMinutes} min` : "duration off"} • ${data.useReleaseAfter ? `after ${data.releaseAfter}` : "year off"}</span>
        <span>Mood: ${data.useMood ? data.preferredMood : "mood off"} • New taste: ${data.useDiscoveryLevel ? `${data.discoveryLevel}%` : "off"} • Types: ${data.contentTypes.join(", ") || "Any"}</span>
      `;
      rules.innerHTML = activeRules.map((rule) => `<li>${rule}</li>`).join("");
      payload.textContent = JSON.stringify(data, null, 2);
    };
    const readForm = () => ({
      useMinImdb: form.useMinImdb.checked,
      minImdb: Number(form.minImdb.value),
      usePopularity: form.usePopularity.checked,
      popularity: Number(form.popularity.value),
      useMaxDuration: form.useMaxDuration.checked,
      maxDurationMinutes: Number(form.maxDurationMinutes.value),
      useReleaseAfter: form.useReleaseAfter.checked,
      releaseAfter: Number(form.releaseAfter.value),
      useDiscoveryLevel: form.useDiscoveryLevel.checked,
      discoveryLevel: Number(form.discoveryLevel.value),
      useMood: form.useMood.checked,
      preferredMood: form.preferredMood.value,
      contentTypes: [...form.querySelectorAll("[name='contentTypes']:checked")].map((input) => input.value),
      avoidSpoilers: form.avoidSpoilers.checked,
      familySafe: form.familySafe.checked
    });
    form.addEventListener("input", updatePreview);
    form.addEventListener("change", updatePreview);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      saveAiPreferences(readForm());
      document.querySelector("[data-ai-tuning-status]").textContent = "AI preferences saved. Home recommendations will use this profile.";
    });
    document.querySelectorAll("[data-ai-preset]").forEach((button) => {
      button.addEventListener("click", () => {
        const preset = presets[button.dataset.aiPreset];
        Object.entries(preset).forEach(([key, value]) => {
          if (form[key]?.type === "checkbox") form[key].checked = value;
          else if (form[key]) form[key].value = value;
        });
        updatePreview();
      });
    });
    updatePreview();
  });

  return `
    <main class="page">
      <section class="ai-tuning-hero">
        <span class="eyebrow">Train your AI</span>
        <h1>Shape the recommendation engine around your taste.</h1>
        <p>This panel is a flexible preference layer that tells Vynex AI which content signals should matter most from now on.</p>
        <div class="ai-preset-row">
          ${Object.keys(presets).map((name) => `<button data-ai-preset="${name}">${name}</button>`).join("")}
        </div>
      </section>

      <section class="ai-tuning-layout">
        <form class="ai-tuning-form" data-ai-tuning-form>
          <div class="tuning-section-title"><span class="eyebrow">Scoring weights</span><h2>Recommendation controls</h2></div>
          <div class="tuning-control ${tuningStateClass(prefs.useMinImdb)}" data-toggle-control><label class="switch-line"><input name="useMinImdb" type="checkbox" ${prefs.useMinImdb ? "checked" : ""} /> Use</label><label><span>Minimum IMDb quality</span><input name="minImdb" type="range" min="5" max="9.5" step="0.1" value="${prefs.minImdb}" /></label></div>
          <div class="tuning-control ${tuningStateClass(prefs.usePopularity)}" data-toggle-control><label class="switch-line"><input name="usePopularity" type="checkbox" ${prefs.usePopularity ? "checked" : ""} /> Use</label><label><span>Popularity importance</span><input name="popularity" type="range" min="0" max="100" value="${prefs.popularity}" /></label></div>
          <div class="tuning-control ${tuningStateClass(prefs.useDiscoveryLevel)}" data-toggle-control><label class="switch-line"><input name="useDiscoveryLevel" type="checkbox" ${prefs.useDiscoveryLevel ? "checked" : ""} /> Use</label><label><span>Novelty appetite</span><input name="discoveryLevel" type="range" min="0" max="100" value="${prefs.discoveryLevel}" /></label></div>
          <div class="number-grid">
            <div class="tuning-control compact ${tuningStateClass(prefs.useMaxDuration)}" data-toggle-control><label class="switch-line"><input name="useMaxDuration" type="checkbox" ${prefs.useMaxDuration ? "checked" : ""} /> Use</label><label><span>Max duration / minutes</span><input class="input" name="maxDurationMinutes" type="number" min="20" max="240" value="${prefs.maxDurationMinutes}" /></label></div>
            <div class="tuning-control compact ${tuningStateClass(prefs.useReleaseAfter)}" data-toggle-control><label class="switch-line"><input name="useReleaseAfter" type="checkbox" ${prefs.useReleaseAfter ? "checked" : ""} /> Use</label><label><span>Release year after</span><input class="input" name="releaseAfter" type="number" min="1970" max="2026" value="${prefs.releaseAfter}" /></label></div>
          </div>
          <div class="tuning-control compact ${tuningStateClass(prefs.useMood)}" data-toggle-control><label class="switch-line"><input name="useMood" type="checkbox" ${prefs.useMood ? "checked" : ""} /> Use</label><label><span>Preferred mood</span><select class="select" name="preferredMood">${moods.map((mood) => `<option ${prefs.preferredMood === mood ? "selected" : ""}>${mood}</option>`).join("")}</select></label></div>
          <fieldset>
            <legend>Content types</legend>
            <div class="check-grid">
              ${types.map((type) => `<label><input name="contentTypes" type="checkbox" value="${type}" ${prefs.contentTypes.includes(type) ? "checked" : ""} /> ${type}</label>`).join("")}
            </div>
          </fieldset>
          <div class="toggle-grid">
            <label><input name="avoidSpoilers" type="checkbox" ${prefs.avoidSpoilers ? "checked" : ""} /> Avoid spoilers in AI answers</label>
            <label><input name="familySafe" type="checkbox" ${prefs.familySafe ? "checked" : ""} /> Family-safe recommendations</label>
          </div>
          <button class="primary-button">Save AI Training</button>
          <p class="muted" data-ai-tuning-status></p>
        </form>
        <aside class="ai-tuning-preview">
          <div data-ai-tuning-preview></div>
          <div class="active-rules-card">
            <span class="eyebrow">Active AI rules</span>
            <h2>What Vynex will use</h2>
            <ul data-ai-rules></ul>
          </div>
          <div class="ai-training-notes">
            <h2>What do these controls do?</h2>
            <p>They define IMDb quality threshold, popularity level, maximum runtime, release year, mood, and novelty appetite. Once the backend is connected, these values can be sent directly to the recommendation endpoint.</p>
          </div>
          <pre class="ai-payload-preview" data-ai-payload></pre>
        </aside>
      </section>
    </main>
  `;
}
