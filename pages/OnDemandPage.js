import { ContentRow } from "../components/ContentRow.js";
import { ContentCard } from "../components/ContentCard.js";
import { api } from "../services/api.js?v=55";

function sortByReleaseDate(items) {
  return [...items].sort((a, b) => String(b.releaseDate || "").localeCompare(String(a.releaseDate || "")));
}

// Titles with a real, working playback source (open-licensed / public-domain films
// wired up in the backend) are the only ones you can actually watch in full, so they
// lead every On Demand shelf. Array.prototype.sort is stable, so the existing order
// (popularity, release date, ...) is preserved within the playable and non-playable groups.
function playableFirst(items) {
  return [...items].sort((a, b) => (b.isPlayable ? 1 : 0) - (a.isPlayable ? 1 : 0));
}

export function OnDemandPage() {
  queueMicrotask(() => {
    (async () => {
      const buttons = [...document.querySelectorAll("[data-vod-filter]")];
      const focusTitle = document.querySelector("[data-vod-focus-title]");
      const focusGrid = document.querySelector("[data-vod-focus-grid]");
      const rows = [...document.querySelectorAll("[data-vod-row]")];

      try {
        const allItemsRaw = await api.getAllCatalog();
        const allItems = playableFirst(allItemsRaw);
        const historyEntries = await api.getMyWatchHistory();
        const history = await api.getCatalogBySlugs(
          historyEntries
            .filter((entry) => entry.contentType === "content")
            .map((entry) => entry.contentId)
        );
        const movies = playableFirst(allItems.filter((item) => item.contentType === "movie"));
        const series = playableFirst(allItems.filter((item) => item.contentType === "tv"));
        const docs = playableFirst(allItems.filter((item) => item.genres.includes("Documentary") || item.genres.includes("Science Fiction") || item.genres.includes("Sci-Fi & Fantasy")));
        const recentlyAdded = playableFirst(sortByReleaseDate(allItems).slice(0, 10));
        const filterGroups = {
          all: [...recentlyAdded.slice(0, 6), ...movies.slice(0, 8), ...series.slice(0, 6), ...docs.slice(0, 6)],
          movies,
          series,
          docs,
          new: recentlyAdded
        };

        const labels = {
          all: "All On Demand",
          movies: "Movies",
          series: "Series & Episodes",
          docs: "Documentaries & Science",
          new: "Recently Added"
        };

        const renderCards = (items) => items.length ? items.map((item) => ContentCard(item)).join("") : `<div class="empty-state">No catalog titles available.</div>`;
        const renderFilter = (key) => {
          buttons.forEach((button) => button.classList.toggle("active", button.dataset.vodFilter === key));
          focusTitle.textContent = labels[key];
          focusGrid.innerHTML = renderCards(filterGroups[key]);
          rows.forEach((row) => {
            row.hidden = key !== "all" && row.dataset.vodRow !== key;
          });
        };

        buttons.forEach((button) => {
          button.addEventListener("click", () => renderFilter(button.dataset.vodFilter));
        });

        const continueMount = document.querySelector("[data-vod-continue]");
        if (continueMount) {
          continueMount.innerHTML = history.length ? ContentRow("Continue Watching", history) : "";
        }
        document.querySelector("[data-vod-new]").innerHTML = recentlyAdded.length ? ContentRow("Recently Added", recentlyAdded) : "";
        document.querySelector("[data-vod-movies]").innerHTML = movies.length ? ContentRow("Movies", movies) : "";
        document.querySelector("[data-vod-series]").innerHTML = series.length ? ContentRow("Series & Episodes", series) : "";
        document.querySelector("[data-vod-docs]").innerHTML = docs.length ? ContentRow("Documentaries & Science", docs) : "";

        renderFilter("all");
      } catch (error) {
        focusTitle.textContent = "Catalog unavailable";
        focusGrid.innerHTML = `<div class="empty-state">${error.message || "On-demand catalog could not be loaded."}</div>`;
        rows.forEach((row) => {
          row.innerHTML = "";
        });
      }
    })();
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
        <div class="content-grid vod-focus-grid" data-vod-focus-grid><div class="empty-state">Loading real catalog...</div></div>
      </section>

      <div data-vod-continue></div>

      <div data-vod-row="new" data-vod-new></div>

      <div data-vod-row="movies" data-vod-movies></div>
      <div data-vod-row="series" data-vod-series></div>
      <div data-vod-row="docs" data-vod-docs></div>
    </main>
  `;
}
