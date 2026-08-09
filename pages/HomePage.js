import { api } from "../services/api.js";
import { content } from "../data/mockData.js";
import { HeroBanner } from "../components/HeroBanner.js";
import { ContentRow } from "../components/ContentRow.js";

export function HomePage() {
  queueMicrotask(async () => {
    const featured = await api.getFeatured();
    const rows = await api.getRows();
    document.querySelector("#homeHero").innerHTML = HeroBanner(featured);
    document.querySelector("#homeRows").innerHTML = Object.entries(rows).map(([title, items]) => ContentRow(title, items)).join("");
    document.dispatchEvent(new CustomEvent("page:mounted"));
  });

  return `
    <main class="page">
      <div id="homeHero">${HeroBanner(content[0])}</div>
      <div id="homeRows"></div>
    </main>
  `;
}
