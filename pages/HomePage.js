import { api } from "../services/api.js";
import { content } from "../data/mockData.js";
import { HeroBanner } from "../components/HeroBanner.js";
import { ContentRow } from "../components/ContentRow.js";
import { ContentCard } from "../components/ContentCard.js";
import { getActiveProfile, getAiPreferences } from "../services/userDataService.js";

export function HomePage() {
  queueMicrotask(async () => {
    const featured = await api.getFeatured();
    const rows = await api.getRows();
    const activeProfile = getActiveProfile();
    const aiPrefs = getAiPreferences();
    const aiTuned = content
      .filter((item) => !aiPrefs.useMinImdb || Number(item.imdb || 0) >= aiPrefs.minImdb)
      .filter((item) => !aiPrefs.useReleaseAfter || item.year >= aiPrefs.releaseAfter)
      .filter((item) => aiPrefs.contentTypes.includes(item.category))
      .sort((a, b) => Number(b.imdb || 0) - Number(a.imdb || 0))
      .slice(0, 8);
    rows["AI Tuned For You"] = aiTuned.length ? aiTuned : content.slice(0, 6);
    if (activeProfile === "Kids") {
      rows["Profile Picks"] = content.filter((item) => ["Kids", "Science", "Entertainment"].includes(item.category)).slice(0, 5);
    } else if (activeProfile === "Family") {
      rows["Profile Picks"] = content.filter((item) => ["Documentaries", "News", "Movies"].includes(item.category)).slice(0, 5);
    } else {
      rows["Profile Picks"] = content.filter((item) => ["Science", "Technology", "Series"].includes(item.category)).slice(0, 5);
    }
    document.querySelector("#homeHero").innerHTML = HeroBanner(featured);
    document.querySelector("#plannerPicks").innerHTML = content
      .filter((item) => ["interstellar", "the-last-of-us", "the-social-dilemma"].includes(item.id))
      .map((item) => ContentCard(item))
      .join("");
    document.querySelector("#homeRows").innerHTML = Object.entries(rows).map(([title, items]) => ContentRow(title, items)).join("");
    document.dispatchEvent(new CustomEvent("page:mounted"));
  });

  return `
    <main class="page">
      <div id="homeHero">${HeroBanner(content[0])}</div>
      <section class="watch-planner">
        <div class="planner-copy">
          <span class="eyebrow">Smart Watchlist</span>
          <h2>Tonight Planner</h2>
          <p>High-IMDb picks around two hours, tuned toward your science-fiction and technology taste.</p>
          <div class="planner-filters">
            <span>⏱ Under 3h</span>
            <span>🧠 Thoughtful</span>
            <span>👥 Watch party ready</span>
          </div>
          <div class="ai-reason-box">
            <strong>AI reasoning</strong>
            <span>Interstellar, The Last of Us, and The Social Dilemma are highlighted because your profile leans toward Science + Technology.</span>
          </div>
        </div>
        <div id="plannerPicks" class="planner-picks"></div>
      </section>
      <div id="homeRows"></div>
    </main>
  `;
}
