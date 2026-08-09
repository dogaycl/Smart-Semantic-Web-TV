import { ContentCard } from "./ContentCard.js";

export function ContentRow(title, items) {
  return `
    <section class="content-row">
      <div class="section-head">
        <h2>${title}</h2>
      </div>
      <div class="row-scroll">
        ${items.map((item) => ContentCard(item)).join("")}
      </div>
    </section>
  `;
}
