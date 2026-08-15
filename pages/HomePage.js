import { api } from "../services/api.js";
import { HeroBanner } from "../components/HeroBanner.js";
import { ContentRow } from "../components/ContentRow.js";
import { ContentCard } from "../components/ContentCard.js";
import { toggleFavorite } from "../services/favoritesService.js";
import { getActiveProfile, getAiPreferences } from "../services/userDataService.js";

export function HomePage() {
  queueMicrotask(async () => {
    const heroMount = document.querySelector("#homeHero");
    const plannerMount = document.querySelector("#plannerPicks");
    const rowsMount = document.querySelector("#homeRows");
    if (!heroMount || !plannerMount || !rowsMount) return;

    try {
      const [featured, rows, allItems] = await Promise.all([
        api.getFeatured(),
        api.getRows(),
        api.getAllCatalog()
      ]);
      const activeProfile = getActiveProfile();
      const aiPrefs = getAiPreferences();
      const aiTuned = await api.getAiTunedCatalog(aiPrefs);
      rows["AI Tuned For You"] = aiTuned.slice(0, 8).length ? aiTuned.slice(0, 8) : allItems.slice(0, 6);
      if (activeProfile === "Kids") {
        rows["Profile Picks"] = allItems.filter((item) => item.genres.includes("Animation") || item.genres.includes("Comedy") || item.genres.includes("Documentary")).slice(0, 5);
      } else if (activeProfile === "Family") {
        rows["Profile Picks"] = allItems.filter((item) => item.category === "Movies" || item.genres.includes("Documentary") || item.genres.includes("Drama")).slice(0, 5);
      } else {
        rows["Profile Picks"] = allItems.filter((item) => item.genres.includes("Science Fiction") || item.genres.includes("Sci-Fi & Fantasy") || item.category === "Series").slice(0, 5);
      }

      const visibleRows = Object.entries(rows).filter(([, items]) => items.length);

      heroMount.innerHTML = featured ? HeroBanner(featured) : `<div class="empty-state">Catalog is empty. Configure TMDB and sync the backend catalog.</div>`;
      plannerMount.innerHTML = aiTuned
        .slice(0, 3)
        .map((item) => ContentCard(item))
        .join("") || `<div class="empty-state">No personalized picks available yet.</div>`;
      rowsMount.innerHTML = visibleRows.length
        ? visibleRows.map(([title, items]) => ContentRow(title, items)).join("")
        : `<div class="empty-state">No real catalog shelves are available yet.</div>`;

      document.querySelector("[data-hero-favorite]")?.addEventListener("click", (event) => {
        event.preventDefault();
        const contentId = event.currentTarget.dataset.heroFavorite;
        toggleFavorite(contentId);
        event.currentTarget.classList.toggle("active");
      });
    } catch (error) {
      heroMount.innerHTML = `<div class="empty-state">${error.message || "Catalog could not be loaded."}</div>`;
      plannerMount.innerHTML = `<div class="empty-state">Personalized picks are unavailable right now.</div>`;
      rowsMount.innerHTML = `<div class="empty-state">Catalog shelves could not be loaded.</div>`;
    }
    document.dispatchEvent(new CustomEvent("page:mounted"));
  });

  return `
    <main class="page">
      <div id="homeHero"><div class="empty-state">Loading real catalog...</div></div>
      <section class="watch-planner">
        <div class="planner-copy">
          <span class="eyebrow">Smart Watchlist</span>
          <h2>Tonight Planner</h2>
          <p>Recommendations now blend your real profile, favorites, watch history, live availability, and catalog semantics from the backend.</p>
          <div class="planner-filters">
            <span>⏱ Under 3h</span>
            <span>🧠 Thoughtful</span>
            <span>👥 Watch party ready</span>
          </div>
          <div class="ai-reason-box">
            <strong>Recommendation engine</strong>
            <span>This shelf now uses transparent weighted scoring over real user data, semantic similarity, popularity, and live availability. Gemini planning comes later.</span>
          </div>
        </div>
        <div id="plannerPicks" class="planner-picks"></div>
      </section>
      <div id="homeRows"></div>
    </main>
  `;
}
