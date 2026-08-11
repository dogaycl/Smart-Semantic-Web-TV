import { content } from "../data/mockData.js";
import { ContentRow } from "../components/ContentRow.js";
import { ContentCard } from "../components/ContentCard.js";
import { getWatchHistory } from "../services/userDataService.js";

function byIds(ids) {
  return ids.map((id) => content.find((item) => item.id === id)).filter(Boolean);
}

export function OnDemandPage() {
  const history = getWatchHistory().map((entry) => content.find((item) => item.id === entry.contentId)).filter(Boolean);
  const movies = content.filter((item) => item.category === "Movies");
  const series = content.filter((item) => item.category === "Series");
  const docs = content.filter((item) => item.category === "Documentaries" || item.category === "Technology" || item.category === "Science");
  const recentlyAdded = byIds(["oppenheimer", "the-last-of-us", "john-wick-4", "wednesday", "avatar-way-water"]);
  const filterGroups = {
    all: [...recentlyAdded, ...movies.slice(0, 8), ...series.slice(0, 6), ...docs.slice(0, 6)],
    movies,
    series,
    docs,
    new: recentlyAdded
  };

  queueMicrotask(() => {
    const buttons = [...document.querySelectorAll("[data-vod-filter]")];
    const focusTitle = document.querySelector("[data-vod-focus-title]");
    const focusGrid = document.querySelector("[data-vod-focus-grid]");
    const rows = [...document.querySelectorAll("[data-vod-row]")];

    const labels = {
      all: "All On Demand",
      movies: "Movies",
      series: "Series & Episodes",
      docs: "Documentaries & Science",
      new: "Recently Added"
    };

    const renderFilter = (key) => {
      buttons.forEach((button) => button.classList.toggle("active", button.dataset.vodFilter === key));
      focusTitle.textContent = labels[key];
      focusGrid.innerHTML = filterGroups[key].map((item) => ContentCard(item)).join("");
      rows.forEach((row) => {
        row.hidden = key !== "all" && row.dataset.vodRow !== key;
      });
    };

    buttons.forEach((button) => {
      button.addEventListener("click", () => renderFilter(button.dataset.vodFilter));
    });

    renderFilter("all");
  });

  return `
    <main class="page">
      <section class="vod-hero">
        <div>
          <span class="eyebrow">Video on Demand</span>
          <h1>Watch anytime.</h1>
          <p>Movies, series, documentaries, new releases, and continue-watching experiences live in one on-demand hub.</p>
          <div class="vod-filter-tabs" aria-label="On Demand filters">
            <button class="active" data-vod-filter="all" type="button">All</button>
            <button data-vod-filter="movies" type="button">Movies</button>
            <button data-vod-filter="series" type="button">Series</button>
            <button data-vod-filter="docs" type="button">Documentaries</button>
            <button data-vod-filter="new" type="button">Recently Added</button>
            <a href="#/discover">Smart Search</a>
          </div>
        </div>
      </section>

      <section class="vod-focus-panel">
        <div class="section-head">
          <div>
            <span class="eyebrow">Selected shelf</span>
            <h2 data-vod-focus-title>All On Demand</h2>
          </div>
        </div>
        <div class="content-grid vod-focus-grid" data-vod-focus-grid></div>
      </section>

      ${history.length ? `<div data-vod-row="continue">${ContentRow("Continue Watching", history)}</div>` : ""}

      <section class="content-row" data-vod-row="new">
        <div class="section-head"><h2>Recently Added</h2></div>
        <div class="row-scroll">${recentlyAdded.map((item) => ContentCard(item)).join("")}</div>
      </section>

      <div data-vod-row="movies">${ContentRow("Movies", movies)}</div>
      <div data-vod-row="series">${ContentRow("Series & Episodes", series)}</div>
      <div data-vod-row="docs">${ContentRow("Documentaries & Science", docs)}</div>
    </main>
  `;
}
